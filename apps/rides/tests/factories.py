import factory
from factory.django import DjangoModelFactory
from decimal import Decimal
from django.contrib.gis.geos import Point
from apps.rides.models import Ride
from apps.users.tests.factories import UserFactory
from apps.drivers.tests.factories import DriverFactory


class RideFactory(DjangoModelFactory):
    """Factory for creating Ride instances for testing."""
    class Meta:
        model = Ride

    user = factory.SubFactory(UserFactory)
    driver = None
    status = Ride.Status.PENDING
    vehicle_type = Ride.VehicleType.ECONOMY
    pickup_location = factory.LazyFunction(lambda: Point(30.5234, 50.4501, srid=4326))
    dropoff_location = factory.LazyFunction(lambda: Point(30.6234, 50.4601, srid=4326))
    pickup_address = 'вул. Хрещатик 1, Київ'
    dropoff_address = 'вул. Велика Васильківська 45, Київ'
    estimated_distance = Decimal('8.5')
    estimated_duration = 25
    estimated_price = Decimal('115.0')
    discount = Decimal('0.0')


class CompletedRideFactory(RideFactory):
    """Factory for creating completed Ride instances for testing."""
    status = Ride.Status.COMPLETED
    driver = factory.SubFactory(DriverFactory)
    final_distance = Decimal('8.7')
    final_duration = 27
    final_price = Decimal('118.0')
    rating = 5


class ActiveRideFactory(RideFactory):
    """Factory for creating active Ride instances (accepted or in progress) for testing."""
    status = Ride.Status.IN_PROGRESS
    driver = factory.SubFactory(DriverFactory)