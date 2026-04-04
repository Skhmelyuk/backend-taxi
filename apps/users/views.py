"""
Views for users app.
"""

import logging
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from svix.webhooks import Webhook, WebhookVerificationError
from rest_framework import viewsets, status
from rest_framework.decorators import action, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated

from apps.users.models import User
from apps.users.serializers import (
    UserSerializer, UserDetailSerializer,
    UserUpdateSerializer, FCMTokenSerializer, UserListSerializer,
)
from apps.users.services import (
    handle_clerk_user_created,
    handle_clerk_user_deleted,
    handle_clerk_user_updated,
)
from core.permissions import IsAdminUser, IsOwnerOrAdmin

logger = logging.getLogger(__name__)


class UserViewSet(viewsets.ModelViewSet):
    """ViewSet for User model."""

    queryset = User.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return UserListSerializer
        elif self.action in ['update', 'partial_update', 'update_profile']:
            return UserUpdateSerializer
        elif self.action in ['retrieve', 'me']:
            return UserDetailSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated(), IsAdminUser()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsOwnerOrAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'role') and user.role == 'admin':
            return User.objects.all()
        return User.objects.filter(id=user.id)

    @action(detail=False, methods=['get'])
    def me(self, request):
        """GET /api/users/me/ — Current user profile."""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['patch'])
    def update_profile(self, request):
        """PATCH /api/users/update_profile/ — Update profile."""
        serializer = self.get_serializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            logger.info(f"User {request.user.email} updated profile")
            return Response(UserDetailSerializer(request.user).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def fcm_token(self, request):
        """POST /api/users/fcm_token/ — Update FCM token."""
        serializer = FCMTokenSerializer(data=request.data)
        if serializer.is_valid():
            request.user.fcm_token = serializer.validated_data['fcm_token']
            request.user.save(update_fields=['fcm_token'])
            logger.info(f"User {request.user.email} updated FCM token")
            return Response({'message': 'FCM token updated successfully'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def ride_history(self, request):
        """GET /api/users/ride_history/ — Ride history (Plan 04)."""
        return Response({'message': 'Ride history endpoint', 'rides': [], 'count': 0})

    @action(detail=False, methods=['delete'])
    def delete_account(self, request):
        """DELETE /api/users/delete_account/ — Soft delete account."""
        user = request.user
        user.is_active = False
        user.save(update_fields=['is_active'])
        logger.info(f"User {user.email} deleted their account")
        return Response({'message': 'Account deleted successfully'}, status=status.HTTP_204_NO_CONTENT)


@csrf_exempt
@require_http_methods(["POST"])
@permission_classes([AllowAny])
def clerk_webhook(request):
    """Webhook endpoint for Clerk events."""
    try:
        headers = {
            'svix-id': request.headers.get('svix-id', ''),
            'svix-timestamp': request.headers.get('svix-timestamp', ''),
            'svix-signature': request.headers.get('svix-signature', ''),
        }

        wh = Webhook(settings.CLERK_WEBHOOK_SECRET)
        payload = wh.verify(request.body, headers)

        event_type = payload.get('type')
        data = payload.get('data')

        logger.info("Received Clerk webhook: %s", event_type)

        if event_type == 'user.created':
            handle_clerk_user_created(data)
        elif event_type == 'user.updated':
            handle_clerk_user_updated(data)
        elif event_type == 'user.deleted':
            handle_clerk_user_deleted(data)
        else:
            logger.warning("Unknown event type: %s", event_type)

        return JsonResponse({'status': 'success'}, status=200)

    except WebhookVerificationError:
        logger.warning("Invalid webhook signature")
        return JsonResponse({'error': 'Invalid signature'}, status=401)
    except Exception as e:
        logger.error("Webhook error: %s", e, exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)
