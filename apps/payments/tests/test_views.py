"""
Tests for PaymentViewSet.
"""

from unittest.mock import patch, Mock
import pytest
from decimal import Decimal

from rest_framework import status
from rest_framework.test import APIClient

from apps.payments.models import PromoCode, Payment
from apps.rides.tests.factories import CompletedRideFactory, RideFactory
from apps.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestPaymentViewSet:

    def test_get_queryset_admin_vs_user(self) -> None:
        user = UserFactory()
        admin = UserFactory(role='admin')
        client = APIClient()
        
        # User only sees own payments
        Payment.objects.create(ride=CompletedRideFactory(user=user), user=user, amount=100)
        Payment.objects.create(ride=CompletedRideFactory(user=admin), user=admin, amount=200)
        
        client.force_authenticate(user=user)
        response = client.get('/api/v1/payments/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1

        client.force_authenticate(user=admin)
        response = client.get('/api/v1/payments/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 2

    def test_history_authenticated(self) -> None:
        """GET /api/v1/payments/history/ — Payment history for authenticated user."""
        user = UserFactory()
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get('/api/v1/payments/history/')
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)

    def test_history_unauthenticated(self) -> None:
        """GET /api/v1/payments/history/ — Payment history should require authentication."""
        client = APIClient()
        response = client.get('/api/v1/payments/history/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_validate_promo_valid(self) -> None:
        """POST /api/v1/payments/validate_promo/ — Validate valid promo code."""
        PromoCode.objects.create(
            code='TEST15',
            discount_percent=Decimal('15'),
            is_active=True,
        )
        user = UserFactory()
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post('/api/v1/payments/validate_promo/', {
            'code': 'TEST15',
            'ride_price': '100.00',
        })
        assert response.status_code == status.HTTP_200_OK
        assert response.data['valid'] is True
        assert response.data['discount'] == 15.0

    def test_validate_promo_invalid(self) -> None:
        """POST /api/v1/payments/validate_promo/ — Validate invalid promo code."""
        user = UserFactory()
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post('/api/v1/payments/validate_promo/', {
            'code': 'INVALID',
            'ride_price': '100.00',
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['valid'] is False

    def test_create_cash_payment(self) -> None:
        """POST /api/v1/payments/create_payment/ — Create cash payment for completed ride."""
        user = UserFactory()
        ride = CompletedRideFactory(user=user, final_price=Decimal('115.0'))
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post('/api/v1/payments/create_payment/', {
            'ride_id': str(ride.id),
            'payment_method': 'cash',
            'provider': 'cash',
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['status'] == 'success'

    def test_create_payment_invalid_serializer(self) -> None:
        """POST /api/v1/payments/create_payment/ — Invalid data should return 400."""
        user = UserFactory()
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post('/api/v1/payments/create_payment/', {
            # missing payment_method
            'ride_id': '123'
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_payment_missing_ride_id(self) -> None:
        """POST /api/v1/payments/create_payment/ — Missing ride_id should return 400."""
        user = UserFactory()
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post('/api/v1/payments/create_payment/', {
            'payment_method': 'cash'
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'ride_id is required' in response.data['error']

    def test_create_payment_ride_not_found(self) -> None:
        """POST /api/v1/payments/create_payment/ — Non-existent ride should return 404."""
        user = UserFactory()
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post('/api/v1/payments/create_payment/', {
            'ride_id': '00000000-0000-0000-0000-000000000000',
            'payment_method': 'cash'
        })
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert 'Ride not found' in response.data['error']

    def test_create_payment_value_error(self) -> None:
        """POST /api/v1/payments/create_payment/ — ValueError from service should return 400."""
        user = UserFactory()
        # Ride not completed leads to ValueError
        ride = RideFactory(user=user, status='pending')
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post('/api/v1/payments/create_payment/', {
            'ride_id': str(ride.id),
            'payment_method': 'cash'
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data

    def test_validate_promo_invalid_serializer(self) -> None:
        """POST /api/v1/payments/validate_promo/ — Invalid data should return 400."""
        user = UserFactory()
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post('/api/v1/payments/validate_promo/', {})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch('apps.payments.services.RefundService.create_refund')
    def test_refund_success(self, mock_create_refund) -> None:
        """POST /api/v1/payments/{payment_id}/refund/ — Successfully create a refund."""
        user = UserFactory()
        ride = CompletedRideFactory(user=user)
        payment = Payment.objects.create(ride=ride, user=user, amount=100, status=Payment.Status.SUCCESS, provider='cash')
        
        # Setup mock return value
        mock_refund_instance = Mock()
        mock_refund_instance.id = 'ref_123'
        mock_refund_instance.status = 'success'
        mock_refund_instance.amount = Decimal('50.0')
        mock_create_refund.return_value = mock_refund_instance
        
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post(f'/api/v1/payments/{payment.id}/refund/', {
            'amount': 50,
            'reason': 'Too slow'
        })
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'success'
        assert response.data['refund_id'] == 'ref_123'

    def test_refund_invalid_amount(self) -> None:
        """POST /api/v1/payments/{payment_id}/refund/ — Invalid refund amount should return 400."""
        user = UserFactory()
        payment = Payment.objects.create(ride=CompletedRideFactory(user=user), user=user, amount=100)
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post(f'/api/v1/payments/{payment.id}/refund/', {'amount': 0, 'reason': 'test'})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'Valid amount required' in response.data['error']

    def test_refund_missing_reason(self) -> None:
        """POST /api/v1/payments/{payment_id}/refund/ — Missing reason should return 400."""
        user = UserFactory()
        payment = Payment.objects.create(ride=CompletedRideFactory(user=user), user=user, amount=100)
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post(f'/api/v1/payments/{payment.id}/refund/', {'amount': 50})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'Reason required' in response.data['error']

    def test_refund_value_error(self) -> None:
        """POST /api/v1/payments/{payment_id}/refund/ — ValueError from service should return 400."""
        user = UserFactory()
        # refund amount > payment amount raises ValueError
        payment = Payment.objects.create(ride=CompletedRideFactory(user=user), user=user, amount=100, status=Payment.Status.SUCCESS)
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post(f'/api/v1/payments/{payment.id}/refund/', {'amount': 200, 'reason': 'test'})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch('apps.payments.services.RefundService.create_refund')
    def test_refund_exception(self, mock_create_refund) -> None:
        """POST /api/v1/payments/{payment_id}/refund/ — Exception from service should return 500."""
        user = UserFactory()
        payment = Payment.objects.create(ride=CompletedRideFactory(user=user), user=user, amount=100, status=Payment.Status.SUCCESS)
        client = APIClient()
        client.force_authenticate(user=user)
        
        mock_create_refund.side_effect = Exception('Unexpected err')
        response = client.post(f'/api/v1/payments/{payment.id}/refund/', {'amount': 50, 'reason': 'test'})
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.data['error'] == 'Unexpected err'
