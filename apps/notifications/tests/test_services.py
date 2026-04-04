import pytest
from unittest.mock import patch, PropertyMock
from apps.notifications.models import Notification
from apps.notifications.services import NotificationService
from apps.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestNotificationService:
    """Tests for NotificationService."""
    @patch('apps.notifications.services.fcm_service.FCMService.send_to_user')
    def test_send_notification_saved_to_db(self, mock_fcm):
        """Test that sending notification saves it to DB."""
        mock_fcm.return_value = {'success': 1, 'failure': 0}
        user = UserFactory()

        notif = NotificationService.send_notification(
            user=user, notification_type='ride_accepted',
            title='Test', message='Test message'
        )
        assert notif is not None
        assert Notification.objects.filter(user=user).count() == 1

    @patch('apps.notifications.services.fcm_service.FCMService.send_to_user')
    def test_send_ride_accepted(self, mock_fcm):
        """Test sending ride accepted notification."""
        mock_fcm.return_value = {'success': 1, 'failure': 0}
        user = UserFactory()
        notif = NotificationService.send_ride_accepted(user, 'ride-id', 'John Driver', 5)
        assert notif is not None
        assert notif.notification_type == 'ride_accepted'

    @patch('apps.notifications.services.fcm_service.FCMService.send_to_user')
    def test_get_user_notifications(self, mock_fcm):
        """Test retrieving user notifications."""
        mock_fcm.return_value = {'success': 1, 'failure': 0}
        user = UserFactory()
        for _ in range(3):
            NotificationService.send_notification(
                user=user, notification_type='ride_completed',
                title='Test', message='Test'
            )
        notifications = NotificationService.get_user_notifications(user)
        assert len(notifications) == 3

    @patch('apps.notifications.services.fcm_service.FCMService.send_to_user')
    def test_mark_all_read(self, mock_fcm):
        """Test marking all notifications as read."""
        mock_fcm.return_value = {'success': 1, 'failure': 0}
        user = UserFactory()
        for _ in range(3):
            NotificationService.send_notification(
                user=user, notification_type='ride_accepted',
                title='T', message='M'
            )
        count = NotificationService.mark_all_read(user)
        assert count == 3
        assert NotificationService.get_unread_count(user) == 0


