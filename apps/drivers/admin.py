from django import forms
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html, mark_safe

from apps.drivers.models import Driver, DriverDocument
from core.admin_site import taxi_admin


class RideInline(admin.TabularInline):
    """Last 20 rides for a driver, shown inline in DriverAdmin."""
    from apps.rides.models import Ride as _Ride
    model = _Ride
    fk_name = 'driver'
    extra = 0
    max_num = 0
    can_delete = False
    verbose_name = 'Поїздка'
    verbose_name_plural = 'Останні поїздки'
    ordering = ('-created_at',)
    fields = ('status_badge', 'passenger_email', 'pickup_address', 'dropoff_address',
              'final_price', 'rating', 'created_at', 'edit_link')
    readonly_fields = ('status_badge', 'passenger_email', 'pickup_address', 'dropoff_address',
                       'final_price', 'rating', 'created_at', 'edit_link')
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user').order_by('-created_at')

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        if obj is not None:
            from apps.rides.models import Ride as _R
            ids = list(
                _R.objects.filter(driver=obj)
                .order_by('-created_at')
                .values_list('pk', flat=True)[:20]
            )
            original_init = formset.__init__

            def patched_init(self_fs, *a, **kw):
                original_init(self_fs, *a, **kw)
                self_fs.queryset = self_fs.queryset.filter(pk__in=ids)

            formset.__init__ = patched_init
        return formset

    def has_add_permission(self, request, obj=None):
        return False

    def edit_link(self, obj):
        if not obj.pk:
            return '—'
        url = reverse('taxi_admin:rides_ride_change', args=[obj.pk])
        return mark_safe(
            f'<a href="{url}" style="display:inline-flex;align-items:center;gap:4px;'
            f'background:#ede9fe;color:#7900FF;border:1px solid #c4b5fd;'
            f'border-radius:6px;padding:4px 10px;font-size:11px;font-weight:600;'
            f'text-decoration:none;white-space:nowrap;'
            f'transition:background 0.12s,color 0.12s;"'
            f'onmouseover="this.style.background=\'#7900FF\';this.style.color=\'#fff\'"'
            f'onmouseout="this.style.background=\'#ede9fe\';this.style.color=\'#7900FF\'"'
            f'>✏️ Редагувати</a>'
        )
    edit_link.short_description = ''

    def passenger_email(self, obj):
        return obj.user.email if obj.user else '—'
    passenger_email.short_description = 'Пасажир'

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
            f'<span style="background:{color};color:white;padding:2px 8px;'
            f'border-radius:10px;font-size:11px;white-space:nowrap;">{label}</span>'
        )
    status_badge.short_description = 'Статус'


