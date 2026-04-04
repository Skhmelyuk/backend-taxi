"""
Tests for payment webhook handlers.
"""

import json
import base64
from unittest.mock import patch, Mock
import pytest
from django.test import RequestFactory

from apps.payments.views import fondy_callback, liqpay_callback

@pytest.mark.django_db
class TestLiqPayCallback:
    """Tests for LiqPay webhook handler."""
    def test_invalid_signature(self) -> None:
        factory = RequestFactory()
        request = factory.post(
            '/api/v1/payments/callback/liqpay/',
            data={'data': 'test', 'signature': 'invalid'},
            content_type='application/x-www-form-urlencoded',
        )
        response = liqpay_callback(request)
        assert response.status_code == 401

    @patch('apps.payments.services.PaymentService.confirm_payment')
    @patch('apps.payments.providers.liqpay_provider.LiqPayProvider.verify_callback', return_value=True)
    def test_valid_signature_success(self, mock_verify, mock_confirm) -> None:
        """Test that valid signature with success status calls confirm_payment."""
        factory = RequestFactory()
        
        payload = {'order_id': '123', 'status': 'success', 'payment_id': 'tx_123'}
        encoded_data = base64.b64encode(json.dumps(payload).encode()).decode()
        
        request = factory.post(
            '/api/v1/payments/callback/liqpay/',
            data={'data': encoded_data, 'signature': 'valid'},
        )
        response = liqpay_callback(request)
        assert response.status_code == 200
        mock_confirm.assert_called_once_with('123', 'tx_123')

    @patch('apps.payments.services.PaymentService.fail_payment')
    @patch('apps.payments.providers.liqpay_provider.LiqPayProvider.verify_callback', return_value=True)
    def test_valid_signature_failure(self, mock_verify, mock_fail) -> None:
        """Test that valid signature with failure status calls fail_payment."""
        factory = RequestFactory()
        
        payload = {'order_id': '123', 'status': 'failure'}
        encoded_data = base64.b64encode(json.dumps(payload).encode()).decode()
        
        request = factory.post(
            '/api/v1/payments/callback/liqpay/',
            data={'data': encoded_data, 'signature': 'valid'},
        )
        response = liqpay_callback(request)
        assert response.status_code == 200
        mock_fail.assert_called_once_with('123', 'Provider status: failure')

    @patch('apps.payments.providers.liqpay_provider.LiqPayProvider.verify_callback', side_effect=Exception('Test Error'))
    def test_exception(self, mock_verify) -> None:
        """Test that an unexpected exception returns a 500 response."""
        factory = RequestFactory()
        request = factory.post('/api/v1/payments/callback/liqpay/', data={})
        response = liqpay_callback(request)
        assert response.status_code == 500

@pytest.mark.django_db
class TestFondyCallback:
    """Tests for Fondy webhook handler."""
    def test_invalid_json(self) -> None:
        factory = RequestFactory()
        request = factory.post(
            '/api/v1/payments/callback/fondy/',
            data='not json',
            content_type='application/json',
        )
        response = fondy_callback(request)
        assert response.status_code == 400

    @patch('apps.payments.services.PaymentService.confirm_payment')
    def test_approved(self, mock_confirm) -> None:
        """Test that approved status calls confirm_payment."""
        factory = RequestFactory()
        
        payload = {'response': {'order_id': '456', 'order_status': 'approved'}}
        request = factory.post(
            '/api/v1/payments/callback/fondy/',
            data=json.dumps(payload),
            content_type='application/json',
        )
        response = fondy_callback(request)
        assert response.status_code == 200
        mock_confirm.assert_called_once_with('456')

    @patch('apps.payments.services.PaymentService.fail_payment')
    def test_declined(self, mock_fail) -> None:
        """Test that declined status calls fail_payment."""
        factory = RequestFactory()
        
        payload = {'response': {'order_id': '456', 'order_status': 'declined'}}
        request = factory.post(
            '/api/v1/payments/callback/fondy/',
            data=json.dumps(payload),
            content_type='application/json',
        )
        response = fondy_callback(request)
        assert response.status_code == 200
        mock_fail.assert_called_once_with('456', 'Provider status: declined')

    @patch('json.loads', side_effect=Exception('Test Error'))
    def test_exception(self, mock_loads) -> None:
        """Test that an unexpected exception returns a 500 response."""
        factory = RequestFactory()
        request = factory.post(
            '/api/v1/payments/callback/fondy/',
            data='{}',
            content_type='application/json',
        )
        response = fondy_callback(request)
        assert response.status_code == 500
