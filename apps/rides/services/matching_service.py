import logging
from typing import Optional
from django.core.cache import cache
from apps.drivers.models import Driver
from apps.rides.models import Ride

logger = logging.getLogger(__name__)

MATCHING_TIMEOUT_SECONDS = 30
MAX_SEARCH_RADIUS_KM = 15
SEARCH_RADII_KM = [2, 5, 10, 15]


class MatchingService:

    @staticmethod
    def find_nearest_driver(
        latitude: float, longitude: float,
        vehicle_type: str,
        radius_km: float = 5.0
    ) -> Optional[Driver]:
        """
        Find nearest available driver.
        Expands search radius if no driver found.
        """
        for radius in SEARCH_RADII_KM:
            if radius > MAX_SEARCH_RADIUS_KM:
                break
            drivers = Driver.objects.nearby_by_type(
                latitude, longitude, vehicle_type, radius_km=radius
            )
            available = drivers.filter(
                status=Driver.Status.APPROVED,
                availability=Driver.Availability.ONLINE
            )
            driver = available.first()
            if driver:
                logger.info(
                    f"Found driver {driver.user.email} at {radius} km for {vehicle_type}"
                )
                return driver

        logger.warning(f"No driver found for {vehicle_type} at ({latitude}, {longitude})")
        return None

    @staticmethod
    def auto_match_ride(ride: Ride) -> Optional[Driver]:
        """
        Automatically find and assign driver to ride.
        Returns matched driver or None.
        """
        if ride.status != Ride.Status.PENDING:
            logger.warning(f"Cannot match ride {ride.id} — status: {ride.status}")
            return None

        pickup_lat = ride.pickup_location.y
        pickup_lon = ride.pickup_location.x

        driver = MatchingService.find_nearest_driver(
            latitude=pickup_lat,
            longitude=pickup_lon,
            vehicle_type=ride.vehicle_type
        )

        if not driver:
            logger.warning(f"No driver found for ride {ride.id}")
            return None

        # Lock matching to prevent race conditions
        lock_key = f'ride:matching:{ride.id}'
        if not cache.add(lock_key, True, timeout=MATCHING_TIMEOUT_SECONDS):
            logger.warning(f"Ride {ride.id} already being matched")
            return None

        try:
            from apps.rides.services.ride_service import RideService
            RideService.accept_ride(str(ride.id), driver)
            logger.info(f"Auto-matched ride {ride.id} → driver {driver.user.email}")
            return driver
        except Exception as e:
            logger.error(f"Matching failed for ride {ride.id}: {e}")
            return None
        finally:
            cache.delete(lock_key)

    @staticmethod
    def get_available_drivers_count(
        latitude: float, longitude: float,
        vehicle_type: str = None,
        radius_km: float = 5.0
    ) -> int:
        """Get count of available drivers nearby (for UI)."""
        if vehicle_type:
            return Driver.objects.nearby_by_type(
                latitude, longitude, vehicle_type, radius_km
            ).count()
        return Driver.objects.nearby(latitude, longitude, radius_km).count()