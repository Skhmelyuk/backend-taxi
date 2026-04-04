"""
Tests for PaymentService.
"""

from unittest.mock import patch, Mock
import pytest
from decimal import Decimal

from apps.payments.models import Payment
from apps.payments.services import PaymentService
from apps.rides.tests.factories import CompletedRideFactory, RideFactory
from apps.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestPaymentService:

    def test_create_cash_payment(self) -> None:
        """Test creating a cash payment."""
        user = UserFactory()
        ride = CompletedRideFactory(user=user, final_price=Decimal('115.0'))
        result = PaymentService.create_payment(
            ride, user, payment_method='cash', provider='cash'
        )
        assert result['status'] == 'success'
        payment = result['payment']
        assert payment.status == Payment.Status.SUCCESS

    def test_cannot_pay_non_completed_ride(self) -> None:
        """Test that payment cannot be created for a non-completed ride."""
        user = UserFactory()
        ride = RideFactory(user=user, status='pending')
        with pytest.raises(ValueError, match='must be completed'):
            PaymentService.create_payment(ride, user, provider='cash')

    def test_cannot_pay_twice(self) -> None:
        """Test that a payment cannot be created for a ride that has already been paid."""
        user = UserFactory()
        ride = CompletedRideFactory(user=user, final_price=Decimal('115.0'))
        PaymentService.create_payment(ride, user, provider='cash')
        with pytest.raises(ValueError, match='already paid'):
            PaymentService.create_payment(ride, user, provider='cash')

    def test_confirm_payment(self) -> None:
        """Test confirming a payment."""
        user = UserFactory()
        ride = CompletedRideFactory(user=user, final_price=Decimal('115.0'))
        payment = Payment.objects.create(
            ride=ride,
            user=user,
            amount=Decimal('115.0'),
            currency='UAH',
            status='processing',
            payment_method='card',
            provider='liqpay',
        )
        confirmed = PaymentService.confirm_payment(str(payment.id))
        assert confirmed.status == Payment.Status.SUCCESS

    def test_create_payment_no_price(self) -> None:
        """Test missing price validation."""
        user = UserFactory()
        ride = CompletedRideFactory(user=user, final_price=Decimal('0.0'), estimated_price=Decimal('0.0'))
        with pytest.raises(ValueError, match='No price set for ride'):
            PaymentService.create_payment(ride, user, provider='cash')

    @patch('apps.payments.services.get_payment_provider')
    def test_create_payment_non_cash_provider_success(self, mock_get_payment_provider) -> None:
        """Test creating via a non-cash provider (mocked)."""
        user = UserFactory()
        ride = CompletedRideFactory(user=user, final_price=Decimal('100.0'))
        
        mock_provider_instance = Mock()
        mock_provider_instance.create_payment.return_value = {
            'transaction_id': 'mocked_tx_123',
            'data': {'mock': 'data'},
            'payment_url': 'http://mock.url',
        }
        mock_get_payment_provider.return_value = mock_provider_instance
        
        result = PaymentService.create_payment(ride, user, payment_method='card', provider='liqpay')
        
        assert result['status'] == 'processing'
        assert result['payment_url'] == 'http://mock.url'
        payment = result['payment']
        assert payment.status == Payment.Status.PROCESSING
        assert payment.provider_transaction_id == 'mocked_tx_123'
        assert payment.provider_data == {'mock': 'data'}

    @patch('apps.payments.services.get_payment_provider')
    def test_create_payment_non_cash_provider_exception(self, mock_get_payment_provider) -> None:
        """Test failure via a non-cash provider raises correct exception."""
        user = UserFactory()
        ride = CompletedRideFactory(user=user, final_price=Decimal('100.0'))
        
        mock_provider_instance = Mock()
        mock_provider_instance.create_payment.side_effect = Exception("Provider error")
        mock_get_payment_provider.return_value = mock_provider_instance
        
        with pytest.raises(Exception, match="Provider error"):
            PaymentService.create_payment(ride, user, payment_method='card', provider='liqpay')
            
        payment = Payment.objects.get(ride=ride)
        assert payment.status == Payment.Status.FAILED
        assert payment.error_message == "Provider error"

    def test_confirm_already_successful_payment(self) -> None:
        """Test confirming a payment that is already successful does nothing."""
        user = UserFactory()
        ride = CompletedRideFactory(user=user, final_price=Decimal('115.0'))
        payment = Payment.objects.create(
            ride=ride, user=user, amount=Decimal('115.0'), status=Payment.Status.SUCCESS
        )
        confirmed = PaymentService.confirm_payment(str(payment.id))
        assert confirmed == payment
        assert confirmed.status == Payment.Status.SUCCESS

    def test_confirm_payment_with_provider_transaction_id(self) -> None:
        """Test confirming a payment with provider transaction ID updates it."""
        user = UserFactory()
        ride = CompletedRideFactory(user=user, final_price=Decimal('115.0'))
        payment = Payment.objects.create(
            ride=ride, user=user, amount=Decimal('115.0'), status=Payment.Status.PROCESSING
        )
        confirmed = PaymentService.confirm_payment(str(payment.id), provider_transaction_id="new_tx_123")
        assert confirmed.status == Payment.Status.SUCCESS
        assert confirmed.provider_transaction_id == "new_tx_123"

    def test_fail_payment(self) -> None:
        """Test failing a payment."""
        user = UserFactory()
        ride = CompletedRideFactory(user=user, final_price=Decimal('115.0'))
        payment = Payment.objects.create(
            ride=ride, user=user, amount=Decimal('115.0'), status=Payment.Status.PROCESSING
        )
        failed = PaymentService.fail_payment(str(payment.id), error="Test error")
        assert failed.status == Payment.Status.FAILED
        assert failed.error_message == "Test error"

    def test_get_payment_for_ride(self) -> None:
        """Test retrieving payment for a ride."""
        user = UserFactory()
        ride = CompletedRideFactory(user=user, final_price=Decimal('115.0'))
        Payment.objects.create(ride=ride, user=user, amount=Decimal('115.0'), status=Payment.Status.PENDING)
        success_payment = Payment.objects.create(ride=ride, user=user, amount=Decimal('115.0'), status=Payment.Status.SUCCESS)
        
        payment = PaymentService.get_payment_for_ride(ride)
        assert payment == success_payment
