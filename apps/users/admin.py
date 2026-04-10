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
        'photo_preview', 'email', 'full_name', 'role_badge', 'is_verified_badge',
        'is_active', 'driver_profile_link', 'created_at',
    ]
    list_filter = ['role', 'is_active', 'is_verified', 'is_staff', 'created_at']
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
        ('Роль та дозволи', {
            'fields': ('role', 'is_active', 'is_verified', 'is_staff', 'is_superuser',
                       'groups', 'user_permissions')
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
            'fields': ('email', 'password1', 'password2', 'role'),
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

    def role_badge(self, obj) -> str:
        config = {
            'admin': ('#dc3545', 'Адмін'),
            'driver': ('#7900FF', 'Водій'),
            'user': ('#198754', 'Пасажир'),
        }
        color, label = config.get(obj.role, ('#6c757d', obj.role))
        return mark_safe(
            f'<span style="background:{color};color:white;padding:3px 10px;'
            f'border-radius:12px;font-size:11px;font-weight:600;white-space:nowrap;">{label}</span>'
        )
    role_badge.short_description = 'Роль'

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
