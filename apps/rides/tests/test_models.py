import pytest
from decimal import Decimal
from django.contrib.gis.geos import Point
from apps.rides.models import Ride
from apps.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestRideModel:

    def _create_ride(self, user=None, **kwargs):
        user = user or UserFactory()
        defaults = {
            'vehicle_type': 'economy',
            'pickup_location': Point(30.5234, 50.4501, srid=4326),
            'dropoff_location': Point(30.6234, 50.4601, srid=4326),
            'pickup_address': 'Pickup Address',
            'dropoff_address': 'Dropoff Address',
            'estimated_distance': Decimal('8.5'),
            'estimated_duration': 25,
            'estimated_price': Decimal('115.0'),
        }
        defaults.update(kwargs)
        return Ride.objects.create(user=user, **defaults)

    def test_create_ride(self):
        ride = self._create_ride()
        assert ride.status == Ride.Status.PENDING
        assert ride.is_active is True
        assert ride.driver is None

    def test_ride_status_flow(self):
        ride = self._create_ride()
        assert ride.status == 'pending'
        ride.status = 'completed'
        ride.save()
        assert not ride.is_active

    def test_ride_manager_active(self):
        user = UserFactory()
        self._create_ride(user=user, status='pending')
        self._create_ride(user=user, status='completed')
        active = Ride.objects.active()
        assert active.count() == 1

    def test_ride_manager_for_user(self):
        user1 = UserFactory()
        user2 = UserFactory()
        self._create_ride(user=user1)
        self._create_ride(user=user2)
        assert Ride.objects.for_user(user1).count() == 1