import pytest
from apps.notifications.models import Notification, Device, NotificationPreference
from apps.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestNotificationModel:
    """Tests for Notification model."""
    def test_create_notification(self):
        """Test creating a notification."""
        user = UserFactory()
        notif = Notification.objects.create(
            user=user,
            notification_type='ride_accepted',
            title='Ride Accepted',
            message='Your driver is on the way'
        )
        assert notif.is_read is False
        assert notif.read_at is None

    def test_mark_as_read(self):
        """Test marking a notification as read."""
        user = UserFactory()
        notif = Notification.objects.create(
            user=user, notification_type='ride_accepted',
            title='Test', message='Test'
        )
        notif.mark_as_read()
        assert notif.is_read is True
        assert notif.read_at is not None


@pytest.mark.django_db
class TestNotificationPreference:
    """Tests for NotificationPreference model."""
    def test_allows_ride_notifications(self):
        """Test that ride notifications are allowed."""
        user = UserFactory()
        pref = NotificationPreference.objects.create(
            user=user, ride_notifications=True, push_enabled=True
        )
        assert pref.allows_notification_type('ride_accepted') is True

    def test_disabled_push(self):
        """Test that notifications are not allowed if push is disabled."""
        user = UserFactory()
        pref = NotificationPreference.objects.create(
            user=user, push_enabled=False
        )
        assert pref.allows_notification_type('ride_accepted') is False