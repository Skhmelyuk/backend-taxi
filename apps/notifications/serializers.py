"""
Serializers for notifications app.
"""

from rest_framework import serializers
from apps.notifications.models import Notification, Device, NotificationPreference


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for Notification model."""
    class Meta:
        model = Notification
        fields = [
            'id', 'notification_type', 'title', 'message',
            'data', 'is_read', 'read_at', 'created_at',
        ]
        read_only_fields = fields


class DeviceSerializer(serializers.ModelSerializer):
    """Serializer for Device model."""
    class Meta:
        model = Device
        fields = ['id', 'device_type', 'fcm_token', 'is_active', 'created_at']
        read_only_fields = ['id', 'is_active', 'created_at']


class RegisterDeviceSerializer(serializers.Serializer):
    """Serializer for registering a new device."""
    fcm_token = serializers.CharField(required=True, min_length=10)
    device_type = serializers.ChoiceField(choices=Device.DeviceType.choices)


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """Serializer for NotificationPreference model."""
    class Meta:
        model = NotificationPreference
        fields = [
            'id', 'ride_notifications', 'payment_notifications',
            'promo_notifications', 'push_enabled', 'email_enabled',
        ]
        read_only_fields = ['id']
