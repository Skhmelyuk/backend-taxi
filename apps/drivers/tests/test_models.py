import pytest
from django.contrib.gis.geos import Point
from apps.drivers.models import Driver
from apps.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestDriverModel:

    def test_create_driver(self):
        user = UserFactory(role='driver')
        driver = Driver.objects.create(
            user=user,
            vehicle_make='Toyota', vehicle_model='Camry',
            vehicle_year=2020, vehicle_color='White',
            vehicle_plate='AA1234BB',
            license_number='DL123456', license_expiry='2026-01-01'
        )
        assert driver.status == Driver.Status.PENDING
        assert driver.availability == Driver.Availability.OFFLINE
        assert driver.is_available is False

    def test_update_location(self):
        user = UserFactory(role='driver')
        driver = Driver.objects.create(
            user=user, vehicle_make='Toyota', vehicle_model='Camry',
            vehicle_year=2020, vehicle_color='White', vehicle_plate='AA1234CC',
            license_number='DL123457', license_expiry='2026-01-01'
        )
        driver.update_location(50.4501, 30.5234)
        assert driver.current_location is not None
        assert abs(driver.current_location.y - 50.4501) < 0.001

    def test_update_rating(self):
        user = UserFactory(role='driver')
        driver = Driver.objects.create(
            user=user, vehicle_make='Toyota', vehicle_model='Camry',
            vehicle_year=2020, vehicle_color='White', vehicle_plate='AA1234DD',
            license_number='DL123458', license_expiry='2026-01-01',
            rating=5.0, total_rides=0
        )
        driver.update_rating(4.0)
        assert driver.total_rides == 1
        assert driver.rating == 4.0

    def test_nearby_drivers(self):
        user = UserFactory(role='driver')
        driver = Driver.objects.create(
            user=user, status='approved', availability='online',
            vehicle_make='Toyota', vehicle_model='Camry',
            vehicle_year=2020, vehicle_color='White', vehicle_plate='AA1234EE',
            license_number='DL123459', license_expiry='2026-01-01',
            current_location=Point(30.5234, 50.4501, srid=4326)
        )
        nearby = Driver.objects.nearby(50.4501, 30.5234, radius_km=1)
        assert driver in nearby


@pytest.mark.django_db
class TestDriverManager:

    def _create_driver(self, lat, lon, status='approved', availability='online', **kwargs):
        from apps.users.tests.factories import UserFactory
        import random
        user = UserFactory(role='driver')
        return Driver.objects.create(
            user=user, status=status, availability=availability,
            vehicle_make='Toyota', vehicle_model='Camry',
            vehicle_year=2020, vehicle_color='White',
            vehicle_plate=f'TEST{random.randint(1000,9999)}',
            license_number=f'DL{random.randint(100000,999999)}',
            license_expiry='2026-01-01',
            current_location=Point(lon, lat, srid=4326),
            **kwargs
        )

    def test_available_drivers(self):
        self._create_driver(50.4501, 30.5234, status='approved', availability='online')
        self._create_driver(50.4502, 30.5235, status='pending', availability='online')
        self._create_driver(50.4503, 30.5236, status='approved', availability='offline')
        assert Driver.objects.available().count() == 1

    def test_nearby_drivers(self):
        self._create_driver(50.4501, 30.5234)  # ~0 km
        self._create_driver(50.5501, 30.5234)  # ~11 km
        nearby = Driver.objects.nearby(50.4501, 30.5234, radius_km=5)
        assert nearby.count() == 1

    def test_nearby_by_type(self):
        self._create_driver(50.4501, 30.5234, vehicle_type='economy')
        self._create_driver(50.4502, 30.5235, vehicle_type='comfort')
        economy = Driver.objects.nearby_by_type(50.4501, 30.5234, 'economy', radius_km=5)
        assert economy.count() == 1