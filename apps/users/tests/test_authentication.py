import pytest
from unittest.mock import MagicMock, patch

from core.authentication import ClerkAuthentication
from apps.users.models import User


@pytest.mark.django_db
class TestClerkAuthentication:

    def test_no_auth_header(self):
        """Returns None when Authorization header is missing."""
        auth = ClerkAuthentication()
        request = MagicMock()
        request.META = {}
        assert auth.authenticate(request) is None

    def test_invalid_format(self):
        """Returns None when Authorization header has invalid format."""
        auth = ClerkAuthentication()
        request = MagicMock()
        request.META = {'HTTP_AUTHORIZATION': 'InvalidFormat token'}
        # Returns None to pass to next authentication class
        assert auth.authenticate(request) is None

    @patch('core.authentication.ClerkAuthentication._verify_token')
    @patch('core.authentication.ClerkAuthentication._get_or_create_user')
    def test_successful_auth(self, mock_get_user, mock_verify):
        """Returns (user, None) on successful authentication."""
        mock_payload = {'sub': 'clerk_user_123', 'email': 'test@example.com'}
        mock_verify.return_value = mock_payload
        user = User.objects.create_user(
            email='test@example.com', clerk_user_id='clerk_user_123'
        )
        mock_get_user.return_value = user

        auth = ClerkAuthentication()
        request = MagicMock()
        request.META = {'HTTP_AUTHORIZATION': 'Bearer valid_token'}
        result = auth.authenticate(request)

        assert result is not None
        assert result[0] == user
        assert result[1] is None
        mock_verify.assert_called_once_with('valid_token')
        mock_get_user.assert_called_once_with(mock_payload)
