from django.contrib import admin
from django.urls import path
from django.shortcuts import render
from django.db.models import Count, Sum, Avg
from django.utils import timezone
from datetime import timedelta


class TaxiAdminSite(admin.AdminSite):
    """Custom admin site with dashboard."""

    site_header = 'Taxi Service Admin'
    site_title = 'Taxi Service Admin'
    index_title = 'Dashboard'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('dashboard/', self.admin_view(self.dashboard_view), name='dashboard'),
        ]
        return custom_urls + urls

    def dashboard_view(self, request):
        """Dashboard view with business statistics."""
        from apps.rides.models import Ride
        from apps.drivers.models import Driver
        from apps.users.models import User
        from apps.payments.models import Payment

        today = timezone.now().date()
        week_ago = timezone.now() - timedelta(days=7)

        context = {
            **self.each_context(request),
            # Users
            'total_users': User.objects.count(),
            'new_users_week': User.objects.filter(created_at__gte=week_ago).count(),
            # Drivers
            'total_drivers': Driver.objects.filter(status='approved').count(),
            'online_drivers': Driver.objects.filter(
                status='approved', availability='online'
            ).count(),
            'pending_drivers': Driver.objects.filter(status='pending').count(),
            # Rides
            'total_rides': Ride.objects.count(),
            'rides_today': Ride.objects.filter(created_at__date=today).count(),
            'active_rides': Ride.objects.filter(
                status__in=['pending', 'accepted', 'in_progress']
            ).count(),
            'completed_today': Ride.objects.filter(
                status='completed', completed_at__date=today
            ).count(),
            # Revenue
            'revenue_today': Payment.objects.filter(
                status='success', processed_at__date=today
            ).aggregate(total=Sum('amount'))['total'] or 0,
            'revenue_week': Payment.objects.filter(
                status='success', processed_at__gte=week_ago
            ).aggregate(total=Sum('amount'))['total'] or 0,
            # Recent rides
            'recent_rides': Ride.objects.select_related(
                'user', 'driver__user'
            ).order_by('-created_at')[:10],
            # Recent drivers
            'pending_driver_list': Driver.objects.filter(
                status='pending'
            ).select_related('user').order_by('-created_at')[:5],
        }
        return render(request, 'admin/dashboard.html', context)


taxi_admin = TaxiAdminSite(name='taxi_admin')