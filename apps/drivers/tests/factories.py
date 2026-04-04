import factory
from factory.django import DjangoModelFactory
from django.contrib.gis.geos import Point
from apps.drivers.models import Driver
from apps.users.tests.factories import DriverUserFactory
import random


class DriverFactory(DjangoModelFactory):
    """Factory for creating Driver instances for testing."""
    class Meta:
        model = Driver

    user = factory.SubFactory(DriverUserFactory)
    status = Driver.Status.APPROVED
    availability = Driver.Availability.ONLINE
    vehicle_type = Driver.VehicleType.ECONOMY
    vehicle_make = factory.Faker('company')
    vehicle_model = factory.Sequence(lambda n: f'Model-{n}')
    vehicle_year = 2020
    vehicle_color = 'White'
    vehicle_plate = factory.Sequence(lambda n: f'AA{n:04d}ZZ')
    license_number = factory.Sequence(lambda n: f'DL{n:06d}')
    license_expiry = '2027-01-01'
    current_location = factory.LazyFunction(
        lambda: Point(30.5234 + random.uniform(-0.1, 0.1),
                      50.4501 + random.uniform(-0.1, 0.1), srid=4326)
    )
    rating = 4.8
    total_rides = 10


class PendingDriverFactory(DriverFactory):
    """Factory for creating Driver instances with pending status."""
    status = Driver.Status.PENDING
    availability = Driver.Availability.OFFLINE
    current_location = None