from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html, mark_safe
from apps.rides.models import Ride
from core.admin_site import taxi_admin


@admin.register(Ride, site=taxi_admin)
class RideAdmin(admin.ModelAdmin):
    """Admin for Ride model with status badges and state machine validation"""
    list_display = [
        'id_short', 'user_email', 'driver_link', 'status_badge',
        'vehicle_type', 'estimated_price', 'final_price', 'rating_stars', 'created_at',
    ]
    list_filter = ['status', 'vehicle_type', 'created_at']
    search_fields = ['user__email', 'driver__user__email', 'pickup_address', 'dropoff_address']
    list_select_related = ['user', 'driver', 'driver__user']
    ordering = ['-created_at']
    readonly_fields = [
        'id', 'user', 'driver', 'pickup_location', 'dropoff_location',
        'created_at', 'accepted_at', 'started_at', 'completed_at', 'cancelled_at', 'updated_at',
    ]

    fieldsets = (
        ('Загально', {'fields': ('id', 'user', 'driver', 'status', 'vehicle_type')}),
        ('Адреси', {'fields': (
            'pickup_location', 'pickup_address', 'dropoff_location', 'dropoff_address'
        )}),
        ('Оплата', {'fields': (
            'estimated_distance', 'estimated_duration', 'estimated_price',
            'final_distance', 'final_duration', 'final_price', 'discount',
        )}),
        ('Оцінка', {'fields': ('rating', 'user_comment')}),
        ('Скасування', {'fields': ('cancellation_reason', 'cancellation_comment')}),
        ('Часові мітки', {'fields': (
            'created_at', 'accepted_at', 'started_at', 'completed_at', 'cancelled_at',
        ), 'classes': ('collapse',)}),
    )

    actions = ['cancel_rides']

    def cancel_rides(self, request, queryset):
        from django.utils import timezone
        active = queryset.filter(status__in=['pending', 'accepted'])
        updated = active.update(status='cancelled', cancelled_at=timezone.now(),
                                cancellation_reason='other', cancellation_comment='Скасовано адміністратором')
        self.message_user(request, f'Скасовано {updated} поїздок.')
    cancel_rides.short_description = 'Скасувати вибрані поїздки'

    def id_short(self, obj):
        return str(obj.id)[:8] + '...'
    id_short.short_description = 'ID'

    def user_email(self, obj):
        url = reverse('taxi_admin:users_user_change', args=[obj.user.pk])
        name = f'{obj.user.first_name} {obj.user.last_name}'.strip() or obj.user.email
        return mark_safe(f'<a href="{url}">{name}</a>')
    user_email.short_description = 'Пасажир'

    def driver_link(self, obj):
        if not obj.driver:
            return '—'
        url = reverse('taxi_admin:drivers_driver_change', args=[obj.driver.pk])
        name = f'{obj.driver.user.first_name} {obj.driver.user.last_name}'.strip() or obj.driver.user.email
        return mark_safe(f'<a href="{url}">{name}</a>')
    driver_link.short_description = 'Водій'

    def status_badge(self, obj):
        colors = {
            'pending': '#fd7e14', 'accepted': '#0d6efd', 'in_progress': '#6610f2',
            'completed': '#198754', 'cancelled': '#dc3545',
        }
        labels = {
            'pending': 'Очікує', 'accepted': 'Прийнята', 'in_progress': 'В дорозі',
            'completed': 'Завершена', 'cancelled': 'Скасована',
        }
        color = colors.get(obj.status, '#6c757d')
        label = labels.get(obj.status, obj.status)
        return mark_safe(
            f'<span style="background:{color};color:white;padding:2px 8px;border-radius:12px;'
            f'font-size:11px;white-space:nowrap;">{label}</span>'
        )
    status_badge.short_description = 'Статус'

    def rating_stars(self, obj):
        if not obj.rating:
            return '—'
        stars = '★' * obj.rating + '☆' * (5 - obj.rating)
        return mark_safe(f'<span style="color:#f59e0b;">{stars}</span>')
    rating_stars.short_description = 'Рейтинг'