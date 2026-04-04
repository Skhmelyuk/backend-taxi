import logging
from typing import Optional, Dict
from django.db import transaction
from apps.notifications.models import Notification, NotificationPreference
from apps.notifications.services.fcm_service import FCMService
from apps.users.models import User

logger = logging.getLogger(__name__)


class NotificationService:

    @staticmethod
    @transaction.atomic
    def send_notification(
        user: User,
        notification_type: str,
        title: str,
        message: str,
        data: Optional[Dict] = None,
        send_push: bool = True,
        save_to_db: bool = True
    ) -> Optional[Notification]:
        """
        Send notification to user (push + save to DB).
        
        Returns:
            Notification instance if saved, None otherwise
        """
        # Check user preferences
        try:
            prefs = user.notification_preferences
            if not prefs.allows_notification_type(notification_type):
                logger.info(f"User {user.email} disabled {notification_type} notifications")
                return None
        except NotificationPreference.DoesNotExist:
            pass  # No preferences = allow all

        # Save to DB
        notification = None
        if save_to_db:
            notification = Notification.objects.create(
                user=user,
                notification_type=notification_type,
                title=title,
                message=message,
                data=data or {},
            )

        # Send push notification
        if send_push:
            FCMService.send_to_user(user, title, message, data)

        logger.info(f"Notification sent to {user.email}: {notification_type}")
        return notification

    @staticmethod
    def send_ride_accepted(user: User, ride_id: str, driver_name: str, eta_minutes: int):
        """Notify user that driver accepted their ride."""
        return NotificationService.send_notification(
            user=user,
            notification_type='ride_accepted',
            title='Driver Found!',
            message=f'{driver_name} is on the way. ETA: {eta_minutes} min',
            data={'ride_id': ride_id, 'driver_name': driver_name, 'eta_minutes': str(eta_minutes)},
        )

    @staticmethod
    def send_ride_started(user: User, ride_id: str):
        """Notify user that ride has started."""
        return NotificationService.send_notification(
            user=user,
            notification_type='ride_started',
            title='Ride Started',
            message='Your ride has started. Enjoy your trip!',
            data={'ride_id': ride_id},
        )

    @staticmethod
    def send_ride_completed(user: User, ride_id: str, final_price: float):
        """Notify user that ride is completed."""
        return NotificationService.send_notification(
            user=user,
            notification_type='ride_completed',
            title='Ride Completed',
            message=f'Your ride is complete. Total: {final_price} UAH',
            data={'ride_id': ride_id, 'final_price': str(final_price)},
        )

    @staticmethod
    def send_ride_cancelled(user: User, ride_id: str, reason: str):
        """Notify user that ride was cancelled."""
        return NotificationService.send_notification(
            user=user,
            notification_type='ride_cancelled',
            title='Ride Cancelled',
            message=f'Your ride was cancelled. Reason: {reason}',
            data={'ride_id': ride_id, 'reason': reason},
        )

    @staticmethod
    def send_driver_arrived(user: User, ride_id: str, driver_name: str):
        """Notify user that driver arrived at pickup."""
        return NotificationService.send_notification(
            user=user,
            notification_type='driver_arrived',
            title='Driver Arrived!',
            message=f'{driver_name} is waiting for you',
            data={'ride_id': ride_id},
        )

    @staticmethod
    def send_payment_success(user: User, amount: float, ride_id: str):
        """Notify user of successful payment."""
        return NotificationService.send_notification(
            user=user,
            notification_type='payment_success',
            title='Payment Successful',
            message=f'Payment of {amount} UAH confirmed',
            data={'ride_id': ride_id, 'amount': str(amount)},
        )

    @staticmethod
    def notify_driver_new_ride(driver_user: User, ride_id: str, pickup_address: str):
        """Notify driver about new ride request."""
        return NotificationService.send_notification(
            user=driver_user,
            notification_type='new_ride_request',
            title='New Ride Request!',
            message=f'Pickup: {pickup_address}',
            data={'ride_id': ride_id, 'pickup_address': pickup_address},
        )

    @staticmethod
    def get_user_notifications(user: User, unread_only: bool = False, limit: int = 50) -> list:
        """Get user notifications from DB."""
        qs = Notification.objects.filter(user=user)
        if unread_only:
            qs = qs.filter(is_read=False)
        return list(qs[:limit])

    @staticmethod
    def mark_all_read(user: User) -> int:
        """Mark all notifications as read. Returns count updated."""
        from django.utils import timezone
        now = timezone.now()
        count = Notification.objects.filter(user=user, is_read=False).update(
            is_read=True, read_at=now
        )
        return count

    @staticmethod
    def get_unread_count(user: User) -> int:
        """Get unread notification count."""
        return Notification.objects.filter(user=user, is_read=False).count()
