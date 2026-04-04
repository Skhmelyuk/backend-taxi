"""
Tests for DriverViewSet API endpoints.
"""

import pytest
from rest_framework.test import APIClient
from rest_framework import status
from apps.drivers.models import Driver
from apps.users.tests.factories import UserFactory, AdminUserFactory, DriverUserFactory


@pytest.mark.django_db
class TestDriverViewSet:

    def _create_driver(self, user=None, **kwargs):
        """Helper to create a driver with default data."""
        user = user or UserFactory(role='driver')
        defaults = {
            'vehicle_make': 'Toyota', 'vehicle_model': 'Camry',
            'vehicle_year': 2020, 'vehicle_color': 'White',
            'vehicle_plate': f'TST{id(user):04d}',
            'license_number': f'DL{id(user):06d}',
            'license_expiry': '2026-01-01',
        }
        defaults.update(kwargs)
        return Driver.objects.create(user=user, **defaults)

    def test_register_driver(self):
        """Test driver registration endpoint."""
        user = UserFactory()
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post('/api/v1/drivers/register/', {
            'vehicle_type': 'economy',
            'vehicle_make': 'Toyota', 'vehicle_model': 'Camry',
            'vehicle_year': 2020, 'vehicle_color': 'White',
            'vehicle_plate': 'REG001', 'license_number': 'DLREG001',
            'license_expiry': '2026-01-01',
        })
        assert response.status_code == status.HTTP_201_CREATED

    def test_driver_me(self):
        """Test retrieving current driver's profile."""
        user = DriverUserFactory()
        driver = self._create_driver(user=user)
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get('/api/v1/drivers/me/')
        assert response.status_code == status.HTTP_200_OK

    def test_update_location(self):
        """Test updating driver's current location."""
        user = DriverUserFactory()
        self._create_driver(user=user, status='approved')
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post('/api/v1/drivers/update_location/', {
            'latitude': 50.4501, 'longitude': 30.5234
        })
        assert response.status_code == status.HTTP_200_OK

    def test_nearby_drivers(self):
        """Test retrieving nearby drivers."""
        user = UserFactory()
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get('/api/v1/drivers/nearby/?lat=50.4501&lon=30.5234&radius=10')
        assert response.status_code == status.HTTP_200_OK

    def test_admin_approve_driver(self):
        """Test admin approving a driver."""
        admin = AdminUserFactory()
        driver = self._create_driver()
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.post(f'/api/v1/drivers/{driver.id}/approve/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'approved'

    def test_register_driver_invalid_data(self):
        """Test driver registration fails with invalid data."""
        user = UserFactory()
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post('/api/v1/drivers/register/', {
            'vehicle_plate': '', # invalid
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_driver_already_registered(self):
        """Test driver registration fails if already registered."""
        user = DriverUserFactory()
        self._create_driver(user=user)
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post('/api/v1/drivers/register/', {
            'vehicle_type': 'economy',
            'vehicle_make': 'Toyota', 'vehicle_model': 'Camry',
            'vehicle_year': 2020, 'vehicle_color': 'White',
            'vehicle_plate': 'REG002', 'license_number': 'DLREG002',
            'license_expiry': '2026-01-01',
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_driver_me_not_found(self):
        """Test retrieving current driver's profile when it doesn't exist."""
        user = DriverUserFactory()  # User with driver role, but no profile created yet
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get('/api/v1/drivers/me/')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_location_invalid_data(self):
        """Test updating driver's location with invalid data."""
        user = DriverUserFactory()
        self._create_driver(user=user, status='approved')
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post('/api/v1/drivers/update_location/', {
            'latitude': 'invalid', 'longitude': 'invalid'
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_update_location_exception(self):
        """Test updating driver's location raising exception in service."""
        user = DriverUserFactory()
        self._create_driver(user=user, status='approved')
        client = APIClient()
        client.force_authenticate(user=user)
        # Mock service to throw exception
        with pytest.MonkeyPatch.context() as m:
            from apps.drivers.services import DriverService
            def mock_update(*args, **kwargs):
                raise Exception("Service Error")
            m.setattr(DriverService, 'update_location', mock_update)

            response = client.post('/api/v1/drivers/update_location/', {
                'latitude': 50.4501, 'longitude': 30.5234
            })
            assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_set_availability_success(self):
        """Test setting driver availability successfully."""
        user = DriverUserFactory()
        self._create_driver(user=user, status='approved')
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.patch('/api/v1/drivers/availability/', {
            'availability': 'online'
        })
        assert response.status_code == status.HTTP_200_OK

    def test_set_availability_invalid(self):
        """Test setting driver availability fails with invalid data."""
        user = DriverUserFactory()
        self._create_driver(user=user, status='approved')
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.patch('/api/v1/drivers/availability/', {
            'availability': 'not-a-valid-choice'
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_set_availability_value_error(self):
        """Test setting driver availability fails for pending driver."""
        user = DriverUserFactory()
        self._create_driver(user=user, status='pending')
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.patch('/api/v1/drivers/availability/', {
            'availability': 'online'
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_nearby_drivers_invalid_params(self):
        """Test retrieving nearby drivers with invalid parameters."""
        user = UserFactory()
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get('/api/v1/drivers/nearby/?lat=invalid&lon=invalid')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_get_driver_list(self):
        """Test retrieving driver list (admin)."""
        admin = AdminUserFactory()
        self._create_driver()
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.get('/api/v1/drivers/')
        assert response.status_code == status.HTTP_200_OK

    def test_get_driver_detail(self):
        """Test retrieving driver detail (admin)."""
        admin = AdminUserFactory()
        driver = self._create_driver()
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.get(f'/api/v1/drivers/{driver.id}/')
        assert response.status_code == status.HTTP_200_OK

    def test_create_driver_default_serializer(self):
        """Fallback to default serializer."""
        admin = AdminUserFactory()
        client = APIClient()
        client.force_authenticate(user=admin)
        # Using post without action decorator uses DriverSerializer
        response = client.post('/api/v1/drivers/', {})
        # Fails validation but triggers get_serializer_class default branch
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_admin_approve_driver_not_found(self):
        """Test admin approving a non-existent driver."""
        admin = AdminUserFactory()
        client = APIClient()
        client.force_authenticate(user=admin)
        from uuid import uuid4
        response = client.post(f'/api/v1/drivers/{uuid4()}/approve/')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_admin_reject_driver(self):
        """Test admin rejecting a driver."""
        admin = AdminUserFactory()
        driver = self._create_driver()
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.post(f'/api/v1/drivers/{driver.id}/reject/', {'reason': 'Invalid docs'})
        assert response.status_code == status.HTTP_200_OK

    def test_admin_reject_driver_not_found(self):
        """Test admin rejecting a non-existent driver."""
        admin = AdminUserFactory()
        client = APIClient()
        client.force_authenticate(user=admin)
        from uuid import uuid4
        response = client.post(f'/api/v1/drivers/{uuid4()}/reject/')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_admin_suspend_driver(self):
        """Test admin suspending a driver."""
        admin = AdminUserFactory()
        driver = self._create_driver()
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.post(f'/api/v1/drivers/{driver.id}/suspend/', {'reason': 'Complaints'})
        assert response.status_code == status.HTTP_200_OK

    def test_admin_suspend_driver_not_found(self):
        """Test admin suspending a non-existent driver."""
        admin = AdminUserFactory()
        client = APIClient()
        client.force_authenticate(user=admin)
        from uuid import uuid4
        response = client.post(f'/api/v1/drivers/{uuid4()}/suspend/')
        assert response.status_code == status.HTTP_404_NOT_FOUND