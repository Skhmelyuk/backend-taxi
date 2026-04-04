"""
Models for rides app.
"""

import uuid
from django.db import models
from django.contrib.gis.db import models as gis_models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class RideManager(models.Manager):

    def get_queryset(self):
        return super().get_queryset().select_related('user', 'driver')

    def active(self):
        return self.filter(status__in=['pending', 'accepted', 'in_progress'])

    def for_user(self, user):
        return self.filter(user=user)

    def for_driver(self, driver):
        return self.filter(driver=driver)

    def completed(self):
        return self.filter(status='completed')

    def pending(self):
        return self.filter(status='pending')


class Ride(models.Model):

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        ACCEPTED = 'accepted', 'Accepted'
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'

    class VehicleType(models.TextChoices):
        ECONOMY = 'economy', 'Economy'
        COMFORT = 'comfort', 'Comfort'
        BUSINESS = 'business', 'Business'

    class CancellationReason(models.TextChoices):
        USER_CANCELLED = 'user_cancelled', 'User Cancelled'
        DRIVER_CANCELLED = 'driver_cancelled', 'Driver Cancelled'
        NO_DRIVERS = 'no_drivers', 'No Drivers Available'
        TIMEOUT = 'timeout', 'Timeout'
        OTHER = 'other', 'Other'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        'users.User', on_delete=models.PROTECT, related_name='rides'
    )
    driver = models.ForeignKey(
        'drivers.Driver', on_delete=models.PROTECT,
        related_name='rides', null=True, blank=True
    )

    status = models.CharField(
        max_length=20, choices=Status.choices,
        default=Status.PENDING, db_index=True
    )
    vehicle_type = models.CharField(max_length=20, choices=VehicleType.choices)

    pickup_location = gis_models.PointField(geography=True, srid=4326)
    dropoff_location = gis_models.PointField(geography=True, srid=4326)
    pickup_address = models.TextField()
    dropoff_address = models.TextField()

    estimated_distance = models.DecimalField(max_digits=10, decimal_places=2)
    estimated_duration = models.IntegerField()
    estimated_price = models.DecimalField(max_digits=10, decimal_places=2)

    final_distance = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    final_duration = models.IntegerField(null=True, blank=True)
    final_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    discount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        validators=[MinValueValidator(0)]
    )

    promo_code = models.ForeignKey(
        'payments.PromoCode', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='rides'
    )

    rating = models.IntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    user_comment = models.TextField(blank=True)
    cancellation_reason = models.CharField(
        max_length=50, choices=CancellationReason.choices,
        blank=True
    )
    cancellation_comment = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = RideManager()

    class Meta:
        db_table = 'rides'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['driver', 'status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['vehicle_type']),
        ]
        verbose_name = 'Ride'
        verbose_name_plural = 'Rides'

    def __str__(self):
        return f"Ride {self.id} ({self.status})"

    @property
    def duration_minutes(self) -> int | None:
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return int(delta.total_seconds() / 60)
        return None

    @property
    def is_active(self) -> bool:
        return self.status in [self.Status.PENDING, self.Status.ACCEPTED, self.Status.IN_PROGRESS]
    
VALID_STATUS_TRANSITIONS = {
    Ride.Status.PENDING: [Ride.Status.ACCEPTED, Ride.Status.CANCELLED],
    Ride.Status.ACCEPTED: [Ride.Status.IN_PROGRESS, Ride.Status.CANCELLED],
    Ride.Status.IN_PROGRESS: [Ride.Status.COMPLETED, Ride.Status.CANCELLED],
    Ride.Status.COMPLETED: [],
    Ride.Status.CANCELLED: [],
}


def validate_status_transition(current_status: str, new_status: str) -> bool:
    """Validate if status transition is allowed."""
    return new_status in VALID_STATUS_TRANSITIONS.get(current_status, [])