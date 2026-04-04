"""Tests for analytics API views."""

import pytest
from rest_framework.test import APIClient
from django.urls import reverse


@pytest.mark.django_db
class TestAnalyticsViews:
    """Tests for analytics API endpoints."""

    def setup_method(self):
        self.client = APIClient()

    def test_ride_analytics_requires_auth(self):
        """Unauthenticated users cannot access analytics."""
        response = self.client.get('/api/v1/analytics/rides/')
        assert response.status_code in (401, 403)

    def test_ride_analytics_accessible_to_admin(self, admin_factory):
        """Admin users can access ride analytics."""
        admin = admin_factory()
        self.client.force_authenticate(user=admin)
        response = self.client.get('/api/v1/analytics/rides/')
        assert response.status_code == 200
        assert 'total_rides' in response.data

    def test_driver_analytics_accessible_to_admin(self, admin_factory):
        """Admin users can access driver analytics."""
        admin = admin_factory()
        self.client.force_authenticate(user=admin)
        response = self.client.get('/api/v1/analytics/drivers/')
        assert response.status_code == 200
        assert 'total_drivers' in response.data

    def test_revenue_analytics_accessible_to_admin(self, admin_factory):
        """Admin users can access revenue analytics."""
        admin = admin_factory()
        self.client.force_authenticate(user=admin)
        response = self.client.get('/api/v1/analytics/revenue/')
        assert response.status_code == 200
        assert 'total_revenue' in response.data

    def test_daily_stats_default_7_days(self, admin_factory):
        """Daily stats returns 7 days by default."""
        admin = admin_factory()
        self.client.force_authenticate(user=admin)
        response = self.client.get('/api/v1/analytics/daily/')
        assert response.status_code == 200
        assert len(response.data) == 7

    def test_rides_csv_download(self, admin_factory):
        """Admin can download rides CSV."""
        admin = admin_factory()
        self.client.force_authenticate(user=admin)
        response = self.client.get('/api/v1/analytics/reports/rides/csv/')
        assert response.status_code == 200
        assert 'text/csv' in response['Content-Type']