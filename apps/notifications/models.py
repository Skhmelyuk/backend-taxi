import uuid
from django.db import models
from django.utils import timezone


class Notification(models.Model):
    """User notifications for ride events, payments, promotions, etc."""
    class Type(models.TextChoices):
        RIDE_CREATED = 'ride_created', 'Ride Created'
        RIDE_ACCEPTED = 'ride_accepted', 'Ride Accepted'
        RIDE_STARTED = 'ride_started', 'Ride Started'
        RIDE_COMPLETED = 'ride_completed', 'Ride Completed'
        RIDE_CANCELLED = 'ride_cancelled', 'Ride Cancelled'
        DRIVER_ARRIVED = 'driver_arrived', 'Driver Arrived'
        PAYMENT_SUCCESS = 'payment_success', 'Payment Success'
        PAYMENT_FAILED = 'payment_failed', 'Payment Failed'
        REFUND_PROCESSED = 'refund_processed', 'Refund Processed'
        NEW_RIDE_REQUEST = 'new_ride_request', 'New Ride Request'
        PROMO_AVAILABLE = 'promo_available', 'Promo Available'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        'users.User', on_delete=models.CASCADE, related_name='notifications'
    )
    notification_type = models.CharField(max_length=50, choices=Type.choices, db_index=True)
    title = models.CharField(max_length=255)
    message = models.TextField()
    data = models.JSONField(default=dict, blank=True)
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['notification_type']),
            models.Index(fields=['is_read']),
        ]
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'

    def __str__(self):
        return f"{self.notification_type} - {self.user.email}"

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])


class Device(models.Model):
    """User devices for push notifications."""
    class DeviceType(models.TextChoices):
        ANDROID = 'android', 'Android'
        IOS = 'ios', 'iOS'
        WEB = 'web', 'Web'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        'users.User', on_delete=models.CASCADE, related_name='devices'
    )
    device_type = models.CharField(max_length=20, choices=DeviceType.choices)
    fcm_token = models.TextField(unique=True, db_index=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'devices'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['fcm_token']),
        ]
        verbose_name = 'Device'

    def __str__(self):
        return f"{self.device_type} - {self.user.email}"


class NotificationPreference(models.Model):
    """User notification preferences."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        'users.User', on_delete=models.CASCADE, related_name='notification_preferences'
    )
    ride_notifications = models.BooleanField(default=True)
    payment_notifications = models.BooleanField(default=True)
    promo_notifications = models.BooleanField(default=True)
    push_enabled = models.BooleanField(default=True)
    email_enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'notification_preferences'
        verbose_name = 'Notification Preference'

    def __str__(self):
        return f"Preferences for {self.user.email}"

    def allows_notification_type(self, notification_type: str) -> bool:
        """Check if user allows a specific notification type."""
        ride_types = ['ride_created', 'ride_accepted', 'ride_started',
                      'ride_completed', 'ride_cancelled', 'driver_arrived', 'new_ride_request']
        payment_types = ['payment_success', 'payment_failed', 'refund_processed']
        promo_types = ['promo_available']

        if notification_type in ride_types:
            return self.ride_notifications and self.push_enabled
        elif notification_type in payment_types:
            return self.payment_notifications and self.push_enabled
        elif notification_type in promo_types:
            return self.promo_notifications and self.push_enabled
        return self.push_enabled