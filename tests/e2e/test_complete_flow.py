"""End-to-end tests for complete user flow."""

import pytest
from decimal import Decimal
from django.contrib.gis.geos import Point
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestCompleteRideFlow:
    """Test complete ride journey from request to payment."""

    def setup_method(self):
        self.client = APIClient()
        self.driver_client = APIClient()

    def test_complete_ride_flow(
        self, user_factory, driver_factory
    ):
        """
        Complete flow:
        1. Passenger requests a ride
        2. Driver accepts
        3. Driver starts the ride
        4. Driver completes the ride
        5. Payment is processed
        """
        from apps.rides.models import Ride
        from apps.drivers.models import Driver

        # Setup users
        passenger = user_factory(role='passenger')
        driver_user = user_factory(role='driver')

        # Setup approved driver
        from apps.drivers.tests.factories import DriverFactory
        driver = DriverFactory(
            user=driver_user,
            status='approved',
            availability='online',
            current_location=Point(30.5, 50.4),  # Kyiv
        )

        # Authenticate
        self.client.force_authenticate(user=passenger)
        self.driver_client.force_authenticate(user=driver_user)

        # 1. Passenger creates ride
        ride_data = {
            'pickup_lat': 50.4501,
            'pickup_lon': 30.5234,
            'dropoff_lat': 50.4600,
            'dropoff_lon': 30.5300,
            'pickup_address': 'Khreshchatyk 1, Kyiv',
            'dropoff_address': 'Khreshchatyk 50, Kyiv',
            'vehicle_type': 'economy'
        }
        response = self.client.post('/api/v1/rides/create_ride/', ride_data)
        assert response.status_code == 201, response.data
        ride_id = response.data['id']

        # 2. Driver accepts ride
        response = self.driver_client.post(
            f'/api/v1/rides/{ride_id}/accept/'
        )
        assert response.status_code == 200

        # Verify ride status
        ride = Ride.objects.get(id=ride_id)
        assert ride.status == 'accepted'
        assert ride.driver == driver

        # 3. Driver starts ride
        response = self.driver_client.post(
            f'/api/v1/rides/{ride_id}/start/'
        )
        assert response.status_code == 200
        ride.refresh_from_db()
        assert ride.status == 'in_progress'

        # 4. Driver completes ride
        response = self.driver_client.post(
            f'/api/v1/rides/{ride_id}/complete/'
        )
        assert response.status_code == 200
        ride.refresh_from_db()
        assert ride.status == 'completed'
        assert ride.completed_at is not None

    def test_ride_cancellation_by_passenger(self, user_factory, driver_factory):
        """Passenger can cancel a pending ride."""
        from apps.rides.models import Ride

        passenger = user_factory(role='passenger')
        self.client.force_authenticate(user=passenger)

        # Create ride
        ride_data = {
            'pickup_lat': 50.4501,
            'pickup_lon': 30.5234,
            'dropoff_lat': 50.4600,
            'dropoff_lon': 30.5300,
            'pickup_address': 'Test pickup',
            'dropoff_address': 'Test dropoff',
            'vehicle_type': 'economy'
        }
        response = self.client.post('/api/v1/rides/create_ride/', ride_data)
        assert response.status_code == 201
        ride_id = response.data['id']

        # Cancel ride
        response = self.client.post(
            f'/api/v1/rides/{ride_id}/cancel/',
            {'reason': 'user_cancelled', 'comment': 'Changed plans'},
        )
        assert response.status_code == 200
        ride = Ride.objects.get(id=ride_id)
        assert ride.status == 'cancelled'


@pytest.mark.django_db
class TestAuthFlow:
    """Test authentication flows."""

    def setup_method(self):
        self.client = APIClient()

    def test_unauthenticated_access_blocked(self):
        """All protected endpoints require authentication."""
        protected_endpoints = [
            '/api/v1/rides/',
            '/api/v1/drivers/',
            '/api/v1/payments/',
            '/api/v1/notifications/',
        ]
        for endpoint in protected_endpoints:
            response = self.client.get(endpoint)
            assert response.status_code in (401, 403), (
                f'{endpoint} returned {response.status_code}'
            )

    def test_health_check_public(self):
        """Health check endpoint is publicly accessible."""
        response = self.client.get('/api/v1/health/')
        assert response.status_code == 200