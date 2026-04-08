from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
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
        'photo_preview', 'email', 'full_name', 'role_badge', 'is_verified_badge', 'is_active', 'created_at',
    ]
    list_filter = ['role', 'is_active', 'is_verified', 'is_staff', 'created_at']
    search_fields = ['email', 'first_name', 'last_name', 'phone_number', 'clerk_user_id']
    ordering = ['-created_at']
    readonly_fields = ['id', 'clerk_user_id', 'created_at', 'updated_at', 'last_login', 'photo_preview']

    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'email', 'first_name', 'last_name', 'phone_number', 'photo_preview', 'profile_image', 'date_of_birth')
        }),
        ('Clerk Integration', {
            'fields': ('clerk_user_id',)
        }),
        ('Role & Permissions', {
            'fields': ('role', 'is_active', 'is_verified', 'is_staff', 'is_superuser',
                       'groups', 'user_permissions')
        }),
        ('Notifications', {
            'fields': ('fcm_token',),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
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
        return obj.full_name
    full_name.short_description = 'Full Name'

    def photo_preview(self, obj) -> str:
        if obj.profile_image:
            return format_html(
                '<img src="{}" style="width: 40px; height: 40px; border-radius: 20px; '
                'border: 1px solid #ddd; object-fit: cover;" />',
                obj.profile_image
            )
        return format_html(
            '<div style="width: 40px; height: 40px; border-radius: 20px; background: #f0f0f0; '
            'display: flex; align-items: center; justify-content: center; border: 1px dashed #ccc;">'
            '<span style="color: #999; font-size: 8px; text-align: center; line-height: 1.1;">Фото<br/>відсутнє</span>'
            '</div>'
        )
    photo_preview.short_description = 'Фото'

    def role_badge(self, obj) -> str:
        colors = {'admin': '#dc3545', 'driver': '#0d6efd', 'user': '#198754'}
        color = colors.get(obj.role, '#6c757d')
        return format_html(
            '<span style="background:{};color:white;padding:2px 8px;border-radius:12px;">{}</span>',
            color, obj.get_role_display()
        )
    role_badge.short_description = 'Role'
    role_badge.allow_tags = True

    def is_verified_badge(self, obj) -> str:
        if obj.is_verified:
            return format_html('<span style="color:#198754;">{}</span>', '✓ Verified')
        return format_html('<span style="color:#dc3545;">{}</span>', '✗ Unverified')
    is_verified_badge.short_description = 'Verified'

    actions = ['verify_users', 'deactivate_users', 'activate_users']

    def verify_users(self, request, queryset):
        queryset.update(is_verified=True)
        self.message_user(request, f'{queryset.count()} users verified.')
    verify_users.short_description = 'Mark selected users as verified'

    def deactivate_users(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f'{queryset.count()} users deactivated.')
    deactivate_users.short_description = 'Deactivate selected users'

    def activate_users(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f'{queryset.count()} users activated.')
    activate_users.short_description = 'Activate selected users'
