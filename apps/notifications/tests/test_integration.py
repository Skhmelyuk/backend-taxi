import pytest
from unittest.mock import patch
from rest_framework.test import APIClient
from rest_framework import status
from apps.notifications.models import Notification, Device
from apps.notifications.services import NotificationService
from apps.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestNotificationIntegration:
    """Integration tests for notification flow: sending, listing, marking read."""
    @patch('apps.notifications.services.fcm_service.FCMService.send_to_user')
    def test_full_notification_flow(self, mock_fcm):
        """Test full notification send → list → mark read flow."""
        mock_fcm.return_value = {'success': 1, 'failure': 0}
        user = UserFactory()
        client = APIClient()
        client.force_authenticate(user=user)

        # 1. Register device
        device_resp = client.post('/api/v1/notifications/register_device/', {
            'fcm_token': 'valid_fcm_token_test_device_001',
            'device_type': 'android',
        })
        assert device_resp.status_code == status.HTTP_201_CREATED

        # 2. Send notification
        notif = NotificationService.send_ride_accepted(user, 'ride-id', 'John', 5)
        assert notif is not None

        # 3. Get unread count
        count_resp = client.get('/api/v1/notifications/unread_count/')
        assert count_resp.data['unread_count'] == 1

        # 4. List
        list_resp = client.get('/api/v1/notifications/')
        assert list_resp.status_code == status.HTTP_200_OK
        assert len(list_resp.data['results']) == 1

        # 5. Mark single read
        mark_resp = client.post(f'/api/v1/notifications/{notif.id}/mark_read/')
        assert mark_resp.status_code == status.HTTP_200_OK
        assert mark_resp.data['is_read'] is True

        # 6. Verify unread count
        count_resp2 = client.get('/api/v1/notifications/unread_count/')
        assert count_resp2.data['unread_count'] == 0

    @patch('apps.notifications.services.fcm_service.FCMService.send_to_user')
    def test_notification_preferences_filter(self, mock_fcm):
        """Test that disabled preferences prevent notification sending."""
        mock_fcm.return_value = {'success': 1, 'failure': 0}
        from apps.notifications.models import NotificationPreference
        user = UserFactory()
        # Disable promo notifications
        NotificationPreference.objects.create(
            user=user, promo_notifications=False, push_enabled=True
        )

        notif = NotificationService.send_notification(
            user=user,
            notification_type='promo_available',
            title='Promo!',
            message='Special offer'
        )
        assert notif is None  # Should not be saved

    def test_device_deduplication(self):
        """Test that registering same FCM token updates existing device."""
        user = UserFactory()
        other_user = UserFactory()
        client = APIClient()
        client.force_authenticate(user=user)

        token = 'shared_fcm_token_device_abc123_long_enough'

        # Register with user
        r1 = client.post('/api/v1/notifications/register_device/', {
            'fcm_token': token, 'device_type': 'android'
        })
        assert r1.status_code == status.HTTP_201_CREATED

        # Register same token with other_user
        client2 = APIClient()
        client2.force_authenticate(user=other_user)
        r2 = client2.post('/api/v1/notifications/register_device/', {
            'fcm_token': token, 'device_type': 'android'
        })
        assert r2.status_code == status.HTTP_200_OK

        # Token should be owned by other_user now
        assert Device.objects.filter(fcm_token=token, user=other_user).exists()
