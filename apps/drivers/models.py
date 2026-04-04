"""
Models for drivers app.
"""
import uuid
from django.contrib.gis.db.models.functions import Distance
from django.db import models
from django.contrib.gis.db import models as gis_models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal


class DriverManager(models.Manager):

    def get_queryset(self):
        return super().get_queryset().select_related('user')

    def available(self):
        """Drivers with approved status and availability online."""
        return self.filter(status='approved', availability='online')

    def by_vehicle_type(self, vehicle_type: str):
       """Available drivers by car type."""
       return self.available().filter(vehicle_type=vehicle_type)

    def nearby(self, latitude, longitude, radius_km=10):
        """Nearest available drivers within radius_km km."""
        from django.contrib.gis.geos import Point
        from django.contrib.gis.measure import D
        location = Point(longitude, latitude, srid=4326)
        return self.available().filter(
            current_location__distance_lte=(location, D(km=radius_km))
        ).annotate(
            distance=Distance('current_location', location)
        ).order_by('distance')
    
    def nearby_by_type(self, latitude: float, longitude: float,
                        vehicle_type: str, radius_km: float = 10):
        """Nearest available drivers by car type."""
        from django.contrib.gis.geos import Point
        from django.contrib.gis.measure import D
        location = Point(longitude, latitude, srid=4326)
        return self.available().filter(
            vehicle_type=vehicle_type,
            current_location__isnull=False,
            current_location__distance_lte=(location, D(km=radius_km))
        ).annotate(
            distance=Distance('current_location', location)
        ).order_by('distance')

    def top_rated(self, limit: int = 10):
        """Highest rated drivers."""
        return self.filter(
            status='approved',
            total_rides__gte=5
        ).order_by('-rating')[:limit]


class Driver(models.Model):

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending Verification'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        SUSPENDED = 'suspended', 'Suspended'

    class Availability(models.TextChoices):
        ONLINE = 'online', 'Online'
        OFFLINE = 'offline', 'Offline'
        BUSY = 'busy', 'Busy'

    class VehicleType(models.TextChoices):
        ECONOMY = 'economy', 'Economy'
        COMFORT = 'comfort', 'Comfort'
        BUSINESS = 'business', 'Business'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.OneToOneField(
        'users.User', on_delete=models.CASCADE,
        related_name='driver_profile',
        help_text='User associated with this driver'
    )

    status = models.CharField(
        max_length=20, choices=Status.choices,
        default=Status.PENDING, db_index=True
    )
    availability = models.CharField(
        max_length=20, choices=Availability.choices,
        default=Availability.OFFLINE, db_index=True
    )

    vehicle_type = models.CharField(
        max_length=20, choices=VehicleType.choices, default=VehicleType.ECONOMY
    )
    vehicle_make = models.CharField(max_length=100)
    vehicle_model = models.CharField(max_length=100)
    vehicle_year = models.IntegerField(
        validators=[MinValueValidator(2000), MaxValueValidator(2030)]
    )
    vehicle_color = models.CharField(max_length=50)
    vehicle_plate = models.CharField(max_length=20, unique=True)

    license_number = models.CharField(max_length=50, unique=True)
    license_expiry = models.DateField()

    current_location = gis_models.PointField(
        geography=True, srid=4326, null=True, blank=True,
        help_text='Current GPS location'
    )
    location_updated_at = models.DateTimeField(null=True, blank=True)

    rating = models.DecimalField(
        max_digits=3, decimal_places=2,
        default=5.0,
        validators=[MinValueValidator(1.0), MaxValueValidator(5.0)]
    )
    total_rides = models.IntegerField(default=0)
    total_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    rejection_reason = models.TextField(blank=True)
    suspension_reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = DriverManager()

    class Meta:
        db_table = 'drivers'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['availability']),
            models.Index(fields=['vehicle_type']),
            models.Index(fields=['rating']),
        ]
        verbose_name = 'Driver'
        verbose_name_plural = 'Drivers'

    def __str__(self) -> str:
        return f"Driver: {self.user.email} ({self.status})"

    def update_location(self, latitude: float, longitude: float) -> None:
        from django.contrib.gis.geos import Point
        self.current_location = Point(longitude, latitude, srid=4326)
        self.location_updated_at = timezone.now()
        self.save(update_fields=['current_location', 'location_updated_at'])

    def update_rating(self, new_rating: float) -> None:
        from decimal import Decimal
        current_rating = Decimal(str(self.rating))
        new_rating_dec = Decimal(str(new_rating))
        total = (current_rating * self.total_rides + new_rating_dec) / (self.total_rides + 1)
        self.rating = round(total, 2)
        self.total_rides += 1
        self.save(update_fields=['rating', 'total_rides'])

    @property
    def is_available(self) -> bool:
        return self.status == self.Status.APPROVED and self.availability == self.Availability.ONLINE