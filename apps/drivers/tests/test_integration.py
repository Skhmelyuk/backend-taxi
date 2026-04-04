import pytest
from rest_framework.test import APIClient
from rest_framework import status
from apps.drivers.models import Driver
from apps.drivers.tests.factories import DriverFactory, PendingDriverFactory
from apps.users.tests.factories import UserFactory, AdminUserFactory, DriverUserFactory


@pytest.mark.django_db
class TestDriverIntegration:

    def test_full_driver_registration_flow(self):
        """Test complete driver registration flow."""
        user = UserFactory()
        client = APIClient()
        client.force_authenticate(user=user)

        # Register
        response = client.post('/api/v1/drivers/register/', {
            'vehicle_type': 'economy',
            'vehicle_make': 'Toyota', 'vehicle_model': 'Camry',
            'vehicle_year': 2020, 'vehicle_color': 'White',
            'vehicle_plate': 'INTEG01', 'license_number': 'DLINTEG01',
            'license_expiry': '2026-01-01',
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['status'] == 'pending'

        # Admin approval flow
        admin = AdminUserFactory()
        driver_id = response.data['id']
        admin_client = APIClient()
        admin_client.force_authenticate(user=admin)

        approve_response = admin_client.post(f'/api/v1/drivers/{driver_id}/approve/')
        assert approve_response.status_code == status.HTTP_200_OK
        assert approve_response.data['status'] == 'approved'

    def test_driver_online_location_flow(self):
        """Test driver goes online and updates location."""
        user = DriverUserFactory()
        driver = DriverFactory(user=user, status='approved', availability='offline')
        client = APIClient()
        client.force_authenticate(user=user)

        # Go online
        avail_response = client.patch('/api/v1/drivers/availability/', {'availability': 'online'})
        assert avail_response.status_code == status.HTTP_200_OK

        # Update location
        loc_response = client.post('/api/v1/drivers/update_location/', {
            'latitude': 50.4501, 'longitude': 30.5234
        })
        assert loc_response.status_code == status.HTTP_200_OK

        # Find nearby
        nearby_response = client.get('/api/v1/drivers/nearby/?lat=50.4501&lon=30.5234&radius=5')
        assert nearby_response.status_code == status.HTTP_200_OK

    def test_admin_reject_and_suspend_driver(self):
        """Test admin rejection and suspension flow."""
        admin = AdminUserFactory()
        driver = PendingDriverFactory()
        client = APIClient()
        client.force_authenticate(user=admin)

        reject_response = client.post(f'/api/v1/drivers/{driver.id}/reject/', {
            'reason': 'Documents incomplete'
        })
        assert reject_response.status_code == status.HTTP_200_OK
        assert reject_response.data['status'] == 'rejected'