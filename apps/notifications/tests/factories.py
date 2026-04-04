import factory
from factory.django import DjangoModelFactory
from apps.notifications.models import Notification, Device, NotificationPreference
from apps.users.tests.factories import UserFactory


class NotificationFactory(DjangoModelFactory):
    """Factory for Notification model."""
    class Meta:
        model = Notification

    user = factory.SubFactory(UserFactory)
    notification_type = Notification.Type.RIDE_ACCEPTED
    title = 'Driver Found!'
    message = 'John is on the way. ETA: 5 min'
    is_read = False


class ReadNotificationFactory(NotificationFactory):
    """Factory for read Notification."""
    is_read = True


class DeviceFactory(DjangoModelFactory):
    """Factory for Device model."""
    class Meta:
        model = Device

    user = factory.SubFactory(UserFactory)
    device_type = Device.DeviceType.ANDROID
    fcm_token = factory.Sequence(lambda n: f'fcm_token_{n:010d}_valid_token_string_here')
    is_active = True


class NotificationPreferenceFactory(DjangoModelFactory):
    """Factory for NotificationPreference model."""
    class Meta:
        model = NotificationPreference

    user = factory.SubFactory(UserFactory)
    ride_notifications = True
    payment_notifications = True
    promo_notifications = True
    push_enabled = True
