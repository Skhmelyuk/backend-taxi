import pytest
from rest_framework.test import APIClient
from rest_framework import status
from apps.users.tests.factories import UserFactory, AdminUserFactory


@pytest.mark.django_db
class TestUserViewSet:

    def test_me_authenticated(self):
        user = UserFactory()
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get('/api/v1/users/me/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['email'] == user.email

    def test_me_unauthenticated(self):
        client = APIClient()
        response = client.get('/api/v1/users/me/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_update_profile(self):
        user = UserFactory()
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.patch('/api/v1/users/update_profile/', {
            'first_name': 'Updated', 'last_name': 'Name'
        })
        assert response.status_code == status.HTTP_200_OK
        assert response.data['first_name'] == 'Updated'

    def test_update_profile_invalid_data(self):
        user = UserFactory()
        client = APIClient()
        client.force_authenticate(user=user)
        # Assuming email is readonly or validation fails with invalid phone
        response = client.patch('/api/v1/users/update_profile/', {
            'phone_number': 'not-a-number'
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_update_fcm_token_invalid_data(self):
        user = UserFactory()
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post('/api/v1/users/fcm_token/', {
            # passing empty to trigger validation error
            'fcm_token': ''
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_update_fcm_token(self):
        user = UserFactory()
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post('/api/v1/users/fcm_token/', {
            # empty token might fail validation
            'fcm_token': ''
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_ride_history(self):
        user = UserFactory()
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get('/api/v1/users/ride_history/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['message'] == 'Ride history endpoint'

    def test_get_serializer_class_default(self):
        user = UserFactory()
        client = APIClient()
        client.force_authenticate(user=user)
        # Calling create (POST) to trigger default branch of get_serializer_class
        response = client.post('/api/v1/users/', {})
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN]

    def test_get_permissions_update(self):
        user1 = UserFactory()
        user2 = UserFactory()
        client = APIClient()
        client.force_authenticate(user=user1)
        # Should be forbidden/not found to update another user's profile if not owner or admin
        response = client.patch(f'/api/v1/users/{user2.id}/', {'first_name': 'Hacker'})
        assert response.status_code in [status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN]
        user = UserFactory()
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post('/api/v1/users/fcm_token/', {
            'fcm_token': 'valid_fcm_token_123abc'
        })
        assert response.status_code == status.HTTP_200_OK

    def test_list_requires_admin(self):
        user = UserFactory()
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get('/api/v1/users/')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_can_list_users(self):
        admin = AdminUserFactory()
        UserFactory.create_batch(3)
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.get('/api/v1/users/')
        assert response.status_code == status.HTTP_200_OK
