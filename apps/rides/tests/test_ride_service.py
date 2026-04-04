"""
Tests for RideService to ensure correct ride lifecycle management, including creation, acceptance, completion, and cancellation.
"""

import pytest
from decimal import Decimal
from django.contrib.gis.geos import Point
from apps.rides.models import Ride
from apps.rides.services import RideService
from apps.users.tests.factories import UserFactory
from apps.drivers.tests.factories import DriverFactory


@pytest.mark.django_db
class TestRideService:
    """Tests for RideService to ensure correct ride lifecycle management, 
       including creation, acceptance, completion, and cancellation."""
    def test_create_ride(self):
        """Test creating a new ride request."""
        user = UserFactory()
        ride = RideService.create_ride(
            user=user,
            pickup_lat=50.4501, pickup_lon=30.5234,
            dropoff_lat=50.4313, dropoff_lon=30.4879,
            pickup_address='Pickup', dropoff_address='Dropoff',
            vehicle_type='economy'
        )
        assert ride.status == Ride.Status.PENDING
        assert ride.user == user
        assert ride.driver is None

    def test_cannot_create_two_active_rides(self):
        """Test that a user cannot create a new ride if they already have an active ride."""
        user = UserFactory()
        RideService.create_ride(
            user=user, pickup_lat=50.4501, pickup_lon=30.5234,
            dropoff_lat=50.4313, dropoff_lon=30.4879,
            pickup_address='Pickup', dropoff_address='Dropoff',
            vehicle_type='economy'
        )
        with pytest.raises(ValueError, match='already has an active ride'):
            RideService.create_ride(
                user=user, pickup_lat=50.4501, pickup_lon=30.5234,
                dropoff_lat=50.4313, dropoff_lon=30.4879,
                pickup_address='Pickup', dropoff_address='Dropoff',
                vehicle_type='economy'
            )

    def test_accept_ride(self):
        """Test accepting a ride request."""
        user = UserFactory()
        driver = DriverFactory(status='approved', availability='online')
        ride = RideService.create_ride(
            user=user, pickup_lat=50.4501, pickup_lon=30.5234,
            dropoff_lat=50.4313, dropoff_lon=30.4879,
            pickup_address='Pickup', dropoff_address='Dropoff',
            vehicle_type='economy'
        )
        accepted = RideService.accept_ride(str(ride.id), driver)
        assert accepted.status == Ride.Status.ACCEPTED
        assert accepted.driver == driver

    def test_complete_ride_flow(self):
        """Test the complete flow of accepting, starting, and completing a ride."""
        user = UserFactory()
        driver = DriverFactory(status='approved', availability='online')
        ride = RideService.create_ride(
            user=user, pickup_lat=50.4501, pickup_lon=30.5234,
            dropoff_lat=50.4313, dropoff_lon=30.4879,
            pickup_address='Pickup', dropoff_address='Dropoff',
            vehicle_type='economy'
        )
        RideService.accept_ride(str(ride.id), driver)
        RideService.start_ride(str(ride.id), driver)
        completed = RideService.complete_ride(str(ride.id), driver, actual_distance_km=4.5)
        assert completed.status == Ride.Status.COMPLETED
        assert completed.final_price is not None

    def test_cancel_ride(self):
        """Test cancelling a ride request."""
        user = UserFactory()
        ride = RideService.create_ride(
            user=user, pickup_lat=50.4501, pickup_lon=30.5234,
            dropoff_lat=50.4313, dropoff_lon=30.4879,
            pickup_address='Pickup', dropoff_address='Dropoff',
            vehicle_type='economy'
        )
        cancelled = RideService.cancel_ride(str(ride.id), user, 'user_cancelled')
        assert cancelled.status == Ride.Status.CANCELLED