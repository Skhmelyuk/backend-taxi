from django.contrib import admin
from django.utils.html import format_html

from apps.drivers.models import Driver, DriverDocument
from core.admin_site import taxi_admin


class DriverDocumentInline(admin.TabularInline):
    model = DriverDocument
    extra = 0
    readonly_fields = ('uploaded_at', 'reviewed_at', 'preview', 'status_badge')
    fields = ('doc_type', 'status_badge', 'status', 'file', 'preview', 'notes', 'reviewer')
    
    def status_badge(self, obj):
        if not obj or not obj.status:
            return '-'
        colors = {
            'pending': '#f59e0b',
            'approved': '#10b981',
            'rejected': '#ef4444',
        }
        color = colors.get(obj.status, '#6b7280')
        label = dict(DriverDocument.VerificationStatus.choices).get(obj.status, obj.status)
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 8px; border-radius: 12px; font-weight: bold; font-size: 11px; white-space: nowrap;">{}</span>',
            color, label
        )
    status_badge.short_description = 'Статус'
    
    def preview(self, obj):
        if obj and obj.file:
            try:
                url = obj.file.url
                js_content = (
                    "if(!document.getElementById('img_modal')) {{"
                    "var m=document.createElement('div');m.id='img_modal';"
                    "m.style.cssText='display:none;position:fixed;z-index:9999;left:0;top:0;width:100%;height:100%;background:rgba(0,0,0,0.8);text-align:center;padding-top:3%;cursor:zoom-out;';"
                    "var i=document.createElement('img');i.id='img_modal_img';"
                    "i.style.cssText='max-height:90%;max-width:90%;border:4px solid white;border-radius:4px;box-shadow:0 0 20px rgba(0,0,0,0.8);';"
                    "m.appendChild(i);document.body.appendChild(m);"
                    "m.onclick=function(){{m.style.display='none';}};"
                    "}}"
                    "document.getElementById('img_modal_img').src=this.src;"
                    "document.getElementById('img_modal').style.display='block';"
                )
                return format_html(
                    '<img src="{}" style="max-height: 150px; border-radius: 4px; border: 1px solid #ccc; padding: 2px; cursor: zoom-in;" '
                    'onclick="{}" title="Відкрити на весь екран" />',
                    url, js_content.replace('{{', '{').replace('}}', '}')
                )
            except Exception:
                return '(помилка завантаження)'
        return '(немає файлу)'
    preview.short_description = 'Превʼю'

@admin.register(DriverDocument, site=taxi_admin)
class DriverDocumentAdmin(admin.ModelAdmin):
    """Admin configuration for Driver Documents."""
    list_display = (
        'id', 'driver_email', 'doc_type_label', 'status_badge', 
        'preview_thumbnail', 'uploaded_at', 'reviewer'
    )
    list_display_links = ('id', 'driver_email', 'doc_type_label')
    list_filter = ('status', 'doc_type', 'uploaded_at')
    search_fields = ('driver__user__email', 'notes')
    readonly_fields = ('uploaded_at', 'reviewed_at', 'preview')
    
    fieldsets = (
        ('Інформація про документ', {
            'fields': ('driver', 'doc_type', 'status', 'file', 'preview')
        }),
        ('Ревʼю', {
            'fields': ('notes', 'reviewer', 'reviewed_at')
        }),
        ('Службова інформація', {
            'fields': ('expires_at', 'uploaded_at')
        }),
    )

    def driver_email(self, obj):
        return obj.driver.user.email
    driver_email.short_description = 'Водій'

    def doc_type_label(self, obj):
        return dict(DriverDocument.DocumentType.choices).get(obj.doc_type, obj.doc_type)
    doc_type_label.short_description = 'Тип документу'

    def status_badge(self, obj):
        colors = {
            'pending': '#f59e0b',
            'approved': '#10b981',
            'rejected': '#ef4444',
        }
        color = colors.get(obj.status, '#6b7280')
        label = dict(DriverDocument.VerificationStatus.choices).get(obj.status, obj.status)
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 8px; border-radius: 12px; font-weight: bold; font-size: 11px;">{}</span>',
            color, label
        )
    status_badge.short_description = 'Статус'

    def preview_thumbnail(self, obj):
        if obj and obj.file:
            try:
                return format_html(
                    '<img src="{}" style="max-height: 40px; border-radius: 4px; border: 1px solid #ddd;" />',
                    obj.file.url
                )
            except Exception:
                return '-'
        return '-'
    preview_thumbnail.short_description = 'Файл'

    def preview(self, obj):
        return DriverDocumentInline.preview(self, obj)
    preview.short_description = 'Превʼю (клікніть для збільшення)'


@admin.register(Driver, site=taxi_admin)
class DriverAdmin(admin.ModelAdmin):
    """Admin configuration for Driver profiles."""

    inlines = [DriverDocumentInline]

    list_display = (
        'user_photo', 'user_email', 'status', 'availability', 'vehicle_plate', 'created_at',
    )
    list_filter = ('status', 'availability', 'vehicle_type', 'created_at')
    search_fields = (
        'user__email', 'user__first_name', 'user__last_name',
        'vehicle_plate', 'license_number',
    )
    readonly_fields = ('created_at', 'updated_at', 'user_photo')
    ordering = ('-created_at',)

    fieldsets = (
        ('Користувач', {
            'fields': ('user', 'user_photo', 'status', 'availability'),
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
        ('Аналітика', {
            'classes': ('collapse',),
            'fields': ('rating', 'total_rides', 'total_earnings'),
        }),
        ('Службова інформація', {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at'),
        }),
    )

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email'

    def user_photo(self, obj) -> str:
        if obj.user and obj.user.profile_image:
            return format_html(
                '<img src="{}" style="width: 40px; height: 40px; border-radius: 20px; '
                'border: 1px solid #ddd; object-fit: cover;" />',
                obj.user.profile_image
            )
        return format_html(
            '<div style="width: 40px; height: 40px; border-radius: 20px; background: #f8f9fa; '
            'display: flex; align-items: center; justify-content: center; border: 1px dashed #ced4da;">'
            '<span style="color: #adb5bd; font-size: 8px; text-align: center; line-height: 1.1;">Немає<br/>фото</span>'
            '</div>'
        )
    user_photo.short_description = 'Фото'



