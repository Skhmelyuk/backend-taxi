import json
import pytest
from unittest.mock import patch, MagicMock
from django.test import RequestFactory
from apps.users.views import clerk_webhook
from apps.users.models import User


@pytest.mark.django_db
class TestClerkWebhook:

    def test_invalid_signature_returns_401(self):
        factory = RequestFactory()
        request = factory.post(
            '/api/v1/users/webhooks/clerk/',
            data=json.dumps({'type': 'user.created', 'data': {}}),
            content_type='application/json'
        )
        response = clerk_webhook(request)
        assert response.status_code == 401

    @patch('apps.users.views.Webhook')
    def test_user_updated_event(self, mock_webhook_class, db):
        mock_wh = MagicMock()
        mock_wh.verify.return_value = {
            'type': 'user.updated',
            'data': {'id': 'clerk_user_123', 'first_name': 'Updated'}
        }
        mock_webhook_class.return_value = mock_wh

        factory = RequestFactory()
        request = factory.post(
            '/api/v1/users/webhooks/clerk/',
            data=json.dumps({}),
            content_type='application/json',
            HTTP_SVIX_ID='test',
            HTTP_SVIX_TIMESTAMP='1234567890',
            HTTP_SVIX_SIGNATURE='test_sig',
        )
        response = clerk_webhook(request)
        assert response.status_code == 200

    @patch('apps.users.views.Webhook')
    def test_user_deleted_event(self, mock_webhook_class, db):
        mock_wh = MagicMock()
        mock_wh.verify.return_value = {
            'type': 'user.deleted',
            'data': {'id': 'clerk_user_123'}
        }
        mock_webhook_class.return_value = mock_wh

        factory = RequestFactory()
        request = factory.post(
            '/api/v1/users/webhooks/clerk/',
            data=json.dumps({}),
            content_type='application/json',
            HTTP_SVIX_ID='test',
            HTTP_SVIX_TIMESTAMP='1234567890',
            HTTP_SVIX_SIGNATURE='test_sig',
        )
        response = clerk_webhook(request)
        assert response.status_code == 200

    @patch('apps.users.views.Webhook')
    def test_unknown_event(self, mock_webhook_class, db):
        mock_wh = MagicMock()
        mock_wh.verify.return_value = {
            'type': 'unknown.event',
            'data': {}
        }
        mock_webhook_class.return_value = mock_wh

        factory = RequestFactory()
        request = factory.post(
            '/api/v1/users/webhooks/clerk/',
            data=json.dumps({}),
            content_type='application/json',
            HTTP_SVIX_ID='test',
            HTTP_SVIX_TIMESTAMP='1234567890',
            HTTP_SVIX_SIGNATURE='test_sig',
        )
        response = clerk_webhook(request)
        assert response.status_code == 200

    @patch('apps.users.views.Webhook')
    def test_webhook_exception(self, mock_webhook_class, db):
        mock_wh = MagicMock()
        # Forcing an unknown error, an error from Webhook Verification Error, to be thrown
        mock_wh.verify.side_effect = Exception("Some weird error")
        mock_webhook_class.return_value = mock_wh

        factory = RequestFactory()
        request = factory.post(
            '/api/v1/users/webhooks/clerk/',
            data=json.dumps({}),
            content_type='application/json',
            HTTP_SVIX_ID='test',
            HTTP_SVIX_TIMESTAMP='1234567890',
            HTTP_SVIX_SIGNATURE='test_sig',
        )
        response = clerk_webhook(request)
        assert response.status_code == 500
        assert json.loads(response.content) == {'error': 'Some weird error'}

    @patch('apps.users.views.Webhook')
    def test_user_created_event(self, mock_webhook_class, db):
        mock_wh = MagicMock()
        mock_wh.verify.return_value = {
            'type': 'user.created',
            'data': {
                'id': 'clerk_user_123',
                'email_addresses': [
                    {'id': 'addr_1', 'email_address': 'new@example.com'}
                ],
                'primary_email_address_id': 'addr_1',
                'first_name': 'New',
                'last_name': 'User',
            }
        }
        mock_webhook_class.return_value = mock_wh

        factory = RequestFactory()
        request = factory.post(
            '/api/v1/users/webhooks/clerk/',
            data=json.dumps({}),
            content_type='application/json',
            HTTP_SVIX_ID='test',
            HTTP_SVIX_TIMESTAMP='1234567890',
            HTTP_SVIX_SIGNATURE='test_sig',
        )
        response = clerk_webhook(request)

        assert response.status_code == 200
        assert User.objects.filter(clerk_user_id='clerk_user_123').exists()