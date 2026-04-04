"""
Business logic services for drivers app.
"""

import logging
from typing import Optional
from django.db import transaction
from django.contrib.gis.geos import Point
from apps.drivers.models import Driver
from apps.users.models import User
from django.core.cache import cache
from django.utils import timezone

DRIVER_LOCATION_CACHE_TTL = 300

logger = logging.getLogger(__name__)


class DriverService:

    @staticmethod
    def register_driver(user: User, **driver_data) -> Driver:
        """Register user as driver."""
        if hasattr(user, 'driver_profile'):
            raise ValueError('User already registered as driver')
        if user.role != 'driver':
            user.role = 'driver'
            user.save(update_fields=['role'])
        driver = Driver.objects.create(
            user=user, status=Driver.Status.PENDING, **driver_data
        )
        logger.info(f"Driver registered: {user.email}")
        return driver

    @staticmethod
    def approve_driver(driver_id: str, approved_by: User) -> Driver:
        """Approve driver for work (admin action)."""
        driver = Driver.objects.get(id=driver_id)
        if driver.status == Driver.Status.APPROVED:
            raise ValueError('Driver already approved')
        driver.status = Driver.Status.APPROVED
        driver.save(update_fields=['status'])
        logger.info(f"Driver approved: {driver.user.email} by {approved_by.email}")
        return driver

    @staticmethod
    def reject_driver(driver_id: str, reason: str, rejected_by: User) -> Driver:
        """Reject driver application (admin action)."""
        driver = Driver.objects.get(id=driver_id)
        driver.status = Driver.Status.REJECTED
        driver.rejection_reason = reason
        driver.save(update_fields=['status', 'rejection_reason'])
        logger.info(f"Driver rejected: {driver.user.email} by {rejected_by.email}")
        return driver

    @staticmethod
    def suspend_driver(driver_id: str, reason: str, suspended_by: User) -> Driver:
        """Suspend driver (admin action)."""
        driver = Driver.objects.get(id=driver_id)
        driver.status = Driver.Status.SUSPENDED
        driver.availability = Driver.Availability.OFFLINE
        driver.suspension_reason = reason
        driver.save(update_fields=['status', 'availability', 'suspension_reason'])
        logger.warning(f"Driver suspended: {driver.user.email} by {suspended_by.email}")
        return driver

    @staticmethod
    def update_location(driver: Driver, latitude: float, longitude: float) -> Driver:
        """Update driver GPS location — DB + Cache."""
        driver.update_location(latitude, longitude)
        # Cache the location in Redis for quick access
        LocationCacheService.set_driver_location(str(driver.id), latitude, longitude)
        logger.debug(f"Driver location updated: {driver.user.email} ({latitude}, {longitude})")
        return driver

    @staticmethod
    def broadcast_location(driver: Driver, latitude: float, longitude: float):
        """
        Update location and broadcast to Redis channel for WebSocket (future).
        Current: stores in Redis cache for polling.
        """
        # Update DB
        driver.update_location(latitude, longitude)

        # Update Redis cache
        LocationCacheService.set_driver_location(str(driver.id), latitude, longitude)

        # Store in sorted set for proximity queries
        from django.core.cache import cache
        cache.set(
            f'driver:coords:{driver.id}',
            {'lat': latitude, 'lon': longitude, 'ts': str(timezone.now())},
            timeout=300
        )

    @staticmethod
    def set_availability(driver: Driver, availability: str) -> Driver:
        """Change driver availability status."""
        if driver.status != Driver.Status.APPROVED:
            raise ValueError('Only approved drivers can change availability')
        driver.availability = availability
        driver.save(update_fields=['availability'])
        logger.info(f"Driver availability changed: {driver.user.email} → {availability}")
        return driver

    @staticmethod
    def get_nearby_drivers(
        latitude: float, longitude: float,
        vehicle_type: Optional[str] = None,
        radius_km: float = 10
    ):
        """Find nearby available drivers."""
        if vehicle_type:
            return Driver.objects.nearby_by_type(latitude, longitude, vehicle_type, radius_km)
        return Driver.objects.nearby(latitude, longitude, radius_km)

    @staticmethod
    def update_driver_rating(driver: Driver, new_rating: float) -> Driver:
        """Update driver rating after ride completion."""
        if not 1.0 <= new_rating <= 5.0:
            raise ValueError('Rating must be between 1.0 and 5.0')
        driver.update_rating(new_rating)
        logger.info(f"Driver rating updated: {driver.user.email} → {driver.rating}")
        return driver


class LocationCacheService:
    """Cache service for driver locations."""

    @staticmethod
    def set_driver_location(driver_id: str, lat: float, lon: float, ttl: int = DRIVER_LOCATION_CACHE_TTL):
        """Cache driver location in Redis."""
        key = f'driver:location:{driver_id}'
        cache.set(key, {'lat': lat, 'lon': lon}, timeout=ttl)

    @staticmethod
    def get_driver_location(driver_id: str) -> dict | None:
        """Get cached driver location from Redis."""
        key = f'driver:location:{driver_id}'
        return cache.get(key)

    @staticmethod
    def delete_driver_location(driver_id: str):
        """Remove driver location from cache."""
        key = f'driver:location:{driver_id}'
        cache.delete(key)

    @staticmethod
    def get_all_online_drivers() -> list:
        """Get all cached driver locations (for monitoring)."""
        # Pattern: driver:location:*
        # Note: Redis KEYS is expensive — use for debug only
        return []