class DriverDocumentInline(admin.TabularInline):
    model = DriverDocument
    extra = 0
    verbose_name = 'Документ'
    verbose_name_plural = 'Документи водія'
    readonly_fields = ('doc_preview',)
    fields = ('doc_preview', 'doc_type', 'status', 'notes', 'reviewer', 'expires_at')
    can_delete = True

    SELECT_STYLE = (
        'height:36px;border-radius:8px;border:1px solid #e5e7eb;'
        'padding:4px 10px;font-size:12px;background:#fff;cursor:pointer;'
    )

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name in ('doc_type', 'status'):
            field = super().formfield_for_dbfield(db_field, request, **kwargs)
            field.widget.attrs.update({'style': self.SELECT_STYLE})
            return field
        if db_field.name == 'notes':
            kwargs['widget'] = forms.Textarea(attrs={
                'rows': 2,
                'style': 'width:180px;border-radius:6px;border:1px solid #e5e7eb;padding:5px 8px;font-size:12px;',
            })
        if db_field.name == 'expires_at':
            field = super().formfield_for_dbfield(db_field, request, **kwargs)
            field.widget.attrs.update({'style': 'border-radius:8px;border:1px solid #e5e7eb;padding:4px 8px;font-size:12px;'})
            return field
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'reviewer':
            from apps.users.models import User
            kwargs['queryset'] = User.objects.filter(is_staff=True).order_by('email')
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name == 'reviewer':
            field.widget.attrs.update({'style': self.SELECT_STYLE})
        return field

    def doc_preview(self, obj):
        if not obj.pk or not obj.file:
            return mark_safe('<div style="width:80px;height:80px;border-radius:8px;background:#f3f4f6;'
                             'display:flex;align-items:center;justify-content:center;'
                             'color:#9ca3af;font-size:22px;">📄</div>')
        try:
            url = obj.file.url
            STATUS_CFG = {
                'pending':  ('#f59e0b', '#fde68a'),
                'approved': ('#10b981', '#bbf7d0'),
                'rejected': ('#ef4444', '#fecaca'),
            }
            clr, border = STATUS_CFG.get(obj.status, ('#6b7280', '#e5e7eb'))
            js = (
                "if(!document.getElementById('img_modal')){"
                "var m=document.createElement('div');m.id='img_modal';"
                "m.style.cssText='display:none;position:fixed;z-index:9999;left:0;top:0;"
                "width:100%;height:100%;background:rgba(0,0,0,0.85);cursor:zoom-out;"
                "align-items:center;justify-content:center;';"
                "var i=document.createElement('img');i.id='img_modal_img';"
                "i.style.cssText='max-height:90vh;max-width:90vw;border-radius:8px;"
                "box-shadow:0 20px 60px rgba(0,0,0,0.5);';"
                "m.appendChild(i);document.body.appendChild(m);"
                "m.onclick=function(){m.style.display='none';};"
                "}"
                "document.getElementById('img_modal_img').src=this.src;"
                "document.getElementById('img_modal').style.display='flex';"
            )
            return mark_safe(
                f'<img src="{url}" '
                f'style="width:80px;height:80px;object-fit:cover;border-radius:8px;'
                f'border:3px solid {border};cursor:zoom-in;transition:transform 0.15s;'
                f'box-shadow:0 2px 8px rgba(0,0,0,0.12);" '
                f'onmouseover="this.style.transform=\'scale(1.08)\'" '
                f'onmouseout="this.style.transform=\'scale(1)\'" '
                f'onclick="{js}" title="Натисніть для збільшення" />'
            )
        except Exception:
            return '—'
    doc_preview.short_description = 'Фото'

class DriverDocumentAdmin(admin.ModelAdmin):
    """Admin configuration for Driver Documents."""
    class Meta:
        verbose_name = 'Документ водія'
        verbose_name_plural = 'Документи водія'
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

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == 'file':
            # Use FileInput instead of ClearableFileInput to hide the "Currently:" link
            kwargs['widget'] = forms.FileInput
        if db_field.name == 'notes':
            # Reduce width of the notes field to save space
            kwargs['widget'] = forms.Textarea(attrs={'rows': 3, 'style': 'width: 400px;'})
        return super().formfield_for_dbfield(db_field, request, **kwargs)


