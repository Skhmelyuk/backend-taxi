import pytest
from decimal import Decimal
from django.utils import timezone
from apps.analytics.services.analytics_service import AnalyticsService
from apps.rides.tests.factories import RideFactory

@pytest.mark.django_db
class TestAnalyticsService:
    """Tests for AnalyticsService."""

    def test_get_ride_analytics_empty(self):
        """Returns zeros when no rides exist."""
        data = AnalyticsService.get_ride_analytics()
        assert data['total_rides'] == 0
        assert data['completed_rides'] == 0
        assert data['completion_rate'] == 0

    def test_get_ride_analytics_with_rides(self, user_factory):
        """Returns correct counts with existing rides."""
        from apps.rides.models import Ride
        user = user_factory()
        ride1 = RideFactory(user=user, status='completed')
        ride2 = RideFactory(user=user, status='cancelled')
        ride3 = RideFactory(user=user, status='completed')

        data = AnalyticsService.get_ride_analytics()
        assert data['total_rides'] == 3
        assert data['completed_rides'] == 2
        assert data['cancelled_rides'] == 1
        assert data['completion_rate'] == pytest.approx(66.7, abs=0.2)

    def test_get_driver_analytics_empty(self):
        """Returns zeros when no drivers exist."""
        data = AnalyticsService.get_driver_analytics()
        assert data['total_drivers'] == 0
        assert data['online_drivers'] == 0

    def test_get_revenue_analytics_empty(self):
        """Returns zeros when no payments exist."""
        data = AnalyticsService.get_revenue_analytics()
        assert data['total_revenue'] == 0
        assert data['total_transactions'] == 0
        assert data['avg_transaction'] == 0

    def test_get_daily_stats_returns_n_days(self):
        """Daily stats returns exactly N days."""
        data = AnalyticsService.get_daily_stats(days=7)
        assert len(data) == 7

    def test_get_daily_stats_includes_today(self):
        """Daily stats last entry is today."""
        today_str = str(timezone.now().date())
        data = AnalyticsService.get_daily_stats(days=3)
        assert data[-1]['date'] == today_str

    def test_get_ride_analytics_date_filter(self, user_factory):
        """Date filter works correctly."""
        from apps.rides.models import Ride
        user = user_factory()
        ride = RideFactory(user=user, status='completed')

        # Use today as filter — should include the ride
        today = str(timezone.now().date())
        data = AnalyticsService.get_ride_analytics(start_date=today, end_date=today)
        assert data['total_rides'] >= 1