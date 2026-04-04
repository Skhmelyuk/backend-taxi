import pytest
from apps.users.models import User
from apps.users.services import (
    handle_clerk_user_created,
    handle_clerk_user_updated,
    handle_clerk_user_deleted
)


@pytest.mark.django_db
class TestClerkServices:

    def test_handle_clerk_user_created_no_email(self):
        """Test user.created event when email is missing."""
        data = {
            'id': 'clerk_no_email',
            'email_addresses': [],
            'primary_email_address_id': None
        }
        handle_clerk_user_created(data)
        assert not User.objects.filter(clerk_user_id='clerk_no_email').exists()

    def test_handle_clerk_user_created_already_exists(self):
        """Test user.created event when user already exists."""
        User.objects.create_user(
            email='existing@test.com',
            clerk_user_id='clerk_existing'
        )
        data = {
            'id': 'clerk_existing',
            'email_addresses': [{'id': 'addr_1', 'email_address': 'existing@test.com'}],
            'primary_email_address_id': 'addr_1',
            'first_name': 'NewName'
        }
        handle_clerk_user_created(data)
        user = User.objects.get(clerk_user_id='clerk_existing')
        # Name should not be updated since we only log that it exists
        assert user.first_name == ''

    def test_handle_clerk_user_updated_success(self):
        """Test successful user update from webhook."""
        user = User.objects.create_user(
            email='update@test.com',
            clerk_user_id='clerk_update',
            first_name='OldFirst',
            last_name='OldLast'
        )
        data = {
            'id': 'clerk_update',
            'first_name': 'NewFirst',
            'last_name': 'NewLast'
        }
        handle_clerk_user_updated(data)
        
        user.refresh_from_db()
        assert user.first_name == 'NewFirst'
        assert user.last_name == 'NewLast'

    def test_handle_clerk_user_updated_not_found(self):
        """Test user update from webhook when user doesn't exist."""
        data = {
            'id': 'clerk_missing_update',
            'first_name': 'NewFirst'
        }
        # Shouldn't raise any exception, just logs a warning
        handle_clerk_user_updated(data)

    def test_handle_clerk_user_deleted_success(self):
        """Test successful user deactivation from webhook."""
        user = User.objects.create_user(
            email='delete@test.com',
            clerk_user_id='clerk_delete',
        )
        assert user.is_active is True
        
        data = {
            'id': 'clerk_delete'
        }
        handle_clerk_user_deleted(data)
        
        user.refresh_from_db()
        assert user.is_active is False

    def test_handle_clerk_user_deleted_not_found(self):
        """Test user deactivation from webhook when user doesn't exist."""
        data = {
            'id': 'clerk_missing_delete',
        }
        # Shouldn't raise any exception, just logs a warning
        handle_clerk_user_deleted(data)