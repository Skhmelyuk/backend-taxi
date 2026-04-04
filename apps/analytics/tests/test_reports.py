"""Tests for ReportService."""

import pytest
from apps.analytics.services.report_service import ReportService


@pytest.mark.django_db
class TestReportService:
    """Tests for ReportService."""

    def test_generate_csv_report_empty(self):
        """CSV report with empty data returns valid response."""
        response = ReportService.generate_csv_report([], filename='test.csv')
        assert response.status_code == 200
        assert 'text/csv' in response['Content-Type']
        assert 'attachment; filename="test.csv"' in response['Content-Disposition']

    def test_generate_csv_report_with_data(self):
        """CSV report with data includes headers and rows."""
        data = [
            {'id': '1', 'status': 'completed', 'price': 150},
            {'id': '2', 'status': 'cancelled', 'price': 0},
        ]
        response = ReportService.generate_csv_report(data, filename='rides.csv')
        content = response.content.decode('utf-8')
        assert 'id' in content
        assert 'completed' in content
        assert 'cancelled' in content

    def test_generate_pdf_report_returns_pdf(self):
        """PDF report returns application/pdf response."""
        data = [{'key': 'value', 'count': 42}]
        response = ReportService.generate_pdf_report(data, title='Test', filename='test.pdf')
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/pdf'
        assert 'attachment; filename="test.pdf"' in response['Content-Disposition']

    def test_export_rides_csv_empty(self):
        """Rides CSV export with no rides returns empty CSV."""
        response = ReportService.export_rides_csv()
        assert response.status_code == 200
        assert 'text/csv' in response['Content-Type']