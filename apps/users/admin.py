from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.urls import reverse
from django.utils.html import format_html, mark_safe
from apps.users.models import User
from apps.drivers.models import Driver
from core.admin_site import taxi_admin


class DriverInline(admin.StackedInline):
    """Inline block to display linked driver profile."""

    model = Driver
    can_delete = False
    extra = 0
    fk_name = 'user'
    fieldsets = (
        ('Статус та доступність', {
            'fields': ('status', 'availability'),
        }),
        ('Автомобіль', {
            'fields': (
                'vehicle_type', 'vehicle_make', 'vehicle_model', 'vehicle_year',
                'vehicle_color', 'vehicle_plate',
            ),
        }),
        ('Водійське посвідчення', {
            'fields': ('license_number', 'license_expiry'),
        }),
        ('Службова інформація', {
            'classes': ('collapse',),
            'fields': ('rating', 'total_rides', 'total_earnings', 'created_at', 'updated_at'),
        }),
    )
    readonly_fields = ('rating', 'total_rides', 'total_earnings', 'created_at', 'updated_at')


@admin.register(User, site=taxi_admin)
class UserAdmin(BaseUserAdmin):
    """Admin interface for User model."""

    list_display = [
        'photo_preview', 'email', 'full_name', 'roles_badge', 'is_verified_badge',
        'is_active', 'driver_profile_link', 'created_at',
    ]
    list_filter = ['is_passenger', 'is_driver', 'is_staff', 'is_active', 'is_verified', 'created_at']
    search_fields = ['email', 'first_name', 'last_name', 'phone_number', 'clerk_user_id']
    ordering = ['-created_at']
    readonly_fields = ['id', 'clerk_user_id', 'created_at', 'updated_at', 'last_login', 'photo_preview', 'driver_profile_link']

    fieldsets = (
        ('Загальна інформація', {
            'fields': ('id', 'email', 'first_name', 'last_name', 'phone_number',
                       'photo_preview', 'profile_image', 'date_of_birth')
        }),
        ('Інтеграція Clerk', {
            'fields': ('clerk_user_id',),
            'classes': ('collapse',),
        }),
        ('Ролі та дозволи', {
            'fields': ('is_passenger', 'is_driver', 'is_staff', 'is_superuser',
                       'is_active', 'is_verified', 'groups', 'user_permissions')
        }),
        ('Профіль водія', {
            'fields': ('driver_profile_link',),
        }),
        ('Сповіщення', {
            'fields': ('fcm_token',),
            'classes': ('collapse',),
        }),
        ('Службова інформація', {
            'fields': ('created_at', 'updated_at', 'last_login'),
            'classes': ('collapse',),
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'is_passenger', 'is_driver'),
        }),
    )

    inlines = [DriverInline]

    USERNAME_FIELD = 'email'

    def full_name(self, obj) -> str:
        return obj.full_name or '—'
    full_name.short_description = "Ім'я"

    def photo_preview(self, obj) -> str:
        if obj.profile_image:
            return mark_safe(
                f'<img src="{obj.profile_image}" style="width:48px;height:48px;border-radius:50%;'
                f'border:2px solid #dee2e6;object-fit:cover;"/>'
            )
        initials = ((obj.first_name or '')[:1] + (obj.last_name or '')[:1]).upper() or '?'
        return mark_safe(
            f'<div style="width:48px;height:48px;border-radius:50%;background:#7900FF;'
            f'display:flex;align-items:center;justify-content:center;'
            f'color:white;font-weight:700;font-size:16px;">{initials}</div>'
        )
    photo_preview.short_description = 'Фото'

    def roles_badge(self, obj) -> str:
        badges = []
        if obj.is_passenger:
            badges.append('<span style="background:#198754;color:white;padding:3px 8px;'
                         'border-radius:8px;font-size:10px;font-weight:600;margin-right:4px;">П</span>')
        if obj.is_driver:
            badges.append('<span style="background:#7900FF;color:white;padding:3px 8px;'
                         'border-radius:8px;font-size:10px;font-weight:600;margin-right:4px;">В</span>')
        if obj.is_staff:
            badges.append('<span style="background:#dc3545;color:white;padding:3px 8px;'
                         'border-radius:8px;font-size:10px;font-weight:600;">А</span>')
        return mark_safe(' '.join(badges)) if badges else mark_safe('<span style="color:#6c757d;">—</span>')
    roles_badge.short_description = 'Ролі'

    def is_verified_badge(self, obj) -> str:
        if obj.is_verified:
            return mark_safe('<span style="color:#198754;font-weight:600;">✔ Підтверджено</span>')
        return mark_safe('<span style="color:#dc3545;font-weight:600;">✖ Не підтверджено</span>')
    is_verified_badge.short_description = 'Верифікація'

    def driver_profile_link(self, obj):
        try:
            driver = obj.driver_profile
            url = reverse('taxi_admin:drivers_driver_change', args=[driver.pk])
            return mark_safe(
                f'<a href="{url}" style="display:inline-block;background:#7900FF !important;'
                f'color:#ffffff !important;padding:5px 12px;'
                f'border-radius:8px;font-size:12px;font-weight:600;text-decoration:none !important;'
                f'line-height:1.4;white-space:nowrap;">Профіль водія →</a>'
            )
        except Exception:
            return '—'
    driver_profile_link.short_description = 'Водій'

    actions = ['verify_users', 'deactivate_users', 'activate_users']

    def verify_users(self, request, queryset):
        updated = queryset.update(is_verified=True)
        self.message_user(request, f'Підтверджено {updated} користувачів.')
    verify_users.short_description = 'Підтвердити вибраних'

    def deactivate_users(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'Деактивовано {updated} користувачів.')
    deactivate_users.short_description = 'Деактивувати вибраних'

    def activate_users(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'Активовано {updated} користувачів.')
    activate_users.short_description = 'Активувати вибраних'
