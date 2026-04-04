import pytest
from unittest.mock import patch
from django.contrib.gis.geos import Point
from django.core.cache import cache
from apps.rides.services.matching_service import MatchingService
from apps.drivers.tests.factories import DriverFactory
from apps.rides.tests.factories import RideFactory
from apps.drivers.models import Driver
from apps.rides.models import Ride


@pytest.mark.django_db
class TestMatchingService:
    """Unit tests for MatchingService."""

    def test_find_nearest_driver_found(self):
        """Test finding nearest driver when one is available."""
        driver = DriverFactory(
            status='approved', availability='online',
            current_location=Point(30.5234, 50.4501, srid=4326)
        )
        result = MatchingService.find_nearest_driver(50.4501, 30.5234, 'economy', radius_km=5)
        assert result is not None

    def test_find_nearest_driver_no_online_drivers(self):
        """Test finding nearest driver when no online drivers are available."""
        DriverFactory(
            status='approved', availability='offline',
            current_location=Point(30.5234, 50.4501, srid=4326)
        )
        result = MatchingService.find_nearest_driver(50.4501, 30.5234, 'economy', radius_km=5)
        assert result is None

    def test_available_drivers_count(self):
        """Test counting available drivers within radius."""
        DriverFactory.create_batch(
            3, status='approved', availability='online',
            current_location=Point(30.5234, 50.4501, srid=4326)
        )
        count = MatchingService.get_available_drivers_count(50.4501, 30.5234, radius_km=5)
        assert count == 3

    def test_find_nearest_driver_break(self):
        """Test breaking out of search loop when radius exceeds MAX."""
        with patch('apps.rides.services.matching_service.MAX_SEARCH_RADIUS_KM', 1):
            # SEARCH_RADII_KM starts at 2, which is > 1
            result = MatchingService.find_nearest_driver(50.4501, 30.5234, 'economy')
            assert result is None

    def test_available_drivers_count_with_type(self):
        """Test counting available drivers with a specific vehicle type."""
        DriverFactory.create_batch(
            2, status='approved', availability='online',
            vehicle_type='economy',
            current_location=Point(30.5234, 50.4501, srid=4326)
        )
        DriverFactory(
            status='approved', availability='online',
            vehicle_type='business',
            current_location=Point(30.5234, 50.4501, srid=4326)
        )
        count = MatchingService.get_available_drivers_count(
            50.4501, 30.5234, vehicle_type='economy', radius_km=5
        )
        assert count == 2

    def test_auto_match_ride_not_pending(self):
        ride = RideFactory(status='accepted')
        result = MatchingService.auto_match_ride(ride)
        assert result is None

    @patch('apps.rides.services.matching_service.MatchingService.find_nearest_driver')
    def test_auto_match_ride_no_driver(self, mock_find):
        mock_find.return_value = None
        ride = RideFactory(status='pending', pickup_location=Point(30.5234, 50.4501))
        result = MatchingService.auto_match_ride(ride)
        assert result is None

    @patch('apps.rides.services.matching_service.MatchingService.find_nearest_driver')
    @patch('apps.rides.services.matching_service.cache.add')
    def test_auto_match_ride_lock_failed(self, mock_cache_add, mock_find):
        driver = DriverFactory(status='approved', availability='online')
        mock_find.return_value = driver
        mock_cache_add.return_value = False
        ride = RideFactory(status='pending', pickup_location=Point(30.5234, 50.4501))
        result = MatchingService.auto_match_ride(ride)
        assert result is None

    @patch('apps.rides.services.matching_service.MatchingService.find_nearest_driver')
    @patch('apps.rides.services.ride_service.RideService.accept_ride')
    def test_auto_match_ride_success(self, mock_accept, mock_find):
        driver = DriverFactory(status='approved', availability='online')
        mock_find.return_value = driver
        ride = RideFactory(status='pending', pickup_location=Point(30.5234, 50.4501))
        
        result = MatchingService.auto_match_ride(ride)
        
        assert result == driver
        mock_accept.assert_called_once_with(str(ride.id), driver)

    @patch('apps.rides.services.matching_service.MatchingService.find_nearest_driver')
    @patch('apps.rides.services.ride_service.RideService.accept_ride')
    def test_auto_match_ride_exception(self, mock_accept, mock_find):
        driver = DriverFactory(status='approved', availability='online')
        mock_find.return_value = driver
        mock_accept.side_effect = Exception("Test Error")
        ride = RideFactory(status='pending', pickup_location=Point(30.5234, 50.4501))
        
        result = MatchingService.auto_match_ride(ride)
        
        assert result is None