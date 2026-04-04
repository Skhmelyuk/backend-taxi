import csv
from io import StringIO, BytesIO
from django.http import HttpResponse
from django.utils import timezone


class ReportService:
    """Service for generating downloadable reports."""

    # ------------------------------------------------------------------ CSV --

    @staticmethod
    def generate_csv_report(data: list[dict], filename: str = 'report.csv') -> HttpResponse:
        """
        Generate a CSV HttpResponse from a list of dicts.

        Args:
            data: List of row dicts (all must share the same keys).
            filename: Name for the downloaded file.

        Returns:
            HttpResponse with Content-Disposition set.
        """
        output = StringIO()
        writer = csv.writer(output)

        if data:
            writer.writerow(data[0].keys())
            for row in data:
                writer.writerow(row.values())

        response = HttpResponse(output.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    # ------------------------------------------------------------------ PDF --

    @staticmethod
    def generate_pdf_report(
        data: list[dict],
        title: str = 'Report',
        filename: str = 'report.pdf',
    ) -> HttpResponse:
        """
        Generate a simple PDF report using reportlab.

        Args:
            data: List of row dicts.
            title: Report title shown at the top.
            filename: Name for the downloaded file.

        Returns:
            HttpResponse with application/pdf content type.
        """
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)

        # Title
        p.setFont('Helvetica-Bold', 16)
        p.drawString(72, 750, title)
        p.setFont('Helvetica', 10)
        p.drawString(72, 735, f'Generated: {timezone.now().strftime("%Y-%m-%d %H:%M")}')

        y = 710
        p.setFont('Helvetica', 11)

        for item in data:
            for key, value in item.items():
                p.drawString(72, y, f'{key}: {value}')
                y -= 16
                if y < 72:
                    p.showPage()
                    y = 750
                    p.setFont('Helvetica', 11)
            y -= 8  # gap between rows

        p.save()
        buffer.seek(0)

        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    # ------------------------------------------------------ Ride CSV helper --

    @staticmethod
    def export_rides_csv(start_date=None, end_date=None) -> HttpResponse:
        """Export rides data as CSV."""
        from apps.rides.models import Ride

        qs = Ride.objects.select_related('user', 'driver__user').order_by('-created_at')
        if start_date:
            qs = qs.filter(created_at__date__gte=start_date)
        if end_date:
            qs = qs.filter(created_at__date__lte=end_date)

        data = [
            {
                'id': str(r.id),
                'user': r.user.email,
                'driver': r.driver.user.email if r.driver else '',
                'status': r.status,
                'final_price': r.final_price or r.estimated_price,
                'created_at': r.created_at.strftime('%Y-%m-%d %H:%M'),
            }
            for r in qs[:5000]
        ]

        return ReportService.generate_csv_report(
            data,
            filename=f'rides_{timezone.now().strftime("%Y%m%d")}.csv',
        )