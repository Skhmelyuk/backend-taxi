import pytest
from rest_framework.test import APIClient
from rest_framework import status
from apps.users.tests.factories import UserFactory, AdminUserFactory, DriverUserFactory
from apps.users.models import User
from apps.users.services import handle_clerk_user_created


@pytest.mark.django_db
class TestUserAPIIntegration:
    """Integration tests for User API using project fixtures."""

    def test_user_registration_flow(self):
        """Test complete user registration via webhook."""

        data = {
            'id': 'clerk_test_001',
            'email_addresses': [{'id': 'addr_1', 'email_address': 'integration@test.com'}],
            'primary_email_address_id': 'addr_1',
            'first_name': 'Integration',
            'last_name': 'Test',
        }
        handle_clerk_user_created(data)
        user = User.objects.get(clerk_user_id='clerk_test_001')
        assert user.email == 'integration@test.com'
        assert user.first_name == 'Integration'

    def test_user_profile_update_flow(self, authenticated_client):
        """Test complete profile update using fixture."""
        client, user = authenticated_client

        response = client.patch('/api/v1/users/update_profile/', {
            'first_name': 'Updated',
            'last_name': 'Name',
            'phone_number': '+380501234567',
        })
        assert response.status_code == status.HTTP_200_OK
        assert response.data['first_name'] == 'Updated'

        user.refresh_from_db()
        assert user.first_name == 'Updated'

    def test_admin_can_manage_users(self, admin_client, user_factory):
        """Test admin access using admin_client fixture."""
        client, admin = admin_client
        users = user_factory.create_batch(3)

        list_response = client.get('/api/v1/users/')
        assert list_response.status_code == status.HTTP_200_OK

    def test_regular_user_cannot_list_users(self, authenticated_client):
        """Test permission denial using authenticated_client."""
        client, user = authenticated_client
        response = client.get('/api/v1/users/')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_account_soft_delete(self, authenticated_client):
        """Test soft delete logic."""
        client, user = authenticated_client

        response = client.delete('/api/v1/users/delete_account/')
        assert response.status_code == status.HTTP_204_NO_CONTENT

        user.refresh_from_db()
        assert user.is_active is False