import pytest
from unittest.mock import patch, MagicMock
from celery.exceptions import Retry
from apps.notifications.tasks import (
    cleanup_old_notifications, 
    send_push_notification,
    send_bulk_notification,
    send_promo_notifications
)


@pytest.mark.django_db
class TestNotificationCeleryTasks:
    """Tests for notification-related Celery tasks."""
    @patch('apps.notifications.services.fcm_service.FCMService.send_to_user')
    def test_send_push_notification(self, mock_fcm):
        """Test sending push notification task."""
        mock_fcm.return_value = {'success': 1, 'failure': 0}
        from apps.users.tests.factories import UserFactory
        user = UserFactory()
        result = send_push_notification.apply(args=[
            str(user.id), 'ride_accepted', 'Test', 'Message'
        ])
        assert result.result['sent'] is True

    @patch('apps.notifications.services.NotificationService.send_notification')
    def test_send_push_notification_retry(self, mock_send):
        """Test sending push notification triggers retry on exception."""
        mock_send.side_effect = Exception("FCM is down")
        from apps.users.tests.factories import UserFactory
        user = UserFactory()
        
        with patch('apps.notifications.tasks.send_push_notification.retry', side_effect=Retry('Retrying')):
            with pytest.raises(Retry):
                send_push_notification(str(user.id), 'ride_accepted', 'Test', 'Message')
        mock_send.assert_called_once()

    @patch('apps.notifications.services.NotificationService.send_notification')
    def test_send_bulk_notification(self, mock_send):
        """Test bulk push notification handles successes and failures."""
        from apps.users.tests.factories import UserFactory
        user1 = UserFactory()
        user2 = UserFactory()
        user3 = UserFactory()
        
        # Make the second call fail
        mock_send.side_effect = [None, Exception("Failed"), None]
        
        result = send_bulk_notification.apply(args=[
            [str(user1.id), str(user2.id), str(user3.id)],
            'general_alert', 'Title', 'Message'
        ])
        
        assert result.result['success'] == 2
        assert result.result['failed'] == 1
        assert mock_send.call_count == 3

    @patch('apps.notifications.services.NotificationService.send_notification')
    def test_send_promo_notifications_no_promos(self, mock_send):
        """Test promo notifications when there are no active promos."""
        result = send_promo_notifications.apply()
        assert result.result['sent'] == 0
        mock_send.assert_not_called()

    @patch('apps.notifications.services.NotificationService.send_notification')
    def test_send_promo_notifications(self, mock_send):
        """Test promo notifications sends and handles failures."""
        from apps.payments.models import PromoCode
        from apps.users.tests.factories import UserFactory
        
        PromoCode.objects.create(code='TESTPROMO', discount_percent=10, is_active=True)
        user1 = UserFactory(is_active=True)
        user2 = UserFactory(is_active=True)
        
        # Second one fails
        mock_send.side_effect = [None, Exception("Fail")]
        
        result = send_promo_notifications.apply()
        
        assert result.result['sent'] == 1
        assert mock_send.call_count == 2

    def test_cleanup_old_notifications(self):
        """Test cleanup of old notifications."""
        from apps.notifications.models import Notification
        from apps.users.tests.factories import UserFactory
        from django.utils import timezone
        from datetime import timedelta

        user = UserFactory()
        old_notif = Notification.objects.create(
            user=user, notification_type='ride_completed',
            title='Old', message='Old notification', is_read=True
        )
        Notification.objects.filter(id=old_notif.id).update(
            created_at=timezone.now() - timedelta(days=31)
        )

        result = cleanup_old_notifications.apply()
        assert result.result['deleted'] >= 1