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
        PENDING = 'pending', 'Очікує'
        PROCESSING = 'processing', 'Обробляється'
        SUCCESS = 'success', 'Успішно'
        FAILED = 'failed', 'Помилка'
        REFUNDED = 'refunded', 'Повернуто'
        CANCELLED = 'cancelled', 'Скасовано'
        EXPIRED = 'expired', 'Строк сплив'
        PARTIAL_REFUND = 'partial_refund', 'Часткове повернення'

    class PaymentMethod(models.TextChoices):
        CARD = 'card', 'Картка'
        GOOGLE_PAY = 'google_pay', 'Google Pay'
        APPLE_PAY = 'apple_pay', 'Apple Pay'
        CASH = 'cash', 'Готівка'

    class Provider(models.TextChoices):
        LIQPAY = 'liqpay', 'LiqPay'
        FONDY = 'fondy', 'Fondy'
        CASH = 'cash', 'Готівка'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ride = models.ForeignKey('rides.Ride', on_delete=models.PROTECT, related_name='payments', verbose_name='Поїздка')
    user = models.ForeignKey('users.User', on_delete=models.PROTECT, related_name='payments', verbose_name='Користувач')
    amount = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='Сума',
    )
    currency = models.CharField(max_length=3, default='UAH', verbose_name='Валюта')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True, verbose_name='Статус')
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, verbose_name='Спосіб оплати')
    provider = models.CharField(max_length=20, choices=Provider.choices, verbose_name='Провайдер')
    provider_transaction_id = models.CharField(max_length=255, unique=True, null=True, blank=True, db_index=True, verbose_name='ID транзакції')
    provider_data = models.JSONField(default=dict, blank=True, verbose_name='Дані провайдера')
    description = models.TextField(blank=True, verbose_name='Опис')
    error_message = models.TextField(blank=True, verbose_name='Повідомлення про помилку')
    created_at   = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Створено')
    processed_at = models.DateTimeField(null=True, blank=True, verbose_name='Оброблено')
    failed_at    = models.DateTimeField(null=True, blank=True, verbose_name='Помилка о')
    refunded_at  = models.DateTimeField(null=True, blank=True, verbose_name='Повернуто о')
    updated_at   = models.DateTimeField(auto_now=True, verbose_name='Оновлено')

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
        verbose_name = 'Платіж'
        verbose_name_plural = 'Платежі'

    def __str__(self) -> str:
        return f"Payment {self.id} ({self.status}) {self.amount} {self.currency}"


class PromoCode(models.Model):
    """Model representing a promotional code for discounts on rides."""
    class DiscountType(models.TextChoices):
        PERCENTAGE = 'percentage', 'Відсоткова'
        FIXED = 'fixed', 'Фіксова сума'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True, db_index=True, verbose_name='Код')
    discount_type = models.CharField(max_length=20, choices=DiscountType.choices, default=DiscountType.PERCENTAGE, verbose_name='Тип знижки')
    discount_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Відсоток знижки (%)',
    )
    discount_amount  = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Сума знижки')
    max_discount     = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='Макс знижка')
    min_ride_price   = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Мін сума поїздки')
    is_active        = models.BooleanField(default=True, verbose_name='Активний')
    usage_limit      = models.IntegerField(null=True, blank=True, verbose_name='Ліміт використань')
    usage_count      = models.IntegerField(default=0, verbose_name='Кількість використань')
    valid_from       = models.DateTimeField(default=timezone.now, verbose_name='Дійсний з')
    valid_until      = models.DateTimeField(null=True, blank=True, verbose_name='Дійсний до')
    created_at       = models.DateTimeField(auto_now_add=True, verbose_name='Створено')

    class Meta:
        db_table = 'promo_codes'
        verbose_name = 'Промокод'
        verbose_name_plural = 'Промокоди'

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
        PENDING = 'pending', 'Очікує'
        PROCESSING = 'processing', 'Обробляється'
        SUCCESS = 'success', 'Успішно'
        FAILED = 'failed', 'Помилка'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment            = models.ForeignKey(Payment, on_delete=models.PROTECT, related_name='refunds', verbose_name='Платіж')
    amount             = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Сума')
    reason             = models.TextField(verbose_name='Причина')
    status             = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, verbose_name='Статус')
    provider_refund_id = models.CharField(max_length=255, blank=True, verbose_name='ID повернення')
    created_at         = models.DateTimeField(auto_now_add=True, verbose_name='Створено')
    processed_at       = models.DateTimeField(null=True, blank=True, verbose_name='Оброблено')

    class Meta:
        db_table = 'refunds'
        verbose_name = 'Повернення'
        verbose_name_plural = 'Повернення'

    def __str__(self) -> str:
        return f"Refund {self.id} ({self.status}) {self.amount}"
