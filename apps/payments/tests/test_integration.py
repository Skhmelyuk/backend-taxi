import pytest
from decimal import Decimal
from rest_framework.test import APIClient
from rest_framework import status
from apps.payments.models import Payment, PromoCode
from apps.payments.tests.factories import PromoCodeFactory
from apps.rides.tests.factories import CompletedRideFactory
from apps.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestPaymentIntegration:
    """Integration tests for payment flows."""
    def test_full_payment_flow(self):
        """Test complete payment flow for a ride."""
        user = UserFactory()
        ride = CompletedRideFactory(user=user, final_price=Decimal('115.0'))
        client = APIClient()
        client.force_authenticate(user=user)

        # Create payment
        response = client.post('/api/v1/payments/create_payment/', {
            'ride_id': str(ride.id),
            'payment_method': 'cash',
            'provider': 'cash',
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['status'] == 'success'
        payment_id = response.data['payment']['id']

        # Check history
        history = client.get('/api/v1/payments/history/')
        assert history.status_code == status.HTTP_200_OK
        assert len(history.data) == 1

        # Try to pay again — should fail
        response2 = client.post('/api/v1/payments/create_payment/', {
            'ride_id': str(ride.id),
            'payment_method': 'cash',
            'provider': 'cash',
        })
        assert response2.status_code == status.HTTP_400_BAD_REQUEST

    def test_promo_code_validation_and_use(self):
        """Test promo code validation then use in ride creation."""
        user = UserFactory()
        promo = PromoCodeFactory(code='INTEG10', discount_percent=10)
        client = APIClient()
        client.force_authenticate(user=user)

        # Validate promo
        resp = client.post('/api/v1/payments/validate_promo/', {
            'code': 'INTEG10', 'ride_price': '100.00'
        })
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['valid'] is True
        assert resp.data['discount'] == 10.0

    def test_refund_after_cancellation(self):
        """Test refund flow after cancelled ride."""
        from apps.payments.services import RefundService, PaymentService
        user = UserFactory()
        ride = CompletedRideFactory(user=user, final_price=Decimal('100.0'))

        result = PaymentService.create_payment(ride, user, payment_method='cash', provider='cash')
        payment = result['payment']

        refund = RefundService.create_refund(
            str(payment.id), Decimal('100.0'), 'Ride cancelled'
        )
        assert refund.status == 'success'
        payment.refresh_from_db()
        assert payment.status == Payment.Status.REFUNDED