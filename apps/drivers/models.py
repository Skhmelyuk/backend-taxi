"""Models for drivers app."""
import os
import uuid
from decimal import Decimal

from django.contrib.gis.db import models as gis_models
from django.contrib.gis.db.models.functions import Distance
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


def driver_document_upload_to(instance, filename: str) -> str:
    """Build upload path for driver documents."""
    base, ext = os.path.splitext(filename)
    ext = ext.lower() or '.dat'
    return (
        f"drivers/{instance.driver_id}/documents/"
        f"{instance.doc_type}/{uuid.uuid4()}{ext}"
    )


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
        PENDING = 'pending', 'Очікує перевірки'
        APPROVED = 'approved', 'Схвалено'
        REJECTED = 'rejected', 'Відхилено'
        SUSPENDED = 'suspended', 'Заблоковано'

    class Availability(models.TextChoices):
        ONLINE = 'online', 'Online'
        OFFLINE = 'offline', 'Offline'
        BUSY = 'busy', 'Зайнятий'

    class VehicleType(models.TextChoices):
        ECONOMY = 'economy', 'Економ'
        COMFORT = 'comfort', 'Комфорт'
        BUSINESS = 'business', 'Бізнес'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.OneToOneField(
        'users.User', on_delete=models.CASCADE,
        related_name='driver_profile',
        verbose_name='Користувач',
    )

    status = models.CharField(
        max_length=20, choices=Status.choices,
        default=Status.PENDING, db_index=True,
        verbose_name='Статус',
    )
    availability = models.CharField(
        max_length=20, choices=Availability.choices,
        default=Availability.OFFLINE, db_index=True,
        verbose_name='Доступність',
    )

    first_name = models.CharField(max_length=100, blank=True, default='', verbose_name="Ім'я")
    last_name  = models.CharField(max_length=100, blank=True, default='', verbose_name='Прізвище')

    vehicle_type = models.CharField(
        max_length=20, choices=VehicleType.choices,
        default=VehicleType.ECONOMY, blank=True,
        verbose_name='Тип авто',
    )
    vehicle_make  = models.CharField(max_length=100, blank=True, default='', verbose_name='Марка')
    vehicle_model = models.CharField(max_length=100, blank=True, default='', verbose_name='Модель')
    vehicle_year  = models.IntegerField(
        validators=[MinValueValidator(2000), MaxValueValidator(2030)],
        null=True, blank=True, verbose_name='Рік випуску',
    )
    vehicle_color = models.CharField(max_length=50, blank=True, default='', verbose_name='Колір')
    vehicle_plate = models.CharField(max_length=20, unique=True, null=True, blank=True, verbose_name='Номерний знак')

    license_number = models.CharField(max_length=50, unique=True, null=True, blank=True, verbose_name='Номер посвідчення')
    license_expiry = models.DateField(null=True, blank=True, verbose_name='Дійсне до')

    current_location = gis_models.PointField(
        geography=True, srid=4326, null=True, blank=True,
        verbose_name='Поточне місцезнаходження',
    )
    location_updated_at = models.DateTimeField(null=True, blank=True, verbose_name='Місцезнаходження оновлено')

    rating = models.DecimalField(
        max_digits=3, decimal_places=2, default=5.0,
        validators=[MinValueValidator(1.0), MaxValueValidator(5.0)],
        verbose_name='Рейтинг',
    )
    total_rides    = models.IntegerField(default=0, verbose_name='Всього поїздок')
    total_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Загальний заробіток')

    rejection_reason  = models.TextField(blank=True, verbose_name='Причина відмови')
    suspension_reason = models.TextField(blank=True, verbose_name='Причина блокування')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Створено')
    updated_at = models.DateTimeField(auto_now=True,       verbose_name='Оновлено')

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
        verbose_name = 'Водій'
        verbose_name_plural = 'Водії'

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


class DriverDocument(models.Model):
    """Stores driver verification documents (license, insurance, photos)."""

    class DocumentType(models.TextChoices):
        DRIVER_LICENSE        = 'driver_license',        'Водійське посвідчення'
        VEHICLE_REGISTRATION  = 'vehicle_registration',  'Техпаспорт'
        INSURANCE_POLICY      = 'insurance_policy',      'Страховий поліс'
        VEHICLE_PHOTO         = 'vehicle_photo',         'Фото авто 1'
        VEHICLE_PHOTO_2       = 'vehicle_photo_2',       'Фото авто 2'
        VEHICLE_PHOTO_3       = 'vehicle_photo_3',       'Фото авто 3'

    class VerificationStatus(models.TextChoices):
        PENDING  = 'pending',  'Очікує перевірки'
        APPROVED = 'approved', 'Схвалено'
        REJECTED = 'rejected', 'Відхилено'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    driver = models.ForeignKey(
        Driver,
        on_delete=models.CASCADE,
        related_name='documents',
        help_text='Driver profile owner',
    )
    doc_type = models.CharField(
        max_length=50,
        choices=DocumentType.choices,
        verbose_name='Тип документа',
    )
    file = models.FileField(
        upload_to=driver_document_upload_to,
        max_length=500,
        verbose_name='Файл',
    )
    status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
        verbose_name='Статус',
    )
    notes      = models.TextField(blank=True, verbose_name='Нотатки')
    expires_at = models.DateField(null=True, blank=True, verbose_name='Дійсне до')
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name='Завантажено')
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name='Перевірено')
    reviewer = models.ForeignKey(
        'users.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='reviewed_documents',
        verbose_name='Перевіряв',
    )

    class Meta:
        db_table = 'driver_documents'
        ordering = ['-uploaded_at']
        unique_together = ('driver', 'doc_type')
        verbose_name = 'Документ водія'
        verbose_name_plural = 'Документи водія'

    def __str__(self) -> str:
        return f"{self.driver.user.email} → {self.doc_type} ({self.status})"