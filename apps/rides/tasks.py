import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def find_driver_for_ride(self, ride_id: str):
    """Find driver for new ride (auto-matching)."""
    try:
        from apps.rides.models import Ride
        from apps.rides.services.matching_service import MatchingService

        ride = Ride.objects.get(id=ride_id)
        if ride.status != 'pending':
            return

        driver = MatchingService.auto_match_ride(ride)
        if driver:
            return {'matched': True, 'driver_id': str(driver.id)}

        raise self.retry(countdown=10)

    except Exception as exc:
        if self.request.retries >= self.max_retries:
            from apps.rides.models import Ride
            try:
                ride = Ride.objects.get(id=ride_id)
                if ride.status == 'pending':
                    ride.status = 'cancelled'
                    ride.cancellation_reason = 'no_drivers'
                    ride.save(update_fields=['status', 'cancellation_reason'])
            except Exception:
                pass
            return {'matched': False}
        raise


@shared_task(bind=True)
def cancel_timeout_rides(self):
    """
    Cancel rides that have been pending for too long (no driver found).
    Runs every 5 minutes via Celery Beat.
    """
    from apps.rides.models import Ride

    timeout = timezone.now() - timedelta(minutes=10)
    pending_rides = Ride.objects.filter(
        status='pending',
        created_at__lt=timeout
    )

    count = 0
    for ride in pending_rides:
        ride.status = 'cancelled'
        ride.cancellation_reason = 'no_drivers'
        ride.cancelled_at = timezone.now()
        ride.save(update_fields=['status', 'cancellation_reason', 'cancelled_at'])
        count += 1
        logger.info(f"Cancelled timeout ride: {ride.id}")

    logger.info(f"Cancelled {count} timeout rides")
    return {'cancelled': count}


@shared_task(bind=True)
def calculate_ride_statistics(self, ride_id: str):
    """Calculate and cache ride statistics after completion."""
    try:
        from apps.rides.models import Ride
        ride = Ride.objects.get(id=ride_id)
        if ride.status != 'completed':
            return

        logger.info(f"Calculated statistics for ride {ride_id}")
        return {'ride_id': ride_id, 'status': 'ok'}
    except Exception as exc:
        logger.error(f"Error calculating stats for ride {ride_id}: {exc}")
        raise


@shared_task
def generate_daily_ride_report():
    """
    Generate daily ride summary statistics.
    Runs at midnight via Celery Beat.
    """
    from apps.rides.models import Ride
    from django.utils import timezone
    from datetime import timedelta

    yesterday = timezone.now().date() - timedelta(days=1)
    rides = Ride.objects.filter(
        created_at__date=yesterday,
        status='completed'
    )

    stats = {
        'date': str(yesterday),
        'total_rides': rides.count(),
        'total_revenue': float(sum(r.final_price or 0 for r in rides)),
    }

    logger.info(f"Daily report: {stats}")
    return stats