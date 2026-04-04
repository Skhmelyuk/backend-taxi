"""Analytics views — admin-only endpoints."""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework.decorators import api_view, permission_classes
from apps.analytics.services.analytics_service import AnalyticsService
from apps.analytics.services.report_service import ReportService


class RideAnalyticsView(APIView):
    """Ride analytics endpoint."""

    permission_classes = [IsAdminUser]

    def get(self, request):
        start = request.query_params.get('start_date')
        end = request.query_params.get('end_date')
        data = AnalyticsService.get_ride_analytics(
            start_date=start, end_date=end
        )
        return Response(data)


class DriverAnalyticsView(APIView):
    """Driver analytics endpoint."""

    permission_classes = [IsAdminUser]

    def get(self, request):
        data = AnalyticsService.get_driver_analytics()
        return Response(data)


class RevenueAnalyticsView(APIView):
    """Revenue analytics endpoint."""

    permission_classes = [IsAdminUser]

    def get(self, request):
        start = request.query_params.get('start_date')
        end = request.query_params.get('end_date')
        data = AnalyticsService.get_revenue_analytics(
            start_date=start, end_date=end
        )
        return Response(data)


class DailyStatsView(APIView):
    """Daily stats for the last N days."""

    permission_classes = [IsAdminUser]

    def get(self, request):
        days = int(request.query_params.get('days', 7))
        data = AnalyticsService.get_daily_stats(days=days)
        return Response(data)
    
class RideCSVReportView(APIView):
    """Download rides CSV report."""

    permission_classes = [IsAdminUser]

    def get(self, request):
        start = request.query_params.get('start_date')
        end = request.query_params.get('end_date')
        return ReportService.export_rides_csv(start_date=start, end_date=end)