from django.contrib import admin
from apps.payments.models import PromoCode, Refund
from core.admin_site import taxi_admin



@admin.register(PromoCode, site=taxi_admin)
class PromoCodeAdmin(admin.ModelAdmin):
    """Admin interface for PromoCode model."""
    list_display = [
        'code', 'discount_type', 'discount_percent', 'discount_amount',
        'usage_count', 'usage_limit', 'is_active', 'valid_until',
    ]
    list_filter = ['is_active', 'discount_type']
    search_fields = ['code']
    readonly_fields = ['usage_count', 'created_at']

    actions = ['activate_codes', 'deactivate_codes']

    def activate_codes(self, request, queryset):
        queryset.update(is_active=True)
    activate_codes.short_description = 'Activate selected promo codes'

    def deactivate_codes(self, request, queryset):
        queryset.update(is_active=False)
    deactivate_codes.short_description = 'Deactivate selected promo codes'


@admin.register(Refund, site=taxi_admin)
class RefundAdmin(admin.ModelAdmin):
    list_display = ['id', 'payment', 'amount', 'status', 'reason', 'created_at']
    list_filter = ['status']
    readonly_fields = ['id', 'payment', 'created_at', 'processed_at', 'provider_refund_id']