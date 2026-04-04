from django.db.models import Count, Sum, Avg, Q, F
from django.utils import timezone
from datetime import timedelta, date


class AnalyticsService:
    """Service for analytics calculations."""

    @staticmethod
    def get_ride_analytics(start_date=None, end_date=None):
        """Get ride analytics for a given period."""
        from apps.rides.models import Ride

        queryset = Ride.objects.all()

        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)

        completed = queryset.filter(status='completed')
        cancelled = queryset.filter(status='cancelled')

        agg = completed.aggregate(
            avg_price=Avg('final_price'),
            total_distance=Sum('final_distance'),
        )

        return {
            'total_rides': queryset.count(),
            'completed_rides': completed.count(),
            'cancelled_rides': cancelled.count(),
            'completion_rate': round(
                completed.count() / queryset.count() * 100, 1
            ) if queryset.count() > 0 else 0,
            'avg_ride_price': round(float(agg['avg_price'] or 0), 2),
            'total_distance_km': round(float(agg['total_distance'] or 0), 2),
        }

    @staticmethod
    def get_driver_analytics(start_date=None, end_date=None):
        """Get driver analytics."""
        from apps.drivers.models import Driver

        drivers = Driver.objects.all()

        return {
            'total_drivers': drivers.count(),
            'approved_drivers': drivers.filter(status='approved').count(),
            'pending_drivers': drivers.filter(status='pending').count(),
            'online_drivers': drivers.filter(
                status='approved', availability='online'
            ).count(),
            'avg_rating': round(
                float(
                    drivers.filter(status='approved').aggregate(
                        avg=Avg('rating')
                    )['avg'] or 0
                ), 2
            ),
            'top_drivers': list(
                drivers.filter(status='approved')
                .order_by('-total_rides')[:5]
                .values('id', 'user__email', 'total_rides', 'rating')
            ),
        }

    @staticmethod
    def get_revenue_analytics(start_date=None, end_date=None):
        """Get revenue analytics."""
        from apps.payments.models import Payment

        queryset = Payment.objects.filter(status='success')

        if start_date:
            queryset = queryset.filter(processed_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(processed_at__date__lte=end_date)

        agg = queryset.aggregate(
            total=Sum('amount'),
            avg=Avg('amount'),
        )

        return {
            'total_revenue': round(float(agg['total'] or 0), 2),
            'total_transactions': queryset.count(),
            'avg_transaction': round(float(agg['avg'] or 0), 2),
        }

    @staticmethod
    def get_daily_stats(days=7):
        """Get daily stats for the last N days."""
        from apps.rides.models import Ride
        from apps.payments.models import Payment

        result = []
        today = timezone.now().date()

        for i in range(days - 1, -1, -1):
            day = today - timedelta(days=i)
            rides = Ride.objects.filter(created_at__date=day)
            revenue = Payment.objects.filter(
                status='success', processed_at__date=day
            ).aggregate(total=Sum('amount'))['total'] or 0

            result.append({
                'date': str(day),
                'total_rides': rides.count(),
                'completed': rides.filter(status='completed').count(),
                'revenue': round(float(revenue), 2),
            })

        return result