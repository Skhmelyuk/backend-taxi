import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_push_notification(self, user_id: str, notification_type: str,
                            title: str, message: str, data: dict = None):
    """Async task: send push notification to user."""
    try:
        from django.contrib.auth import get_user_model
        from apps.notifications.services import NotificationService

        User = get_user_model()
        user = User.objects.get(id=user_id)
        NotificationService.send_notification(
            user=user,
            notification_type=notification_type,
            title=title,
            message=message,
            data=data or {},
        )
        logger.info(f"Push notification sent to {user.email}: {notification_type}")
        return {'sent': True, 'user_id': user_id}
    except Exception as exc:
        logger.error(f"Error sending push notification to {user_id}: {exc}")
        raise self.retry(exc=exc, countdown=30)


@shared_task(bind=True)
def send_bulk_notification(self, user_ids: list, notification_type: str,
                            title: str, message: str, data: dict = None):
    """Async task: send notification to multiple users."""
    from django.contrib.auth import get_user_model
    from apps.notifications.services import NotificationService

    User = get_user_model()
    success_count = 0
    fail_count = 0

    for user_id in user_ids:
        try:
            user = User.objects.get(id=user_id)
            NotificationService.send_notification(
                user=user,
                notification_type=notification_type,
                title=title,
                message=message,
                data=data or {},
            )
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to notify user {user_id}: {e}")
            fail_count += 1

    logger.info(f"Bulk notification: {success_count} ok, {fail_count} failed")
    return {'success': success_count, 'failed': fail_count}


@shared_task
def cleanup_old_notifications():
    """
    Delete read notifications older than 30 days.
    Runs weekly via Celery Beat.
    """
    from apps.notifications.models import Notification
    from django.utils import timezone
    from datetime import timedelta

    cutoff = timezone.now() - timedelta(days=30)
    deleted, _ = Notification.objects.filter(
        is_read=True, created_at__lt=cutoff
    ).delete()

    logger.info(f"Cleaned up {deleted} old notifications")
    return {'deleted': deleted}


@shared_task
def send_promo_notifications():
    """
    Send promo code notifications to users.
    Can be triggered manually or on schedule.
    """
    from apps.payments.models import PromoCode
    from django.contrib.auth import get_user_model
    from apps.notifications.services import NotificationService

    User = get_user_model()
    active_promos = PromoCode.objects.filter(is_active=True)[:5]
    if not active_promos:
        return {'sent': 0}

    promo = active_promos[0]
    users = User.objects.filter(is_active=True)[:100]

    sent = 0
    for user in users:
        try:
            NotificationService.send_notification(
                user=user,
                notification_type='promo_available',
                title='Special Offer! 🎉',
                message=f'Use promo code {promo.code} for discount!',
                data={'promo_code': promo.code},
                save_to_db=True
            )
            sent += 1
        except Exception as e:
            logger.warning(f"Promo notification failed for {user.email}: {e}")

    logger.info(f"Sent promo notifications to {sent} users")
    return {'sent': sent}