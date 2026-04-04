import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.notifications.models import Notification, Device, NotificationPreference
from apps.notifications.serializers import (
    NotificationSerializer, DeviceSerializer, RegisterDeviceSerializer,
    NotificationPreferenceSerializer,
)
from apps.notifications.services import NotificationService

logger = logging.getLogger(__name__)


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for Notification model."""

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """POST /api/v1/notifications/{id}/mark_read/ — Mark single notification as read."""
        try:
            notification = Notification.objects.get(id=pk, user=request.user)
            notification.mark_as_read()
            return Response(NotificationSerializer(notification).data)
        except Notification.DoesNotExist:
            return Response({'error': 'Notification not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """POST /api/v1/notifications/mark_all_read/ — Mark all as read."""
        count = NotificationService.mark_all_read(request.user)
        return Response({'marked_read': count})

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """GET /api/v1/notifications/unread_count/ — Get unread count."""
        count = NotificationService.get_unread_count(request.user)
        return Response({'unread_count': count})

    @action(detail=False, methods=['post'])
    def register_device(self, request):
        """POST /api/v1/notifications/register_device/ — Register FCM device token."""
        serializer = RegisterDeviceSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        fcm_token = serializer.validated_data['fcm_token']
        device_type = serializer.validated_data['device_type']

        device, created = Device.objects.get_or_create(
            fcm_token=fcm_token,
            defaults={
                'user': request.user,
                'device_type': device_type,
                'is_active': True,
            }
        )

        if not created:
            device.user = request.user
            device.is_active = True
            device.save(update_fields=['user', 'is_active'])

        logger.info(f"Device registered: {request.user.email} ({device_type})")
        return Response(DeviceSerializer(device).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=False, methods=['get', 'patch'])
    def preferences(self, request):
        """GET/PATCH /api/v1/notifications/preferences/ — Notification preferences."""
        prefs, _ = NotificationPreference.objects.get_or_create(user=request.user)

        if request.method == 'GET':
            return Response(NotificationPreferenceSerializer(prefs).data)

        serializer = NotificationPreferenceSerializer(prefs, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

