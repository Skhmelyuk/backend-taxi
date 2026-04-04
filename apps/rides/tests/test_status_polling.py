import pytest
from rest_framework.test import APIClient
from rest_framework import status
from apps.rides.tests.factories import RideFactory
from apps.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestRideStatusPolling:
    """Tests for /api/v1/rides/{id}/status/ endpoint."""
    def test_ride_owner_can_poll(self):
        """Ride owner should be able to poll ride status."""
        user = UserFactory()
        ride = RideFactory(user=user, status='pending')
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get(f'/api/v1/rides/{ride.id}/status/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'pending'
        assert 'driver_location' in response.data

    def test_other_user_cannot_poll(self):
        """Other users should not be able to poll ride status."""
        user = UserFactory()
        other_user = UserFactory()
        ride = RideFactory(user=user, status='pending')
        client = APIClient()
        client.force_authenticate(user=other_user)
        response = client.get(f'/api/v1/rides/{ride.id}/status/')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_nonexistent_ride(self):
        """Polling a nonexistent ride should return 404."""
        user = UserFactory()
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get('/api/v1/rides/00000000-0000-0000-0000-000000000000/status/')
        assert response.status_code == status.HTTP_404_NOT_FOUND
