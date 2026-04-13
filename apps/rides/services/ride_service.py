"""
Ride service for handling ride lifecycle: creation, acceptance, completion, cancellation, and rating.
"""

import logging
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.contrib.gis.geos import Point
from apps.rides.models import Ride
from apps.rides.services.pricing_service import PricingService
from apps.users.models import User
from apps.drivers.models import Driver

logger = logging.getLogger(__name__)


class RideService:
    """Service class for managing ride operations."""
    @staticmethod
    @transaction.atomic
    def create_ride(
        user: User,
        pickup_lat: float, pickup_lon: float,
        dropoff_lat: float, dropoff_lon: float,
        pickup_address: str, dropoff_address: str,
        vehicle_type: str,
        promo_code=None
    ) -> Ride:
        """Create a new ride request."""
        active_ride = Ride.objects.filter(
            user=user, status__in=['pending', 'accepted', 'in_progress']
        ).first()
        if active_ride:
            raise ValueError('User already has an active ride')

        estimate = PricingService.get_price_estimate(
            pickup_lat=pickup_lat, pickup_lon=pickup_lon,
            dropoff_lat=dropoff_lat, dropoff_lon=dropoff_lon,
            vehicle_type=vehicle_type
        )
        estimated_price = Decimal(str(estimate['estimated_price']))
        discount = Decimal('0.00')

        if promo_code:
            estimated_price, discount = PricingService.apply_promo_code(estimated_price, promo_code)

        ride = Ride.objects.create(
            user=user,
            vehicle_type=vehicle_type,
            pickup_location=Point(pickup_lon, pickup_lat, srid=4326),
            dropoff_location=Point(dropoff_lon, dropoff_lat, srid=4326),
            pickup_address=pickup_address,
            dropoff_address=dropoff_address,
            estimated_distance=estimate['distance_km'],
            estimated_duration=estimate['duration_minutes'],
            estimated_price=Decimal(str(estimate['estimated_price'])),
            discount=discount,
            status=Ride.Status.PENDING
        )
        logger.info(f"Ride created: {ride.id} for user {user.email}, price: {estimated_price} UAH")

        from apps.rides.tasks import find_driver_for_ride
        find_driver_for_ride.delay(str(ride.id))

        return ride

    @staticmethod
    @transaction.atomic
    def accept_ride(ride_id: str, driver: Driver) -> Ride:
        """Driver accepts a ride."""
        ride = Ride.objects.select_related(None).select_for_update().get(id=ride_id)
        if ride.status != Ride.Status.PENDING:
            raise ValueError('Ride is not in pending status')
        if not driver.is_available:
            raise ValueError('Driver is not available')

        ride.driver = driver
        ride.status = Ride.Status.ACCEPTED
        ride.accepted_at = timezone.now()
        ride.save(update_fields=['driver', 'status', 'accepted_at'])

        driver.availability = Driver.Availability.BUSY
        driver.save(update_fields=['availability'])

        # Send notification to user
        from apps.notifications.services import NotificationService
        try:
            NotificationService.send_ride_accepted(
                user=ride.user,
                ride_id=str(ride.id),
                driver_name=driver.user.full_name,
                eta_minutes=5
            )
        except Exception as e:
            logger.warning(f"Notification failed: {e}")  # non-critical

        logger.info(f"Ride {ride_id} accepted by driver {driver.user.email}")
        return ride

    @staticmethod
    @transaction.atomic
    def start_ride(ride_id: str, driver: Driver) -> Ride:
        """Driver starts the ride."""
        ride = Ride.objects.select_related(None).select_for_update().get(id=ride_id)
        if ride.status != Ride.Status.ACCEPTED:
            raise ValueError('Ride is not in accepted status')
        if ride.driver != driver:
            raise ValueError('You are not the assigned driver')

        ride.status = Ride.Status.IN_PROGRESS
        ride.started_at = timezone.now()
        ride.save(update_fields=['status', 'started_at'])

        logger.info(f"Ride {ride_id} started by driver {driver.user.email}")
        return ride

    @staticmethod
    @transaction.atomic
    def complete_ride(ride_id: str, driver: Driver, actual_distance_km: float = None) -> Ride:
        """Driver completes the ride."""
        ride = Ride.objects.select_related(None).select_for_update().get(id=ride_id)
        if ride.status != Ride.Status.IN_PROGRESS:
            raise ValueError('Ride is not in progress')
        if ride.driver != driver:
            raise ValueError('You are not the assigned driver')

        ride.completed_at = timezone.now()
        final_distance = actual_distance_km or float(ride.estimated_distance)
        ride.final_distance = Decimal(str(final_distance))
        ride.final_duration = ride.duration_minutes

        price_data = PricingService.calculate_price(final_distance, ride.vehicle_type)
        ride.final_price = Decimal(str(price_data['estimated_price']))
        ride.final_price -= ride.discount

        ride.status = Ride.Status.COMPLETED
        ride.save(update_fields=[
            'status', 'completed_at', 'final_distance', 'final_duration', 'final_price'
        ])

        # Update driver earnings — detect payment method from Payment if exists
        from apps.payments.models import Payment
        payment = Payment.objects.filter(
            ride=ride, status=Payment.Status.SUCCESS
        ).first()

        driver_update_fields = ['availability', 'total_earnings', 'total_rides']
        driver.availability = Driver.Availability.ONLINE
        driver.total_earnings = Decimal(str(driver.total_earnings)) + ride.final_price
        driver.total_rides += 1

        if payment and payment.payment_method == Payment.PaymentMethod.CASH:
            driver.cash_earnings = Decimal(str(driver.cash_earnings)) + ride.final_price
            driver_update_fields.append('cash_earnings')
        elif payment and payment.payment_method in (
            Payment.PaymentMethod.CARD,
            Payment.PaymentMethod.GOOGLE_PAY,
            Payment.PaymentMethod.APPLE_PAY,
        ):
            driver.card_earnings = Decimal(str(driver.card_earnings)) + ride.final_price
            driver.pending_card_withdrawal = Decimal(str(driver.pending_card_withdrawal)) + ride.final_price
            driver_update_fields += ['card_earnings', 'pending_card_withdrawal']

        driver.save(update_fields=driver_update_fields)

        logger.info(f"Ride {ride_id} completed, final price: {ride.final_price} UAH")
        return ride

    @staticmethod
    @transaction.atomic
    def cancel_ride(ride_id: str, cancelled_by: User, reason: str, comment: str = '') -> Ride:
        """Cancel a ride (user or driver)."""
        ride = Ride.objects.select_related(None).select_for_update().get(id=ride_id)
        if not ride.is_active:
            raise ValueError('Only active rides can be cancelled')

        ride.status = Ride.Status.CANCELLED
        ride.cancelled_at = timezone.now()
        ride.cancellation_reason = reason
        ride.cancellation_comment = comment
        ride.save(update_fields=['status', 'cancelled_at', 'cancellation_reason', 'cancellation_comment'])

        if ride.driver:
            ride.driver.availability = Driver.Availability.ONLINE
            ride.driver.save(update_fields=['availability'])

        logger.info(f"Ride {ride_id} cancelled by {cancelled_by.email}, reason: {reason}")
        return ride

    @staticmethod
    def rate_ride(ride_id: str, user: User, rating: int, comment: str = '') -> Ride:
        """User rates a completed ride."""
        ride = Ride.objects.get(id=ride_id)
        if ride.user != user:
            raise ValueError('You can only rate your own rides')
        if ride.status != Ride.Status.COMPLETED:
            raise ValueError('Only completed rides can be rated')
        if ride.rating is not None:
            raise ValueError('Ride already rated')

        ride.rating = rating
        ride.user_comment = comment
        ride.save(update_fields=['rating', 'user_comment'])

        if ride.driver:
            from apps.drivers.services import DriverService
            DriverService.update_driver_rating(ride.driver, float(rating))

        return ride

    @staticmethod
    @transaction.atomic
    def rate_passenger(ride_id: str, driver: Driver, rating: int, comment: str = '') -> Ride:
        """Driver rates the passenger after ride completion."""
        ride = Ride.objects.get(id=ride_id)
        if ride.driver != driver:
            raise ValueError('You are not the assigned driver for this ride')
        if ride.status != Ride.Status.COMPLETED:
            raise ValueError('Only completed rides can be rated')
        if ride.driver_rating_for_passenger is not None:
            raise ValueError('Passenger already rated for this ride')

        ride.driver_rating_for_passenger = rating
        ride.driver_comment_for_passenger = comment
        ride.save(update_fields=['driver_rating_for_passenger', 'driver_comment_for_passenger'])

        # Update passenger's average_rating on User model
        passenger = ride.user
        completed_rides_with_rating = Ride.objects.filter(
            user=passenger,
            driver_rating_for_passenger__isnull=False
        ).values_list('driver_rating_for_passenger', flat=True)
        ratings = list(completed_rides_with_rating)
        if ratings:
            avg = sum(ratings) / len(ratings)
            from decimal import Decimal
            passenger.average_rating = Decimal(str(round(avg, 2)))
            passenger.save(update_fields=['average_rating'])

        logger.info(f"Passenger {passenger.email} rated {rating} by driver {driver.user.email} for ride {ride_id}")
        return ride

    @staticmethod
    @transaction.atomic
    def reject_ride(ride_id: str, driver: Driver) -> Ride:
        """Driver rejects an accepted ride — returns it to pending and re-queues matching."""
        ride = Ride.objects.select_related(None).select_for_update().get(id=ride_id)
        if ride.status != Ride.Status.ACCEPTED:
            raise ValueError('Only accepted rides can be rejected')
        if ride.driver != driver:
            raise ValueError('You are not the assigned driver for this ride')

        ride.driver = None
        ride.status = Ride.Status.PENDING
        ride.accepted_at = None
        ride.save(update_fields=['driver', 'status', 'accepted_at'])

        driver.availability = Driver.Availability.ONLINE
        driver.save(update_fields=['availability'])

        # Re-queue driver matching
        from apps.rides.tasks import find_driver_for_ride
        find_driver_for_ride.delay(str(ride.id))

        logger.info(f"Ride {ride_id} rejected by driver {driver.user.email}, re-queued for matching")
        return ride