@pytest.mark.django_db
class TestFCMService:
    """Tests for FCMService."""

    def setup_method(self):
        # Reset FCMService internal state before each test
        from apps.notifications.services.fcm_service import FCMService
        FCMService._app = None

    @patch('django.conf.settings.FIREBASE_CREDENTIALS_PATH', '')
    def test_get_app_no_credentials(self):
        """Test _get_app when credentials path is empty."""
        from apps.notifications.services.fcm_service import FCMService
        assert FCMService._get_app() is None

    @patch('django.conf.settings.FIREBASE_CREDENTIALS_PATH', 'dummy_path.json')
    @patch('firebase_admin.initialize_app')
    @patch('firebase_admin.credentials.Certificate')
    def test_get_app_success(self, mock_cert, mock_init):
        """Test _get_app successful initialization."""
        from apps.notifications.services.fcm_service import FCMService
        mock_init.return_value = 'mock_app'
        app = FCMService._get_app()
        assert app == 'mock_app'
        # Second call should return cached app
        assert FCMService._get_app() == 'mock_app'
        mock_init.assert_called_once()

    @patch('django.conf.settings.FIREBASE_CREDENTIALS_PATH', 'dummy_path.json')
    @patch('firebase_admin.initialize_app')
    @patch('firebase_admin.credentials.Certificate')
    def test_get_app_failure(self, mock_cert, mock_init):
        """Test _get_app initialization failure."""
        from apps.notifications.services.fcm_service import FCMService
        mock_init.side_effect = Exception("Test error")
        assert FCMService._get_app() is None

    @patch('apps.notifications.services.fcm_service.FCMService._get_app')
    def test_send_notification_no_app(self, mock_get_app):
        """Test send_notification when FCM app is not initialized."""
        mock_get_app.return_value = None
        from apps.notifications.services.fcm_service import FCMService
        assert FCMService.send_notification('token', 'Test', 'Body') is False

    @patch('firebase_admin.messaging.send')
    @patch('apps.notifications.services.fcm_service.FCMService._get_app')
    def test_send_notification_success(self, mock_get_app, mock_send):
        """Test send_notification successful send."""
        mock_get_app.return_value = 'dummy_app'
        from apps.notifications.services.fcm_service import FCMService
        assert FCMService.send_notification('token', 'Test', 'Body') is True
        mock_send.assert_called_once()

    @patch('firebase_admin.messaging.send')
    @patch('apps.notifications.services.fcm_service.FCMService._get_app')
    def test_send_notification_failure(self, mock_get_app, mock_send):
        """Test send_notification when sending fails."""
        mock_get_app.return_value = 'dummy_app'
        mock_send.side_effect = Exception("Test error")
        from apps.notifications.services.fcm_service import FCMService
        assert FCMService.send_notification('token', 'Test', 'Body') is False

    @patch('apps.notifications.services.fcm_service.FCMService._get_app')
    def test_send_multicast_no_app(self, mock_get_app):
        """Test send_multicast when FCM app is not initialized."""
        mock_get_app.return_value = None
        from apps.notifications.services.fcm_service import FCMService
        res = FCMService.send_multicast(['t1', 't2'], 'Test', 'Body')
        assert res == {'success': 0, 'failure': 2}

    @patch('firebase_admin.messaging.send_multicast')
    @patch('apps.notifications.services.fcm_service.FCMService._get_app')
    def test_send_multicast_success(self, mock_get_app, mock_send):
        """Test send_multicast successful send."""
        mock_get_app.return_value = 'dummy_app'
        mock_response = type('Response', (), {'success_count': 2, 'failure_count': 0})
        mock_send.return_value = mock_response
        from apps.notifications.services.fcm_service import FCMService
        res = FCMService.send_multicast(['t1', 't2'], 'Test', 'Body')
        assert res == {'success': 2, 'failure': 0}

    @patch('firebase_admin.messaging.send_multicast')
    @patch('apps.notifications.services.fcm_service.FCMService._get_app')
    def test_send_multicast_failure(self, mock_get_app, mock_send):
        """Test send_multicast when sending fails."""
        mock_get_app.return_value = 'dummy_app'
        mock_send.side_effect = Exception("Test error")
        from apps.notifications.services.fcm_service import FCMService
        res = FCMService.send_multicast(['t1', 't2'], 'Test', 'Body')
        assert res == {'success': 0, 'failure': 2}

    @patch('apps.notifications.services.fcm_service.FCMService.send_notification')
    def test_send_to_user_single_token(self, mock_send):
        """Test send_to_user with single device token."""
        mock_send.return_value = True
        from apps.notifications.services.fcm_service import FCMService
        user = UserFactory()
        user.fcm_token = 'single-token'
        res = FCMService.send_to_user(user, 'Test', 'Body')
        assert res == {'success': 1, 'failure': 0}
        mock_send.assert_called_once_with('single-token', 'Test', 'Body', None)

    @patch('apps.notifications.services.fcm_service.FCMService.send_multicast')
    def test_send_to_user_multiple_tokens(self, mock_multi):
        """Test send_to_user with multiple device tokens."""
        mock_multi.return_value = {'success': 2, 'failure': 0}
        from apps.notifications.services.fcm_service import FCMService
        user = UserFactory()
        
        # Patch the related manager directly on the class temporarily
        with patch.object(type(user), 'devices', new_callable=PropertyMock) as mock_devices:
            mock_manager = mock_devices.return_value
            mock_manager.filter.return_value.values_list.return_value = ['token1', 'token2']
            
            res = FCMService.send_to_user(user, 'Test', 'Body')
            
        assert res == {'success': 2, 'failure': 0}
        mock_multi.assert_called_once_with(['token1', 'token2'], 'Test', 'Body', None)
