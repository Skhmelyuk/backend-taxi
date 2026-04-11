from django import forms
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html, mark_safe

from apps.drivers.models import Driver, DriverDocument, WithdrawalRequest
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
        ('Виплати', {
            'fields': (
                'payout_card_number',
                'pending_card_withdrawal',
                'cash_earnings',
                'card_earnings',
                'total_earnings',
            ),
        }),
        ('Службова інформація', {
            'classes': ('collapse',),
            'fields': ('rating', 'total_rides', 'created_at', 'updated_at'),
        }),
    )

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        field = super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.name == 'vehicle_year':
            field.widget.attrs.update({'style': 'width:90px;'})
        return field

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

        # ── Section 3: Bar chart (rides) ─────────────────────────────────────
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

        # ── Section 4: Earnings ───────────────────────────────────────────────
        from django.db.models import Sum
        from apps.payments.models import Payment

        total_e   = float(obj.total_earnings or 0)
        cash_e    = float(obj.cash_earnings or 0)
        card_e    = float(obj.card_earnings or 0)
        pending_w = float(obj.pending_card_withdrawal or 0)

        cash_pct = round(cash_e / total_e * 100) if total_e else 0
        card_pct = 100 - cash_pct if total_e else 0

        # Monthly earnings (last 5 months)
        earn_months = []
        for i in range(4, -1, -1):
            mo = (today.month - i - 1) % 12 + 1
            yr = today.year + ((today.month - i - 1) // 12)
            ms = date(yr, mo, 1)
            me = date(yr + 1, 1, 1) if mo == 12 else date(yr, mo + 1, 1)
            earn = Payment.objects.filter(
                ride__driver=obj, status='success',
                processed_at__date__gte=ms, processed_at__date__lt=me,
            ).aggregate(t=Sum('amount'))['t'] or 0
            earn_months.append((MONTH_UA[mo], float(earn)))

        max_earn = max((e for _, e in earn_months), default=1) or 1

        earn_bars = ''
        for label, earn in earn_months:
            h   = max(6, round(earn / max_earn * 90))
            pct = round(earn / max_earn * 100) if max_earn else 0
            clr = '#10b981' if pct >= 70 else '#34d399' if pct >= 30 else '#a7f3d0'
            earn_bars += (
                f'<div {S}"flex:1;display:flex;flex-direction:column;align-items:center;gap:4px;">'
                f'<span {S}"font-size:10px;font-weight:700;color:#374151;">{int(earn):,}₴</span>'
                f'<div {S}"width:100%;height:{h}px;background:{clr};border-radius:6px 6px 0 0;"></div>'
                f'<span {S}"font-size:11px;color:#9ca3af;font-weight:500;">{label}</span>'
                f'</div>'
            )

        def earn_row(label, val, color):
            return (
                f'<div {S}"display:flex;justify-content:space-between;align-items:center;'
                f'padding:6px 0;border-bottom:1px solid #f3f4f6;">'
                f'<span {S}"font-size:12px;color:#6b7280;">{label}</span>'
                f'<span {S}"font-size:14px;font-weight:700;color:{color};">{val:,.0f} ₴</span>'
                f'</div>'
            )

        bar_w_cash = f'{cash_pct}%'
        bar_w_card = f'{card_pct}%'

        split_bar = (
            f'<div {S}"display:flex;border-radius:8px;overflow:hidden;height:10px;margin:12px 0 4px;">'
            f'<div {S}"width:{bar_w_cash};background:#22c55e;" title="Готівка {cash_pct}%"></div>'
            f'<div {S}"width:{bar_w_card};background:#7900FF;" title="Картка {card_pct}%"></div>'
            f'</div>'
            f'<div {S}"display:flex;gap:14px;margin-bottom:10px;">'
            f'<span {S}"font-size:11px;color:#22c55e;font-weight:600;">● Готівка {cash_pct}%</span>'
            f'<span {S}"font-size:11px;color:#7900FF;font-weight:600;">● Картка {card_pct}%</span>'
            f'</div>'
        )

        from apps.drivers.models import WithdrawalRequest as _WR
        card_paid_out = float(_WR.objects.filter(
            driver=obj, status=_WR.Status.COMPLETED
        ).aggregate(t=Sum('amount'))['t'] or 0)
        card_remaining = card_e - card_paid_out  # what's left incl. pending_w

        earn_summary = (
            earn_row('Загальний заробіток', total_e, '#1f2937') +
            earn_row('Готівка', cash_e, '#22c55e') +
            earn_row('Картка (всього)', card_e, '#7900FF')
        )

        card_breakdown = (
            f'<div {S}"margin-top:10px;background:#f5f3ff;border:1px solid #ede9fe;'
            f'border-radius:10px;padding:10px 14px;">'
            f'<div {S}"font-size:10px;font-weight:700;color:#5A00CC;text-transform:uppercase;'
            f'letter-spacing:0.5px;margin-bottom:8px;">💳 Розбивка картки</div>'
            f'<div {S}"display:flex;justify-content:space-between;padding:4px 0;'
            f'border-bottom:1px solid #ede9fe;">'
            f'<span {S}"font-size:12px;color:#6b7280;">Зароблено карткою</span>'
            f'<span {S}"font-size:13px;font-weight:700;color:#7900FF;">{card_e:,.0f} ₴</span>'
            f'</div>'
            f'<div {S}"display:flex;justify-content:space-between;padding:4px 0;'
            f'border-bottom:1px solid #ede9fe;">'
            f'<span {S}"font-size:12px;color:#6b7280;">Виплачено</span>'
            f'<span {S}"font-size:13px;font-weight:700;color:#10b981;">− {card_paid_out:,.0f} ₴</span>'
            f'</div>'
            f'<div {S}"display:flex;justify-content:space-between;padding:6px 0 0;">'
            f'<span {S}"font-size:12px;font-weight:700;color:#1f2937;">Залишок (не виплачено)</span>'
            f'<span {S}"font-size:15px;font-weight:800;color:#d97706;">{card_remaining:,.0f} ₴</span>'
            f'</div>'
            f'</div>'
        )

        pending_html = ''
        if pending_w > 0:
            pending_html = (
                f'<div {S}"display:flex;justify-content:space-between;align-items:center;'
                f'margin-top:8px;background:#fffbeb;border:1px solid #fde68a;'
                f'border-radius:10px;padding:8px 12px;">'
                f'<span {S}"font-size:12px;color:#d97706;font-weight:600;">⏳ Доступно до виведення</span>'
                f'<span {S}"font-size:14px;font-weight:800;color:#d97706;">{pending_w:,.0f} ₴</span>'
                f'</div>'
            )

        section4_left = card(
            f'<div {S}"font-size:12px;font-weight:700;color:#5A00CC;text-transform:uppercase;'
            f'letter-spacing:0.8px;margin-bottom:12px;">💰 Заробіток</div>'
            f'{earn_summary}'
            f'{split_bar}'
            f'{card_breakdown}'
            f'{pending_html}',
        )

        section4_right = card(
            f'<div {S}"font-size:12px;font-weight:700;color:#5A00CC;text-transform:uppercase;'
            f'letter-spacing:0.8px;margin-bottom:16px;">📈 Заробіток за місяцями</div>'
            f'<div {S}"display:flex;align-items:flex-end;gap:8px;height:110px;'
            f'border-bottom:2px solid #dcfce7;padding-bottom:0;">{earn_bars}</div>',
        )

        # ── Section 5: Withdrawal statistics ──────────────────────────────────
        from apps.drivers.models import WithdrawalRequest as WR

        wrs = WR.objects.filter(driver=obj)
        wr_total      = wrs.count()
        wr_pending    = wrs.filter(status=WR.Status.PENDING).count()
        wr_approved   = wrs.filter(status=WR.Status.APPROVED).count()
        wr_completed  = wrs.filter(status=WR.Status.COMPLETED).count()
        wr_rejected   = wrs.filter(status=WR.Status.REJECTED).count()
        wr_paid_sum   = float(wrs.filter(status=WR.Status.COMPLETED).aggregate(
            t=Sum('amount'))['t'] or 0)
        payout_card   = obj.payout_card_number or None
        pending_now   = float(obj.pending_card_withdrawal or 0)

        def wr_pill(icon, label, val, color, bg):
            return (
                f'<div {S}"display:flex;align-items:center;gap:10px;background:{bg};'
                f'border-radius:12px;padding:10px 14px;">'
                f'<span {S}"font-size:20px;">{icon}</span>'
                f'<div>'
                f'<div {S}"font-size:18px;font-weight:800;color:{color};">{val}</div>'
                f'<div {S}"font-size:11px;color:#6b7280;margin-top:1px;">{label}</div>'
                f'</div></div>'
            )

        card_block = ''
        if payout_card:
            url_list = reverse('taxi_admin:drivers_withdrawalrequest_changelist') + f'?driver__id__exact={obj.pk}'
            card_block = (
                f'<div {S}"background:#f5f3ff;border:1px solid #ede9fe;border-radius:10px;'
                f'padding:12px 16px;margin-top:12px;">'
                f'<div {S}"font-size:10px;font-weight:700;color:#6b7280;text-transform:uppercase;'
                f'letter-spacing:0.5px;margin-bottom:6px;">💳 Картка виплати</div>'
                f'<div {S}"font-size:20px;font-weight:800;color:#7900FF;letter-spacing:2px;margin-bottom:8px;">'
                f'{payout_card}</div>'
                f'<a href="{url_list}" {S}"font-size:12px;color:#7900FF;font-weight:600;">'
                f'Переглянути всі запити →</a>'
                f'</div>'
            )
        else:
            card_block = (
                f'<div {S}"background:#fef2f2;border:1px solid #fecaca;border-radius:10px;'
                f'padding:10px 14px;margin-top:12px;">'
                f'<span {S}"font-size:12px;color:#ef4444;font-weight:600;">'
                f'⚠️ Картку виплати не вказано</span>'
                f'</div>'
            )

        pending_block = ''
        if pending_now > 0:
            pending_block = (
                f'<div {S}"display:flex;justify-content:space-between;align-items:center;'
                f'background:#fffbeb;border:1px solid #fde68a;border-radius:10px;'
                f'padding:10px 14px;margin-top:10px;">'
                f'<span {S}"font-size:12px;color:#d97706;font-weight:700;">💰 Доступно до виведення</span>'
                f'<span {S}"font-size:16px;font-weight:800;color:#d97706;">{pending_now:,.0f} ₴</span>'
                f'</div>'
            )

        section5_left = card(
            f'<div {S}"font-size:12px;font-weight:700;color:#5A00CC;text-transform:uppercase;'
            f'letter-spacing:0.8px;margin-bottom:14px;">💸 Виведення коштів</div>'
            f'<div {S}"display:grid;grid-template-columns:1fr 1fr;gap:8px;">'
            f'{wr_pill("📋", "Всього запитів", wr_total, "#374151", "#f9fafb")}'
            f'{wr_pill("✅", "Виплачено", wr_completed, "#7900FF", "#f5f3ff")}'
            f'{wr_pill("⏳", "Очікує розгляду", wr_pending, "#d97706", "#fffbeb")}'
            f'{wr_pill("🔄", "Схвалено", wr_approved, "#10b981", "#f0fdf4")}'
            f'{wr_pill("❌", "Відхилено", wr_rejected, "#ef4444", "#fef2f2")}'
            f'{wr_pill("💵", "Виплачено разом", f"{wr_paid_sum:,.0f} ₴", "#7900FF", "#f5f3ff")}'
            f'</div>'
            f'{pending_block}'
            f'{card_block}',
        )

        # Withdrawal history table (last 5)
        recent_wrs = wrs.order_by('-created_at')[:5]
        wr_rows = ''
        status_cfg = {
            WR.Status.PENDING:   ('#d97706', '#fffbeb', '⏳ Очікує'),
            WR.Status.APPROVED:  ('#10b981', '#f0fdf4', '✅ Схвалено'),
            WR.Status.REJECTED:  ('#ef4444', '#fef2f2', '❌ Відхилено'),
            WR.Status.COMPLETED: ('#7900FF', '#f5f3ff', '💸 Виплачено'),
        }
        for wr in recent_wrs:
            sc, sbg, sl = status_cfg.get(wr.status, ('#6b7280', '#f9fafb', wr.status))
            edit_url = reverse('taxi_admin:drivers_withdrawalrequest_change', args=[wr.pk])
            ref = f'<span {S}"font-size:10px;color:#10b981;">{wr.payment_reference[:20]}</span>' if wr.payment_reference else ''
            wr_rows += (
                f'<tr>'
                f'<td {S}"padding:6px 8px;font-size:12px;color:#374151;">{wr.created_at.strftime("%d.%m.%Y")}</td>'
                f'<td {S}"padding:6px 8px;font-size:13px;font-weight:700;color:#7900FF;">{float(wr.amount):,.0f} ₴</td>'
                f'<td {S}"padding:6px 8px;">'
                f'<span {S}"background:{sbg};color:{sc};border:1px solid {sc}40;padding:2px 8px;'
                f'border-radius:20px;font-size:11px;font-weight:700;white-space:nowrap;">{sl}</span>'
                f'</td>'
                f'<td {S}"padding:6px 8px;">{ref}</td>'
                f'<td {S}"padding:6px 8px;">'
                f'<a href="{edit_url}" {S}"font-size:11px;color:#7900FF;font-weight:600;">Деталі</a>'
                f'</td>'
                f'</tr>'
            )

        section5_right = card(
            f'<div {S}"font-size:12px;font-weight:700;color:#5A00CC;text-transform:uppercase;'
            f'letter-spacing:0.8px;margin-bottom:12px;">🕐 Останні запити на виведення</div>'
            + ((
                f'<table {S}"width:100%;border-collapse:collapse;">'
                f'<thead><tr>'
                f'<th {S}"text-align:left;font-size:10px;color:#9ca3af;padding:4px 8px;">Дата</th>'
                f'<th {S}"text-align:left;font-size:10px;color:#9ca3af;padding:4px 8px;">Сума</th>'
                f'<th {S}"text-align:left;font-size:10px;color:#9ca3af;padding:4px 8px;">Статус</th>'
                f'<th {S}"text-align:left;font-size:10px;color:#9ca3af;padding:4px 8px;">Транзакція</th>'
                f'<th></th>'
                f'</tr></thead>'
                f'<tbody>{wr_rows}</tbody>'
                f'</table>'
            ) if wr_rows else f'<div {S}"color:#9ca3af;font-size:13px;">Запитів ще немає</div>')
        )

        return mark_safe(
            f'<div {S}"font-family:Inter,system-ui,sans-serif;display:flex;flex-direction:column;gap:12px;">'
            f'<div {S}"display:grid;grid-template-columns:1fr 1fr 1.3fr;gap:12px;align-items:start;">'
            f'{section1}{section2}{section3}'
            f'</div>'
            f'<div {S}"display:grid;grid-template-columns:1fr 1.6fr;gap:12px;align-items:start;">'
            f'{section4_left}{section4_right}'
            f'</div>'
            f'<div {S}"display:grid;grid-template-columns:1fr 1.6fr;gap:12px;align-items:start;">'
            f'{section5_left}{section5_right}'
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


@admin.register(WithdrawalRequest, site=taxi_admin)
class WithdrawalRequestAdmin(admin.ModelAdmin):
    """Admin for driver card-earnings withdrawal requests."""

    list_display = (
        'created_at_fmt', 'driver_link', 'amount_fmt',
        'payout_card_display', 'status_badge', 'admin_comment_short', 'resolved_at',
    )
    list_display_links = ('created_at_fmt', 'driver_link')
    list_filter = ('status', 'created_at')
    search_fields = ('driver__user__email', 'driver__user__first_name', 'driver__user__last_name')
    ordering = ('-created_at',)
    readonly_fields = ('id', 'driver_link', 'amount', 'status_badge', 'created_at', 'resolved_at', 'payout_card_display')

    fieldsets = (
        ('Запит', {
            'fields': ('id', 'driver_link', 'amount', 'status_badge', 'created_at'),
        }),
        ('Реквізити виплати', {
            'fields': ('payout_card_display',),
            'description': 'Номер картки водія для переказу коштів',
        }),
        ('Рішення', {
            'fields': ('status', 'admin_comment', 'payment_reference', 'resolved_at'),
        }),
    )

    actions = ['approve_requests', 'reject_requests', 'mark_completed']

    # ── Save override (handles manual form edits) ─────────────────────────────

    def save_model(self, request, obj, form, change):
        from django.utils import timezone
        from decimal import Decimal

        if change and 'status' in form.changed_data:
            old_status = WithdrawalRequest.objects.get(pk=obj.pk).status
            new_status = obj.status

            if new_status in (WithdrawalRequest.Status.APPROVED,
                              WithdrawalRequest.Status.REJECTED,
                              WithdrawalRequest.Status.COMPLETED):
                if not obj.resolved_at:
                    obj.resolved_at = timezone.now()

            # Restore balance if rejected
            if new_status == WithdrawalRequest.Status.REJECTED and old_status in (
                WithdrawalRequest.Status.PENDING, WithdrawalRequest.Status.APPROVED
            ):
                driver = obj.driver
                driver.pending_card_withdrawal = (
                    Decimal(str(driver.pending_card_withdrawal)) + obj.amount
                )
                driver.save(update_fields=['pending_card_withdrawal'])

        super().save_model(request, obj, form, change)

    # ── Actions ──────────────────────────────────────────────────────────────

    def approve_requests(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status=WithdrawalRequest.Status.PENDING).update(
            status=WithdrawalRequest.Status.APPROVED,
            resolved_at=timezone.now(),
        )
        self.message_user(request, f'Схвалено {updated} запитів.')
    approve_requests.short_description = '✅ Схвалити вибрані'

    def reject_requests(self, request, queryset):
        from django.utils import timezone
        from decimal import Decimal

        updated = 0
        for wr in queryset.filter(
            status__in=[WithdrawalRequest.Status.PENDING, WithdrawalRequest.Status.APPROVED]
        ).select_related('driver'):
            wr.status = WithdrawalRequest.Status.REJECTED
            wr.resolved_at = timezone.now()
            wr.save(update_fields=['status', 'resolved_at'])
            # Restore frozen amount back to driver balance
            driver = wr.driver
            driver.pending_card_withdrawal = (
                Decimal(str(driver.pending_card_withdrawal)) + wr.amount
            )
            driver.save(update_fields=['pending_card_withdrawal'])
            updated += 1
        self.message_user(request, f'Відхилено {updated} запитів, суму повернено на баланс водія.')
    reject_requests.short_description = '❌ Відхилити вибрані'

    def mark_completed(self, request, queryset):
        from django.utils import timezone
        from decimal import Decimal

        updated = 0
        for wr in queryset.filter(status=WithdrawalRequest.Status.APPROVED).select_related('driver'):
            wr.status = WithdrawalRequest.Status.COMPLETED
            wr.resolved_at = timezone.now()
            wr.save(update_fields=['status', 'resolved_at'])
            # Amount was already deducted from pending_card_withdrawal on request creation
            updated += 1
        self.message_user(request, f'Виплачено {updated} запитів.')
    mark_completed.short_description = '💸 Позначити як виплачено'

    # ── Display helpers ───────────────────────────────────────────────────────

    def payout_card_display(self, obj):
        card = obj.driver.payout_card_number
        if not card:
            return mark_safe(
                '<span style="color:#ef4444;font-weight:600;font-size:12px;">'
                '⚠️ Картку не вказано</span>'
            )
        return mark_safe(
            f'<div style="background:#f5f3ff;border:1px solid #ede9fe;border-radius:8px;'
            f'padding:8px 14px;display:inline-block;">'
            f'<div style="font-size:10px;color:#6b7280;font-weight:600;text-transform:uppercase;'
            f'letter-spacing:0.5px;margin-bottom:4px;">💳 Картка виплати</div>'
            f'<div style="font-size:18px;font-weight:800;color:#7900FF;letter-spacing:2px;">'
            f'{card}</div>'
            f'</div>'
        )
    payout_card_display.short_description = 'Картка виплати'

    def created_at_fmt(self, obj):
        return obj.created_at.strftime('%d.%m.%Y %H:%M')
    created_at_fmt.short_description = 'Дата запиту'
    created_at_fmt.admin_order_field = 'created_at'

    def driver_link(self, obj):
        url = reverse('taxi_admin:drivers_driver_change', args=[obj.driver.pk])
        name = f'{obj.driver.user.last_name} {obj.driver.user.first_name}'.strip() or obj.driver.user.email
        return mark_safe(
            f'<a href="{url}" style="font-weight:600;color:#7900FF;text-decoration:none;">'
            f'{name}<br/>'
            f'<span style="font-size:11px;color:#6b7280;font-weight:400;">{obj.driver.user.email}</span>'
            f'</a>'
        )
    driver_link.short_description = 'Водій'

    def amount_fmt(self, obj):
        return mark_safe(
            f'<span style="font-size:16px;font-weight:800;color:#7900FF;">'
            f'{obj.amount:.0f} ₴</span>'
        )
    amount_fmt.short_description = 'Сума'
    amount_fmt.admin_order_field = 'amount'

    def status_badge(self, obj):
        config = {
            WithdrawalRequest.Status.PENDING:   ('#f59e0b', '#fffbeb', '⏳ Очікує розгляду'),
            WithdrawalRequest.Status.APPROVED:  ('#10b981', '#f0fdf4', '✅ Схвалено'),
            WithdrawalRequest.Status.REJECTED:  ('#ef4444', '#fef2f2', '❌ Відхилено'),
            WithdrawalRequest.Status.COMPLETED: ('#7900FF', '#f5f3ff', '💸 Виплачено'),
        }
        color, bg, label = config.get(obj.status, ('#6b7280', '#f9fafb', obj.status))
        return mark_safe(
            f'<span style="background:{bg};color:{color};border:1px solid {color}40;'
            f'padding:4px 12px;border-radius:20px;font-weight:700;font-size:12px;'
            f'white-space:nowrap;">{label}</span>'
        )
    status_badge.short_description = 'Статус'

    def admin_comment_short(self, obj):
        if not obj.admin_comment:
            return mark_safe('<span style="color:#9ca3af;">—</span>')
        short = obj.admin_comment[:60]
        if len(obj.admin_comment) > 60:
            short += '…'
        return short
    admin_comment_short.short_description = 'Коментар'
