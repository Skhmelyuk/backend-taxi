import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, name='apps.drivers.tasks.cleanup_stale_locations')
def cleanup_stale_locations(self):
    """
    Remove location data for drivers that haven't updated in 10+ minutes.
    Runs periodically via Celery Beat.
    """
    try:
        from apps.drivers.models import Driver
        from apps.drivers.services import LocationCacheService

        # Find drivers with outdated location
        stale_threshold = timezone.now() - timedelta(minutes=10)
        stale_drivers = Driver.objects.filter(
            location_updated_at__lt=stale_threshold,
            availability='online'
        )

        count = 0
        for driver in stale_drivers:
            # Change status to offline
            driver.availability = 'offline'
            driver.save(update_fields=['availability'])
            # Clear the cache
            LocationCacheService.delete_driver_location(str(driver.id))
            count += 1

        logger.info(f"Cleaned up {count} stale driver locations")
        return {'cleaned': count}

    except Exception as exc:
        logger.error(f"Error in cleanup_stale_locations: {exc}")
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, name='apps.drivers.tasks.update_driver_statistics')
def update_driver_statistics(self, driver_id: str):
    """
    Update driver statistics after ride completion.
    Called after each ride is completed.
    """
    try:
        from apps.drivers.models import Driver
        driver = Driver.objects.get(id=driver_id)
        # TODO: Calculate from rides in Plan 04
        logger.info(f"Updated statistics for driver: {driver.user.email}")
        return {'driver_id': driver_id, 'status': 'updated'}
    except Exception as exc:
        logger.error(f"Error updating driver stats {driver_id}: {exc}")
        raise


@shared_task(bind=True, name='apps.drivers.tasks.notify_driver_new_ride')
def notify_driver_new_ride(self, driver_id: str, ride_id: str):
    """
    Notify driver about a new ride request.
    Called during ride matching in Plan 04.
    """
    try:
        from apps.drivers.models import Driver
        driver = Driver.objects.get(id=driver_id)
        # TODO: Send FCM notification in Plan 06
        logger.info(f"Notified driver {driver.user.email} about ride {ride_id}")
        return {'driver_id': driver_id, 'ride_id': ride_id, 'notified': True}
    except Exception as exc:
        logger.error(f"Error notifying driver {driver_id}: {exc}")
        raise


@shared_task(name='apps.drivers.tasks.check_driver_documents_expiry')
def check_driver_documents_expiry():
    """
    Check for drivers with expiring documents (license).
    Runs daily via Celery Beat.
    """
    from apps.drivers.models import Driver
    expiry_warning_days = 30
    warning_date = timezone.now().date() + timedelta(days=expiry_warning_days)

    expiring = Driver.objects.filter(
        status='approved',
        license_expiry__lte=warning_date,
        license_expiry__gt=timezone.now().date()
    )

    count = expiring.count()
    logger.info(f"Found {count} drivers with expiring documents")
    # TODO: Send notifications in Plan 06
    return {'expiring_count': count}