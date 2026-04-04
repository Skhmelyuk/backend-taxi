import pytest
from rest_framework.test import APIClient
from rest_framework import status
from apps.rides.models import Ride
from apps.rides.tests.factories import RideFactory
from apps.users.tests.factories import UserFactory
from apps.drivers.tests.factories import DriverFactory


@pytest.mark.django_db
class TestRideAPIIntegration:

    def test_full_ride_lifecycle(self):
        """Test complete ride lifecycle via API."""
        user = UserFactory()
        driver = DriverFactory(status='approved', availability='online')

        user_client = APIClient()
        user_client.force_authenticate(user=user)
        driver_client = APIClient()
        driver_client.force_authenticate(user=driver.user)

        # 1. Get price estimate
        est_response = user_client.post('/api/v1/rides/estimate/', {
            'pickup_lat': 50.4501, 'pickup_lon': 30.5234,
            'dropoff_lat': 50.4313, 'dropoff_lon': 30.4879,
            'vehicle_type': 'economy',
        })
        assert est_response.status_code == status.HTTP_200_OK
        assert 'economy' in est_response.data['estimates']

        # 2. Create ride
        create_response = user_client.post('/api/v1/rides/create_ride/', {
            'pickup_lat': 50.4501, 'pickup_lon': 30.5234,
            'dropoff_lat': 50.4313, 'dropoff_lon': 30.4879,
            'pickup_address': 'Хрещатик 1', 'dropoff_address': 'Вокзал',
            'vehicle_type': 'economy',
        })
        assert create_response.status_code == status.HTTP_201_CREATED
        ride_id = create_response.data['id']

        # 3. Driver accepts
        accept_response = driver_client.post(f'/api/v1/rides/{ride_id}/accept/')
        assert accept_response.status_code == status.HTTP_200_OK

        # 4. Driver starts
        start_response = driver_client.post(f'/api/v1/rides/{ride_id}/start/')
        assert start_response.status_code == status.HTTP_200_OK

        # 5. Driver completes
        complete_response = driver_client.post(f'/api/v1/rides/{ride_id}/complete/', {
            'actual_distance_km': 4.5
        })
        assert complete_response.status_code == status.HTTP_200_OK
        assert complete_response.data['status'] == 'completed'

        # 6. User rates
        rate_response = user_client.post(f'/api/v1/rides/{ride_id}/rate/', {
            'rating': 5, 'comment': 'Excellent!'
        })
        assert rate_response.status_code == status.HTTP_200_OK
        assert rate_response.data['rating'] == 5

    def test_user_cancels_pending_ride(self):
        """Test user cancels pending ride."""
        user = UserFactory()
        ride = RideFactory(user=user, status='pending')
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.post(f'/api/v1/rides/{ride.id}/cancel/', {'reason': 'user_cancelled'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'cancelled'

    def test_price_estimate_all_types(self):
        """Test price estimate returns all vehicle types."""
        user = UserFactory()
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.post('/api/v1/rides/estimate/', {
            'pickup_lat': 50.4501, 'pickup_lon': 30.5234,
            'dropoff_lat': 50.4313, 'dropoff_lon': 30.4879,
            'vehicle_type': 'economy',
        })
        assert response.status_code == status.HTTP_200_OK
        estimates = response.data['estimates']
        assert 'economy' in estimates
        assert 'comfort' in estimates
        assert 'business' in estimates
        assert estimates['business']['estimated_price'] > estimates['economy']['estimated_price']