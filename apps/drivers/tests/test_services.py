"""
Tests for DriverService functions.
"""

import pytest
from unittest.mock import patch
from apps.drivers.models import Driver
from apps.drivers.services import DriverService
from apps.users.tests.factories import UserFactory, AdminUserFactory


@pytest.mark.django_db
class TestDriverService:

    def _create_approved_driver(self):
        """Helper to create an approved driver."""
        user = UserFactory(role='driver')
        return Driver.objects.create(
            user=user, status='approved', availability='offline',
            vehicle_make='Toyota', vehicle_model='Camry',
            vehicle_year=2020, vehicle_color='White',
            vehicle_plate='SVC1234', license_number='DLSVC001',
            license_expiry='2026-01-01'
        )

    def test_register_driver(self):
        """Test registering a new driver."""
        user = UserFactory()
        driver = DriverService.register_driver(
            user,
            vehicle_make='Toyota', vehicle_model='Camry',
            vehicle_year=2020, vehicle_color='White',
            vehicle_plate='REG1234', license_number='DLREG001',
            license_expiry='2026-01-01'
        )
        assert driver.status == Driver.Status.PENDING
        user.refresh_from_db()
        assert user.role == 'driver'

    def test_register_driver_already_exists(self):
        """Test registering a driver when user already has a driver profile."""
        driver = self._create_approved_driver()
        with pytest.raises(ValueError, match='already registered'):
            DriverService.register_driver(driver.user)

    def test_approve_driver(self):
        """Test approving a driver."""
        user = UserFactory(role='driver')
        driver = Driver.objects.create(
            user=user, vehicle_make='T', vehicle_model='C',
            vehicle_year=2020, vehicle_color='W',
            vehicle_plate='APP1234', license_number='DLAPP001',
            license_expiry='2026-01-01'
        )
        admin = AdminUserFactory()
        result = DriverService.approve_driver(str(driver.id), admin)
        assert result.status == Driver.Status.APPROVED

    def test_approve_driver_already_approved(self):
        """Test approving a driver that is already approved raises an error."""
        driver = self._create_approved_driver()
        admin = AdminUserFactory()
        with pytest.raises(ValueError, match='Driver already approved'):
            DriverService.approve_driver(str(driver.id), admin)

    def test_suspend_driver(self):
        """Test suspending a driver."""
        driver = self._create_approved_driver()
        admin = AdminUserFactory()
        reason = "Multiple complaints"
        
        result = DriverService.suspend_driver(str(driver.id), reason, admin)
        
        assert result.status == Driver.Status.SUSPENDED
        assert result.availability == Driver.Availability.OFFLINE
        assert result.suspension_reason == reason

    def test_update_location(self):
        """Test updating driver's current location."""
        driver = self._create_approved_driver()
        result = DriverService.update_location(driver, 50.4501, 30.5234)
        assert result.current_location is not None
        assert abs(result.current_location.y - 50.4501) < 0.001

    def test_set_availability(self):
        """Test setting driver availability."""
        driver = self._create_approved_driver()
        result = DriverService.set_availability(driver, 'online')
        assert result.availability == Driver.Availability.ONLINE

    def test_set_availability_pending_driver(self):
        """Test setting availability for a driver that is not approved."""
        user = UserFactory(role='driver')
        driver = Driver.objects.create(
            user=user, status='pending', vehicle_make='T', vehicle_model='C',
            vehicle_year=2020, vehicle_color='W', vehicle_plate='PND1234',
            license_number='DLPND001', license_expiry='2026-01-01'
        )
        with pytest.raises(ValueError, match='Only approved'):
            DriverService.set_availability(driver, 'online')

    @patch('apps.drivers.models.Driver.objects')
    def test_get_nearby_drivers_with_type(self, mock_objects):
        """Test getting nearby drivers with vehicle type filter."""
        # Мокаємо queryset, який повертає nearby_by_type
        mock_objects.nearby_by_type.return_value = ["driver1", "driver2"]
        
        result = DriverService.get_nearby_drivers(
            latitude=50.4501, 
            longitude=30.5234, 
            vehicle_type='sedan', 
            radius_km=5
        )
        assert result == ["driver1", "driver2"]
        mock_objects.nearby_by_type.assert_called_once_with(50.4501, 30.5234, 'sedan', 5)

    def test_update_driver_rating_success(self):
        """Test updating driver rating successfully."""
        driver = self._create_approved_driver()
        # Assuming the driver has an initial rating of 0 or null, update_rating should work
        result = DriverService.update_driver_rating(driver, 4.5)
        
        # The exact value depends on your implementation of update_rating in the model
        # Check that the rating has been changed and is equal to the expected one
        assert result.rating > 0

    def test_update_driver_rating_invalid(self):
        """Test updating driver rating with invalid value raises ValueError."""
        driver = self._create_approved_driver()
        
        with pytest.raises(ValueError, match='Rating must be between 1.0 and 5.0'):
            DriverService.update_driver_rating(driver, 6.0)
            
        with pytest.raises(ValueError, match='Rating must be between 1.0 and 5.0'):
            DriverService.update_driver_rating(driver, 0.5)