@admin.register(Driver, site=taxi_admin)
class DriverAdmin(admin.ModelAdmin):
    """Admin configuration for Driver profiles."""

    inlines = [DriverDocumentInline, RideInline]

    list_display = (
        'user_photo', 'driver_name_link', 'user_email', 'vehicle_info',
        'status_badge', 'availability_badge', 'rating_stars', 'total_rides', 'created_at',
    )
    list_filter = ('status', 'availability', 'vehicle_type', 'created_at')
    search_fields = (
        'user__email', 'user__first_name', 'user__last_name',
        'vehicle_plate', 'license_number',
    )
    readonly_fields = (
        'created_at', 'updated_at', 'user_photo', 'status_badge',
        'availability_badge', 'rating_stars', 'stats_panel', 'driver_rides_link',
    )
    ordering = ('-created_at',)

    fieldsets = (
        ('Користувач', {
            'fields': ('user', 'user_photo', 'first_name', 'last_name', 'status', 'availability'),
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
        ('Статистика', {
            'fields': ('stats_panel', 'driver_rides_link'),
        }),
        ('Службова інформація', {
            'classes': ('collapse',),
            'fields': ('rating', 'total_rides', 'total_earnings', 'created_at', 'updated_at'),
        }),
    )

    actions = ['approve_drivers', 'suspend_drivers', 'set_online', 'set_offline']

    def approve_drivers(self, request, queryset):
        updated = queryset.update(status='approved')
        self.message_user(request, f'Схвалено {updated} водіїв.')
    approve_drivers.short_description = 'Схвалити вибраних'

    def suspend_drivers(self, request, queryset):
        updated = queryset.update(status='suspended')
        self.message_user(request, f'Заблоковано {updated} водіїв.')
    suspend_drivers.short_description = 'Заблокувати вибраних'

    def set_online(self, request, queryset):
        updated = queryset.filter(status='approved').update(availability='online')
        self.message_user(request, f'{updated} водіїв переключено в Online.')
    set_online.short_description = 'Переключити в Online'

    def set_offline(self, request, queryset):
        updated = queryset.update(availability='offline')
        self.message_user(request, f'{updated} водіїв переключено в Offline.')
    set_offline.short_description = 'Переключити в Offline'

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email'

    def driver_name_link(self, obj):
        url = reverse('taxi_admin:drivers_driver_change', args=[obj.pk])
        full = f'{obj.user.last_name} {obj.user.first_name}'.strip() or obj.user.email
        return mark_safe(f'<a href="{url}" style="font-weight:600;color:#7900FF;">{full}</a>')
    driver_name_link.short_description = "Ім'я"

    def vehicle_info(self, obj):
        parts = filter(None, [obj.vehicle_make, obj.vehicle_model, str(obj.vehicle_year or '')])
        line1 = ' '.join(parts)
        plate = obj.vehicle_plate or ''
        return mark_safe(
            f'<span style="font-weight:600;">{line1}</span><br/>'
            f'<span style="font-size:11px;color:#6b7280;letter-spacing:1px;">{plate}</span>'
        )
    vehicle_info.short_description = 'Автомобіль'

    def user_photo(self, obj) -> str:
        if obj.user and obj.user.profile_image:
            return mark_safe(
                f'<img src="{obj.user.profile_image}" style="width:48px;height:48px;border-radius:50%;'
                f'border:3px solid #7900FF;object-fit:cover;"/>'
            )
        initials = (
            (obj.user.first_name or '')[:1] + (obj.user.last_name or '')[:1]
        ).upper() or '⁠?'
        return mark_safe(
            f'<div style="width:48px;height:48px;border-radius:50%;background:#7900FF;'
            f'display:flex;align-items:center;justify-content:center;'
            f'color:white;font-weight:700;font-size:17px;">{initials}</div>'
        )
    user_photo.short_description = 'Фото'

    def status_badge(self, obj):
        config = {
            'approved': ('#10b981', 'Схвалено'),
            'pending':  ('#f59e0b', 'Очікує'),
            'rejected': ('#ef4444', 'Відхилено'),
            'suspended': ('#374151', 'Заблоковано'),
        }
        color, label = config.get(obj.status, ('#6b7280', obj.status))
        return mark_safe(
            f'<span style="background:{color};color:white;padding:4px 10px;'
            f'border-radius:12px;font-weight:700;font-size:11px;white-space:nowrap;">{label}</span>'
        )
    status_badge.short_description = 'Статус'

    def availability_badge(self, obj):
        config = {
            'online':  ('#10b981', '● Online'),
            'offline': ('#9ca3af', '○ Offline'),
            'busy':    ('#f59e0b', '● Зайнятий'),
        }
        if not obj.availability:
            return '—'
        color, label = config.get(obj.availability, ('#6b7280', obj.availability))
        return mark_safe(
            f'<span style="color:{color};font-weight:700;font-size:12px;white-space:nowrap;">{label}</span>'
        )
    availability_badge.short_description = 'Доступність'

    def rating_stars(self, obj):
        if not obj.rating:
            return '—'
        rating = float(obj.rating)
        full = int(rating)
        empty = 5 - full
        stars = '★' * full + '☆' * empty
        return mark_safe(
            f'<span style="color:#f59e0b;font-size:15px;letter-spacing:1px;">{stars}</span> '
            f'<span style="color:#374151;font-weight:700;">{rating:.2f}</span>'
        )
    rating_stars.short_description = 'Рейтинг'

    def stats_panel(self, obj):
        from datetime import date
        from django.db.models import Avg
        from apps.rides.models import Ride

        # ── Data ─────────────────────────────────────────────────────────────
        all_rides   = Ride.objects.filter(driver=obj)
        completed   = all_rides.filter(status=Ride.Status.COMPLETED)
        completed_count  = completed.count()
        cancelled_count  = all_rides.filter(status=Ride.Status.CANCELLED).count()
        total_count      = all_rides.count()
        accepted_rides   = all_rides.filter(accepted_at__isnull=False)
        total_accepted   = accepted_rides.count()

        on_time_count = sum(
            1 for r in accepted_rides
            if (r.accepted_at - r.created_at).total_seconds() <= 180
        ) if total_accepted else 0
        on_time_pct    = round(on_time_count / total_accepted * 100) if total_accepted else 0
        completion_pct = round(completed_count / total_accepted * 100) if total_accepted else 0
        avg_r          = completed.filter(rating__isnull=False).aggregate(avg=Avg('rating'))['avg']
        safe_pct       = round((float(avg_r) - 1) / 4 * 100) if avg_r else 0
        avg_r_str      = f'{float(avg_r):.1f}' if avg_r else '—'

        # ── Monthly chart (last 5 months) ─────────────────────────────────────
        MONTH_UA = {1:'Січ',2:'Лют',3:'Бер',4:'Кві',5:'Тра',6:'Чер',
                    7:'Лип',8:'Сер',9:'Вер',10:'Жов',11:'Лис',12:'Гру'}
        today = date.today()
        months_data = []
        for i in range(4, -1, -1):
            mo = (today.month - i - 1) % 12 + 1
            yr = today.year + ((today.month - i - 1) // 12)
            ms = date(yr, mo, 1)
            me = date(yr + 1, 1, 1) if mo == 12 else date(yr, mo + 1, 1)
            cnt = completed.filter(completed_at__date__gte=ms, completed_at__date__lt=me).count()
            months_data.append((MONTH_UA[mo], cnt))
        max_cnt = max((c for _, c in months_data), default=1) or 1

        # ── Helpers ───────────────────────────────────────────────────────────
        S = 'style='
        def card(content, extra=''):
            return (f'<div {S}"background:#fff;border:1px solid #ede9fe;border-radius:14px;'
                    f'padding:16px 18px;box-shadow:0 1px 4px rgba(121,0,255,0.07);{extra}">'
                    f'{content}</div>')

        def ring_bar(pct, color, gradient_end):
            filled = pct
            empty  = 100 - pct
            return (
                f'<div {S}"position:relative;display:inline-flex;align-items:center;'
                f'justify-content:center;width:80px;height:80px;">'
                f'<svg width="80" height="80" viewBox="0 0 80 80">'
                f'<circle cx="40" cy="40" r="32" fill="none" stroke="#f3f0ff" stroke-width="8"/>'
                f'<circle cx="40" cy="40" r="32" fill="none" stroke="{color}" stroke-width="8" '
                f'stroke-dasharray="{filled*2.01:.1f} {empty*2.01:.1f}" '
                f'stroke-dashoffset="50.3" stroke-linecap="round" transform="rotate(-90 40 40)"/>'
                f'</svg>'
                f'<span {S}"position:absolute;font-size:15px;font-weight:800;color:#1f2937;">'
                f'{pct}%</span>'
                f'</div>'
            )

        def stat_pill(icon, label, val, color, bg):
            return (
                f'<div {S}"display:flex;align-items:center;gap:10px;background:{bg};'
                f'border-radius:12px;padding:12px 16px;">'
                f'<div {S}"width:40px;height:40px;border-radius:10px;background:{color}20;'
                f'display:flex;align-items:center;justify-content:center;font-size:18px;">{icon}</div>'
                f'<div>'
                f'<div {S}"font-size:18px;font-weight:800;color:{color};">{val}</div>'
                f'<div {S}"font-size:11px;color:#6b7280;margin-top:1px;">{label}</div>'
                f'</div></div>'
            )

        # ── Section 1: Performance rings ──────────────────────────────────────
        rings_html = ''
        for label, pct, color, icon in [
            ('Вчасне прийняття', on_time_pct,    '#10b981', '⏱'),
            ('Виконання поїздок', completion_pct, '#7900FF', '✓'),
            ('Рейтинг маршруту',  safe_pct,       '#f59e0b', '★'),
        ]:
            rings_html += (
                f'<div {S}"display:flex;flex-direction:column;align-items:center;gap:8px;">'
                f'{ring_bar(pct, color, color)}'
                f'<div {S}"text-align:center;">'
                f'<div {S}"font-size:11px;color:#6b7280;font-weight:500;">{label}</div>'
                f'</div></div>'
            )
        section1 = card(
            f'<div {S}"font-size:12px;font-weight:700;color:#5A00CC;text-transform:uppercase;'
            f'letter-spacing:0.8px;margin-bottom:14px;">📊 Показники ефективності</div>'
            f'<div {S}"display:grid;grid-template-columns:repeat(3,1fr);gap:12px;">'
            f'{rings_html}</div>',
        )

        # ── Section 2: Summary pills ──────────────────────────────────────────
        pills_html = ''
        for icon, label, val, color, bg in [
            ('🚗', 'Всього поїздок',   total_count,     '#1f2937', '#f9fafb'),
            ('✅', 'Завершено',         completed_count,  '#10b981', '#f0fdf4'),
            ('❌', 'Скасовано',         cancelled_count,  '#ef4444', '#fef2f2'),
            ('⭐', 'Середній рейтинг', avg_r_str,        '#f59e0b', '#fffbeb'),
        ]:
            pills_html += stat_pill(icon, label, val, color, bg)

        section2 = card(
            f'<div {S}"font-size:12px;font-weight:700;color:#5A00CC;text-transform:uppercase;'
            f'letter-spacing:0.8px;margin-bottom:14px;">📋 Підсумок</div>'
            f'<div {S}"display:grid;grid-template-columns:1fr 1fr;gap:10px;">{pills_html}</div>',
        )

        # ── Section 3: Bar chart ──────────────────────────────────────────────
        bars = ''
        for label, cnt in months_data:
            h   = max(6, round(cnt / max_cnt * 90))
            pct = round(cnt / max_cnt * 100) if max_cnt else 0
            clr = '#7900FF' if pct >= 70 else '#a855f7' if pct >= 30 else '#d8b4fe'
            bars += (
                f'<div {S}"flex:1;display:flex;flex-direction:column;align-items:center;gap:4px;">'
                f'<span {S}"font-size:11px;font-weight:700;color:#374151;">{cnt}</span>'
                f'<div {S}"width:100%;height:{h}px;background:{clr};border-radius:6px 6px 0 0;'
                f'transition:height 0.3s;"></div>'
                f'<span {S}"font-size:11px;color:#9ca3af;font-weight:500;">{label}</span>'
                f'</div>'
            )

        section3 = card(
            f'<div {S}"font-size:12px;font-weight:700;color:#5A00CC;text-transform:uppercase;'
            f'letter-spacing:0.8px;margin-bottom:16px;">📅 Поїздки за останні 5 місяців</div>'
            f'<div {S}"display:flex;align-items:flex-end;gap:8px;height:110px;'
            f'border-bottom:2px solid #ede9fe;padding-bottom:0;">{bars}</div>',
        )

        return mark_safe(
            f'<div {S}"font-family:Inter,system-ui,sans-serif;">'
            f'<div {S}"display:grid;grid-template-columns:1fr 1fr 1.3fr;gap:12px;align-items:start;">'
            f'{section1}{section2}{section3}'
            f'</div>'
            f'</div>'
        )
    stats_panel.short_description = 'Аналітика водія'

    def driver_rides_link(self, obj):
        if not obj.pk:
            return '—'
        url = reverse('taxi_admin:rides_ride_changelist') + f'?driver__id__exact={obj.pk}'
        count = obj.rides.count()
        return mark_safe(
            f'<a href="{url}" style="display:inline-block;background:#7900FF;color:white;'
            f'padding:6px 14px;border-radius:8px;font-size:13px;font-weight:600;text-decoration:none;">'
            f'Переглянути всі {count} поїздок →</a>'
        )
    driver_rides_link.short_description = 'Всі поїздки'



