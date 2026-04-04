import pytest
from decimal import Decimal
from apps.payments.providers.cash_provider import CashProvider
from apps.payments.providers.liqpay_provider import LiqPayProvider

class TestLiqPayProvider:
    """Tests for LiqPayProvider."""
    
    def setup_method(self):
        """Setup LiqPayProvider instance for tests."""
        self.provider = LiqPayProvider()
        self.provider.public_key = "test_public"
        self.provider.private_key = "test_private"
        self.provider.sandbox = True

    def test_encode_data(self):
        """Test encoding data to base64."""
        params = {'key': 'value'}
        encoded = self.provider._encode_data(params)
        assert isinstance(encoded, str)
        import base64
        import json
        assert json.loads(base64.b64decode(encoded.encode()).decode()) == params

    def test_create_payment(self):
        """Test creating a payment with LiqPayProvider."""
        result = self.provider.create_payment(
            amount=Decimal('100.50'),
            currency='UAH',
            description='Test ride',
            order_id='test_order_123',
            callback_url='http://example.com'
        )
        assert 'payment_url' in result
        assert 'transaction_id' in result
        assert result['transaction_id'] == 'test_order_123'
        assert 'data' in result
        assert 'data' in result['data']
        assert 'signature' in result['data']
        assert result['payment_url'].startswith("https://www.liqpay.ua/api/3/checkout?")

    def test_verify_payment(self):
        """Test verifying a payment with LiqPayProvider."""
        result = self.provider.verify_payment('test_transaction_123')
        assert result == {'status': 'unknown', 'transaction_id': 'test_transaction_123'}

    def test_refund_payment(self):
        """Test refunding a payment with LiqPayProvider."""
        result = self.provider.refund_payment('test_transaction_123', Decimal('50.00'))
        assert result == {'refund_id': None, 'status': 'processing'}

    def test_verify_callback_exception(self):
        """Test that verify_callback handles exceptions and returns False."""
        # Pass something that causes an exception in _sign or so, to trigger except Exception: return False
        # Passing None for data to cause AttributeError inside _sign since it expects a str
        result = self.provider.verify_callback({'data': None}, 'dummy_signature')
        assert result is False


class TestCashProvider:
    """Tests for CashProvider."""
    def setup_method(self):
        """Setup CashProvider instance for tests."""
        self.provider = CashProvider()

    def test_create_payment(self):
        """Test creating a cash payment."""
        result = self.provider.create_payment(
            amount=Decimal('100.00'),
            currency='UAH',
            description='Test ride',
            order_id='test_order_123',
            callback_url='http://example.com'
        )
        assert result == {
            'payment_url': None,
            'transaction_id': 'cash_test_order_123',
            'data': {'method': 'cash'},
        }

    def test_verify_payment(self):
        """Test verifying a cash payment."""
        transaction_id = 'cash_test_123'
        result = self.provider.verify_payment(transaction_id)
        assert result == {
            'status': 'success',
            'transaction_id': transaction_id
        }

    def test_refund_payment(self):
        """Test refunding a cash payment."""
        transaction_id = 'cash_test_123'
        result = self.provider.refund_payment(transaction_id, Decimal('100.00'))
        assert result == {
            'refund_id': f'refund_{transaction_id}',
            'status': 'success',
        }

    def test_verify_callback(self):
        """Test verifying callback data."""
        result = self.provider.verify_callback({'some': 'data'}, 'signature')
        assert result is True


class TestPaymentProviderFactory:
    """Tests for get_payment_provider factory function."""
    
    def test_get_liqpay_provider(self):
        """Test retrieving LiqPayProvider from factory."""
        from apps.payments.providers.factory import get_payment_provider
        from apps.payments.providers.liqpay_provider import LiqPayProvider
        
        provider = get_payment_provider('liqpay')
        assert isinstance(provider, LiqPayProvider)

    def test_get_cash_provider(self):
        """Test retrieving CashProvider from factory."""
        from apps.payments.providers.factory import get_payment_provider
        
        provider = get_payment_provider('cash')
        assert isinstance(provider, CashProvider)

    def test_get_unknown_provider_raises_error(self):
        """Test that requesting an unknown provider raises ValueError."""
        from apps.payments.providers.factory import get_payment_provider
        
        with pytest.raises(ValueError, match="Unknown payment provider: unknown"):
            get_payment_provider('unknown')
