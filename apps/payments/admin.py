from django.contrib import admin
from django.utils.html import mark_safe
from apps.payments.models import PromoCode, Refund
from core.admin_site import taxi_admin


@admin.register(PromoCode, site=taxi_admin)
class PromoCodeAdmin(admin.ModelAdmin):
    """Admin interface for PromoCode model."""
    list_display = [
        'code', 'discount_type', 'discount_badge', 'usage_progress',
        'active_badge', 'valid_until', 'created_at',
    ]
    list_filter = ['is_active', 'discount_type']
    search_fields = ['code']
    readonly_fields = ['usage_count', 'created_at']
    ordering = ['-created_at']

    actions = ['activate_codes', 'deactivate_codes']

    def discount_badge(self, obj):
        if obj.discount_type == 'percent':
            val = f'{obj.discount_percent}%'
            color = '#7900FF'
        else:
            val = f'{obj.discount_amount}₴'
            color = '#198754'
        return mark_safe(
            f'<span style="background:{color};color:white;padding:2px 10px;'
            f'border-radius:10px;font-size:12px;font-weight:700;">{val}</span>'
        )
    discount_badge.short_description = 'Знижка'

    def usage_progress(self, obj):
        limit = obj.usage_limit or 1
        count = obj.usage_count or 0
        pct = min(100, round(count / limit * 100)) if limit else 0
        color = '#198754' if pct < 80 else '#fd7e14' if pct < 100 else '#dc3545'
        return mark_safe(
            f'<div style="display:flex;align-items:center;gap:6px;">'
            f'<div style="width:80px;background:#f3f4f6;border-radius:4px;height:8px;">'
            f'<div style="width:{pct}%;background:{color};height:8px;border-radius:4px;"></div></div>'
            f'<span style="font-size:11px;color:#6b7280;">{count}/{obj.usage_limit or "∞"}</span></div>'
        )
    usage_progress.short_description = 'Використання'

    def active_badge(self, obj):
        if obj.is_active:
            return mark_safe('<span style="color:#198754;font-weight:700;">✔ Активний</span>')
        return mark_safe('<span style="color:#dc3545;font-weight:700;">✖ Неактивний</span>')
    active_badge.short_description = 'Статус'

    def activate_codes(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'Активовано {updated} промокодів.')
    activate_codes.short_description = 'Активувати вибрані'

    def deactivate_codes(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'Деактивовано {updated} промокодів.')
    deactivate_codes.short_description = 'Деактивувати вибрані'


@admin.register(Refund, site=taxi_admin)
class RefundAdmin(admin.ModelAdmin):
    list_display = ['id', 'payment', 'amount_display', 'status_badge', 'reason', 'created_at']
    list_filter = ['status']
    readonly_fields = ['id', 'payment', 'created_at', 'processed_at', 'provider_refund_id']
    ordering = ['-created_at']

    def amount_display(self, obj):
        return mark_safe(f'<strong>{obj.amount}₴</strong>')
    amount_display.short_description = 'Сума'

    def status_badge(self, obj):
        colors = {'pending': '#fd7e14', 'approved': '#198754', 'rejected': '#dc3545'}
        labels = {'pending': 'Очікує', 'approved': 'Схвалено', 'rejected': 'Відхилено'}
        color = colors.get(obj.status, '#6c757d')
        label = labels.get(obj.status, obj.status)
        return mark_safe(
            f'<span style="background:{color};color:white;padding:2px 8px;'
            f'border-radius:10px;font-size:11px;font-weight:600;">{label}</span>'
        )
    status_badge.short_description = 'Статус'