"""
Tests for driver location caching and retrieval.
"""

import pytest
from apps.drivers.models import Driver
from apps.drivers.services import DriverService, LocationCacheService
from apps.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestLocationCaching:

    def test_cache_and_retrieve_location(self):
        """Test setting and getting driver location from cache."""
        LocationCacheService.set_driver_location('test-id', 50.4501, 30.5234)
        cached = LocationCacheService.get_driver_location('test-id')
        assert cached is not None
        assert abs(cached['lat'] - 50.4501) < 0.001
        assert abs(cached['lon'] - 30.5234) < 0.001

    def test_delete_location_cache(self):
        """Test deleting driver location from cache."""
        LocationCacheService.set_driver_location('test-id-2', 50.4501, 30.5234)
        LocationCacheService.delete_driver_location('test-id-2')
        assert LocationCacheService.get_driver_location('test-id-2') is None

    def test_update_location_sets_cache(self):
        """Test that updating driver location also updates the cache."""
        user = UserFactory(role='driver')
        driver = Driver.objects.create(
            user=user, vehicle_make='T', vehicle_model='C', vehicle_year=2020,
            vehicle_color='W', vehicle_plate='LOC1234', license_number='DLLOC001',
            license_expiry='2026-01-01', status='approved'
        )
        DriverService.update_location(driver, 50.4501, 30.5234)
        cached = LocationCacheService.get_driver_location(str(driver.id))
        assert cached is not None
        assert abs(cached['lat'] - 50.4501) < 0.001