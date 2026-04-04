from unittest.mock import patch, Mock
import pytest
from decimal import Decimal
from apps.payments.models import Payment, Refund
from apps.payments.services import RefundService, PaymentService
from apps.rides.tests.factories import CompletedRideFactory
from apps.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestRefundService:
    """Tests for RefundService."""
    def _create_paid_ride(self):
        """Helper to create a completed ride with a successful payment."""
        user = UserFactory()
        ride = CompletedRideFactory(user=user, final_price=Decimal('100.0'))
        result = PaymentService.create_payment(ride, user, payment_method='cash', provider='cash')
        return result['payment'], user, ride

    def test_refund_cash_payment(self):
        """Test refunding a cash payment."""
        payment, user, ride = self._create_paid_ride()
        refund = RefundService.create_refund(str(payment.id), Decimal('100.0'), 'Driver no show')
        assert refund.status == 'success'
        payment.refresh_from_db()
        assert payment.status == Payment.Status.REFUNDED

    def test_refund_exceeds_payment(self):
        """Test refund amount exceeds original payment."""
        payment, user, ride = self._create_paid_ride()
        with pytest.raises(ValueError, match='exceeds payment amount'):
            RefundService.create_refund(str(payment.id), Decimal('200.0'), 'Test')

    def test_refund_non_successful_payment(self):
        """Test refunding a payment that is not successful."""
        user = UserFactory()
        ride = CompletedRideFactory(user=user)
        payment = Payment.objects.create(
            ride=ride, user=user, amount=Decimal('100.0'),
            currency='UAH', status='pending',
            payment_method='card', provider='liqpay'
        )
        with pytest.raises(ValueError, match='Cannot refund'):
            RefundService.create_refund(str(payment.id), Decimal('50.0'), 'Test')

    @patch('apps.payments.services.get_payment_provider')
    def test_refund_non_cash_provider_success(self, mock_get_payment_provider):
        """Test refunding a non-cash payment successfully."""
        user = UserFactory()
        ride = CompletedRideFactory(user=user, final_price=Decimal('100.0'))
        payment = Payment.objects.create(
            ride=ride, user=user, amount=Decimal('100.0'), status=Payment.Status.SUCCESS,
            provider='liqpay', provider_transaction_id='tx_123'
        )
        
        mock_provider_instance = Mock()
        mock_provider_instance.refund_payment.return_value = {'refund_id': 'ref_123'}
        
        mock_get_payment_provider.return_value = mock_provider_instance
        
        refund = RefundService.create_refund(str(payment.id), Decimal('50.0'), 'Test')
        assert refund.provider_refund_id == 'ref_123'

    @patch('apps.payments.services.get_payment_provider')
    def test_refund_non_cash_provider_exception(self, mock_get_payment_provider):
        """Test refunding a non-cash payment when provider raises an exception."""
        user = UserFactory()
        ride = CompletedRideFactory(user=user, final_price=Decimal('100.0'))
        payment = Payment.objects.create(
            ride=ride, user=user, amount=Decimal('100.0'), status=Payment.Status.SUCCESS,
            provider='liqpay', provider_transaction_id='tx_123'
        )
        
        mock_provider_instance = Mock()
        mock_provider_instance.refund_payment.side_effect = Exception("Refund failed")
        
        mock_get_payment_provider.return_value = mock_provider_instance
        
        with pytest.raises(Exception, match='Refund failed'):
            RefundService.create_refund(str(payment.id), Decimal('50.0'), 'Test')
            
        refund = Refund.objects.get(payment=payment)
        assert refund.status == 'failed'

    def test_get_refund_status(self):
        """Test retrieving refund status."""
        payment, user, ride = self._create_paid_ride()
        refund = RefundService.create_refund(str(payment.id), Decimal('100.0'), 'Driver no show')
        
        status = RefundService.get_refund_status(str(refund.id))
        assert status['id'] == str(refund.id)
        assert status['status'] == 'success'
        assert status['amount'] == 100.0
        assert status['reason'] == 'Driver no show'