"""
URL configuration for analytics app.
"""

from django.urls import path, include
from apps.analytics import views


urlpatterns = [
    path('rides/', views.RideAnalyticsView.as_view(), name='analytics-rides'),
    path('drivers/', views.DriverAnalyticsView.as_view(), name='analytics-drivers'),
    path('revenue/', views.RevenueAnalyticsView.as_view(), name='analytics-revenue'),
    path('daily/', views.DailyStatsView.as_view(), name='analytics-daily'),
    path('reports/rides/csv/', views.RideCSVReportView.as_view(), name='report-rides-csv'),
]
