"""
Models for payments app.
"""

import uuid
from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class PaymentManager(models.Manager):
    """Custom manager for Payment model to add common query methods."""
    def get_queryset(self):
        return super().get_queryset().select_related('user', 'ride')

    def successful(self):
        return self.filter(status='success')

    def pending(self):
        return self.filter(status='pending')

    def for_user(self, user):
        return self.filter(user=user)

    def for_ride(self, ride):
        return self.filter(ride=ride)


class Payment(models.Model):
    """Model representing a payment for a ride."""
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PROCESSING = 'processing', 'Processing'
        SUCCESS = 'success', 'Success'
        FAILED = 'failed', 'Failed'
        REFUNDED = 'refunded', 'Refunded'
        CANCELLED = 'cancelled', 'Cancelled'
        EXPIRED = 'expired', 'Expired'
        PARTIAL_REFUND = 'partial_refund', 'Partial Refund'

    class PaymentMethod(models.TextChoices):
        CARD = 'card', 'Card'
        GOOGLE_PAY = 'google_pay', 'Google Pay'
        APPLE_PAY = 'apple_pay', 'Apple Pay'
        CASH = 'cash', 'Cash'

    class Provider(models.TextChoices):
        LIQPAY = 'liqpay', 'LiqPay'
        FONDY = 'fondy', 'Fondy'
        CASH = 'cash', 'Cash'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ride = models.ForeignKey('rides.Ride', on_delete=models.PROTECT, related_name='payments')
    user = models.ForeignKey('users.User', on_delete=models.PROTECT, related_name='payments')
    amount = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))]
    )
    currency = models.CharField(max_length=3, default='UAH')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    provider = models.CharField(max_length=20, choices=Provider.choices)
    provider_transaction_id = models.CharField(max_length=255, unique=True, null=True, blank=True, db_index=True)
    provider_data = models.JSONField(default=dict, blank=True)
    description = models.TextField(blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    refunded_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = PaymentManager()

    class Meta:
        db_table = 'payments'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['provider_transaction_id']),
            models.Index(fields=['created_at']),
        ]
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'

    def __str__(self) -> str:
        return f"Payment {self.id} ({self.status}) {self.amount} {self.currency}"


class PromoCode(models.Model):
    """Model representing a promotional code for discounts on rides."""
    class DiscountType(models.TextChoices):
        PERCENTAGE = 'percentage', 'Percentage'
        FIXED = 'fixed', 'Fixed Amount'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True, db_index=True)
    discount_type = models.CharField(max_length=20, choices=DiscountType.choices, default=DiscountType.PERCENTAGE)
    discount_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    min_ride_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    usage_limit = models.IntegerField(null=True, blank=True)
    usage_count = models.IntegerField(default=0)
    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'promo_codes'
        verbose_name = 'Promo Code'
        verbose_name_plural = 'Promo Codes'

    def __str__(self) -> str:
        return self.code

    @property
    def is_valid(self) -> bool:
        now = timezone.now()
        if not self.is_active:
            return False
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        if self.usage_limit and self.usage_count >= self.usage_limit:
            return False
        return True


class Refund(models.Model):
    """Model representing a refund for a payment."""
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PROCESSING = 'processing', 'Processing'
        SUCCESS = 'success', 'Success'
        FAILED = 'failed', 'Failed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(Payment, on_delete=models.PROTECT, related_name='refunds')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    provider_refund_id = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'refunds'
        verbose_name = 'Refund'

    def __str__(self) -> str:
        return f"Refund {self.id} ({self.status}) {self.amount}"
