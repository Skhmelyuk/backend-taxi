from django.contrib import admin
from django.utils.html import format_html
from apps.rides.models import Ride
from core.admin_site import taxi_admin


@admin.register(Ride, site=taxi_admin)
class RideAdmin(admin.ModelAdmin):
    """Admin for Ride model with status badges and state machine validation"""
    list_display = [
        'id_short', 'user_email', 'driver_email', 'status_badge',
        'vehicle_type', 'estimated_price', 'final_price', 'rating', 'created_at',
    ]
    list_filter = ['status', 'vehicle_type', 'created_at']
    search_fields = ['user__email', 'driver__user__email', 'pickup_address', 'dropoff_address']
    ordering = ['-created_at']
    readonly_fields = [
        'id', 'user', 'driver', 'pickup_location', 'dropoff_location',
        'created_at', 'accepted_at', 'started_at', 'completed_at', 'cancelled_at', 'updated_at',
    ]

    fieldsets = (
        ('Basic', {'fields': ('id', 'user', 'driver', 'status', 'vehicle_type')}),
        ('Locations', {'fields': (
            'pickup_location', 'pickup_address', 'dropoff_location', 'dropoff_address'
        )}),
        ('Pricing', {'fields': (
            'estimated_distance', 'estimated_duration', 'estimated_price',
            'final_distance', 'final_duration', 'final_price', 'discount',
        )}),
        ('Rating', {'fields': ('rating', 'user_comment')}),
        ('Cancellation', {'fields': ('cancellation_reason', 'cancellation_comment')}),
        ('Timestamps', {'fields': (
            'created_at', 'accepted_at', 'started_at', 'completed_at', 'cancelled_at',
        ), 'classes': ('collapse',)}),
    )

    def id_short(self, obj):
        return str(obj.id)[:8] + '...'
    id_short.short_description = 'ID'

    def user_email(self, obj): return obj.user.email
    user_email.short_description = 'User'

    def driver_email(self, obj):
        return obj.driver.user.email if obj.driver else '—'
    driver_email.short_description = 'Driver'

    def status_badge(self, obj):
        colors = {
            'pending': '#fd7e14', 'accepted': '#0d6efd', 'in_progress': '#6610f2',
            'completed': '#198754', 'cancelled': '#dc3545',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background:{};color:white;padding:2px 8px;border-radius:12px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'