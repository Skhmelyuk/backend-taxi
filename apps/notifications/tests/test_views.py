import pytest
from rest_framework.test import APIClient
from rest_framework import status
from apps.notifications.models import Notification
from apps.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestNotificationViewSet:
    """Tests for NotificationViewSet."""
    def test_list_notifications(self):
        """GET /api/v1/notifications/ — List user notifications."""
        user = UserFactory()
        Notification.objects.create(
            user=user, notification_type='ride_accepted',
            title='Test', message='Test'
        )
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get('/api/v1/notifications/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1 

    def test_mark_single_read(self):
        """POST /api/v1/notifications/{id}/mark_read/ — Mark single notification as read."""
        user = UserFactory()
        notif = Notification.objects.create(
            user=user, notification_type='ride_accepted',
            title='Test', message='Test'
        )
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post(f'/api/v1/notifications/{notif.id}/mark_read/')
        assert response.status_code == status.HTTP_200_OK
        notif.refresh_from_db()
        assert notif.is_read is True

    def test_mark_single_read_not_found(self):
        """POST /api/v1/notifications/{id}/mark_read/ — Handle notification not found."""
        user = UserFactory()
        client = APIClient()
        client.force_authenticate(user=user)
        import uuid
        fake_uuid = uuid.uuid4()
        response = client.post(f'/api/v1/notifications/{fake_uuid}/mark_read/')
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data['error'] == 'Notification not found'

    def test_mark_all_read(self):
        """POST /api/v1/notifications/mark_all_read/ — Mark all as read."""
        user = UserFactory()
        for _ in range(3):
            Notification.objects.create(
                user=user, notification_type='ride_accepted',
                title='T', message='M'
            )
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post('/api/v1/notifications/mark_all_read/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['marked_read'] == 3

    def test_unread_count(self):
        """GET /api/v1/notifications/unread_count/ — Get unread count."""
        user = UserFactory()
        Notification.objects.create(
            user=user, notification_type='ride_accepted',
            title='T', message='M', is_read=False
        )
        Notification.objects.create(
            user=user, notification_type='ride_accepted',
            title='T', message='M', is_read=True
        )
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get('/api/v1/notifications/unread_count/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['unread_count'] == 1

    def test_register_device(self):
        """POST /api/v1/notifications/register_device/ — Register FCM device token."""
        user = UserFactory()
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post('/api/v1/notifications/register_device/', {
            'fcm_token': 'valid_fcm_token_device_123abc',
            'device_type': 'android',
        })
        assert response.status_code == status.HTTP_201_CREATED

    def test_register_device_invalid_data(self):
        """POST /api/v1/notifications/register_device/ — Handle invalid data registration."""
        user = UserFactory()
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post('/api/v1/notifications/register_device/', {
            # Sending no data to trigger serializer error
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_get_preferences(self):
        """GET /api/v1/notifications/preferences/ — Get notification preferences."""
        user = UserFactory()
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get('/api/v1/notifications/preferences/')
        assert response.status_code == status.HTTP_200_OK
        assert 'push_enabled' in response.data

    def test_put_preferences_valid_data(self):
        """PATCH /api/v1/notifications/preferences/ — Update preferences with valid data."""
        user = UserFactory()
        client = APIClient()
        client.force_authenticate(user=user)
        # Ensure we have prefs
        client.get('/api/v1/notifications/preferences/')
        
        response = client.patch('/api/v1/notifications/preferences/', {
            'push_enabled': False,
            'email_enabled': True
        })
        assert response.status_code == status.HTTP_200_OK
        assert response.data['push_enabled'] is False

    def test_put_preferences_invalid_data(self):
        """PATCH /api/v1/notifications/preferences/ — Handle invalid data update."""
        user = UserFactory()
        client = APIClient()
        client.force_authenticate(user=user)
        # Ensure we have prefs
        client.get('/api/v1/notifications/preferences/')
        
        response = client.patch('/api/v1/notifications/preferences/', {
            'push_enabled': 'not-a-boolean'  # This should fail validation
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST
