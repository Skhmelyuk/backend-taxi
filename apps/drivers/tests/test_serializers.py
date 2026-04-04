"""
Tests for Driver serializers. 
"""

import pytest
from django.contrib.gis.geos import Point
from apps.drivers.models import Driver
from apps.drivers.serializers import (
    DriverSerializer, DriverRegistrationSerializer, DriverLocationSerializer
)
from apps.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestDriverRegistrationSerializer:

    def test_valid_data(self):
        data = {
            'vehicle_type': 'economy',
            'vehicle_make': 'Toyota',
            'vehicle_model': 'Camry',
            'vehicle_year': 2020,
            'vehicle_color': 'White',
            'vehicle_plate': 'AA1234ZZ',
            'license_number': 'DL000001',
            'license_expiry': '2026-01-01',
        }
        serializer = DriverRegistrationSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_duplicate_plate(self):
        user = UserFactory(role='driver')
        Driver.objects.create(
            user=user, vehicle_make='Toyota', vehicle_model='Camry',
            vehicle_year=2020, vehicle_color='White', vehicle_plate='AA1234ZZ',
            license_number='DL000001', license_expiry='2026-01-01'
        )
        serializer = DriverRegistrationSerializer(data={
            'vehicle_type': 'economy', 'vehicle_make': 'BMW', 'vehicle_model': 'X5',
            'vehicle_year': 2021, 'vehicle_color': 'Black', 'vehicle_plate': 'AA1234ZZ',
            'license_number': 'DL000002', 'license_expiry': '2026-01-01',
        })
        assert not serializer.is_valid()
        assert 'vehicle_plate' in serializer.errors


@pytest.mark.django_db
class TestDriverLocationSerializer:

    def test_valid_location(self):
        serializer = DriverLocationSerializer(data={'latitude': 50.4501, 'longitude': 30.5234})
        assert serializer.is_valid()

    def test_invalid_latitude(self):
        serializer = DriverLocationSerializer(data={'latitude': 91.0, 'longitude': 30.5234})
        assert not serializer.is_valid()