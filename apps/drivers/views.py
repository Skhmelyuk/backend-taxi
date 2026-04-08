"""
Views for drivers app.
"""

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.drivers.models import Driver
from apps.drivers.serializers import (
    DriverSerializer, DriverDetailSerializer, DriverListSerializer,
    DriverRegistrationSerializer, DriverLocationSerializer, DriverAvailabilitySerializer,
    DriverDocumentSerializer, DriverDocumentUploadSerializer, DriverDocumentReviewSerializer,
)
from apps.drivers.services import DriverService, DriverDocumentService
from core.permissions import IsAdminUser, IsDriverUser

logger = logging.getLogger(__name__)


class DriverViewSet(viewsets.ModelViewSet):
    """ViewSet for Driver model."""

    queryset = Driver.objects.select_related('user')
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return DriverListSerializer
        elif self.action == 'register':
            return DriverRegistrationSerializer
        elif self.action == 'update_location':
            return DriverLocationSerializer
        elif self.action == 'availability':
            return DriverAvailabilitySerializer
        elif self.action == 'upload_document':
            return DriverDocumentUploadSerializer
        elif self.action == 'review_document':
            return DriverDocumentReviewSerializer
        elif self.action in ['retrieve', 'me']:
            return DriverDetailSerializer
        return DriverSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'approve', 'reject', 'suspend']:
            return [IsAuthenticated(), IsAdminUser()]
        elif self.action in ['me', 'update_location', 'availability', 'upload_document']:
            return [IsAuthenticated(), IsDriverUser()]
        elif self.action in ['review_document']:
            return [IsAuthenticated(), IsAdminUser()]
        elif self.action == 'nearby':
            return [IsAuthenticated()]
        return [IsAuthenticated()]

    @action(detail=False, methods=['post'])
    def register(self, request):
        """POST /api/drivers/register/ — Register as driver."""
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            driver = DriverService.register_driver(
                request.user, **serializer.validated_data
            )
            return Response(DriverSerializer(driver).data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def me(self, request):
        """GET /api/drivers/me/ — Current driver profile."""
        try:
            driver = request.user.driver_profile
            return Response(DriverDetailSerializer(driver).data)
        except Driver.DoesNotExist:
            return Response({'error': 'Driver profile not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'])
    def update_location(self, request):
        """POST /api/drivers/update_location/ — Update GPS location."""
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            driver = request.user.driver_profile
            DriverService.update_location(
                driver,
                serializer.validated_data['latitude'],
                serializer.validated_data['longitude']
            )
            return Response({'message': 'Location updated successfully'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['patch'])
    def availability(self, request):
        """PATCH /api/drivers/availability/ — Change availability status."""
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            driver = request.user.driver_profile
            DriverService.set_availability(driver, serializer.validated_data['availability'])
            return Response(DriverSerializer(driver).data)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['patch'])
    def update_profile(self, request):
        """PATCH /api/drivers/update_profile/ — Update driver details."""
        try:
            driver = request.user.driver_profile
            # Use registration serializer for fields validation
            serializer = DriverRegistrationSerializer(driver, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(DriverDetailSerializer(driver).data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Driver.DoesNotExist:
            return Response({'error': 'Driver profile not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'])
    def nearby(self, request):
        """GET /api/drivers/nearby/?lat=50.45&lon=30.52&radius=5&vehicle_type=economy"""
        try:
            lat = float(request.query_params.get('lat', 0))
            lon = float(request.query_params.get('lon', 0))
            radius = float(request.query_params.get('radius', 10))
            vehicle_type = request.query_params.get('vehicle_type')
            drivers = DriverService.get_nearby_drivers(lat, lon, vehicle_type, radius)
            return Response(DriverSerializer(drivers, many=True).data)
        except (ValueError, TypeError) as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='documents')
    def upload_document(self, request):
        """POST /api/drivers/documents/ — Upload or replace driver document."""
        driver = getattr(request.user, 'driver_profile', None)
        if not driver:
            return Response({'error': 'Driver profile not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            document = DriverDocumentService.upload_document(
                driver=driver,
                doc_type=serializer.validated_data['doc_type'],
                file=serializer.validated_data['file'],
                expires_at=serializer.validated_data.get('expires_at'),
                notes=serializer.validated_data.get('notes'),
            )
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        response_serializer = DriverDocumentSerializer(document, context={'request': request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='documents/review')
    def review_document(self, request):
        """POST /api/drivers/documents/review/ — Approve or reject a document (admin)."""

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            document = DriverDocumentService.review_document(
                document_id=str(serializer.validated_data['document_id']),
                status=serializer.validated_data['status'],
                reviewer=request.user,
                notes=serializer.validated_data.get('notes'),
            )
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        response_serializer = DriverDocumentSerializer(document, context={'request': request})
        return Response(response_serializer.data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """POST /api/drivers/{id}/approve/ — Approve driver (admin)."""
        try:
            driver = DriverService.approve_driver(pk, request.user)
            return Response(DriverSerializer(driver).data)
        except (Driver.DoesNotExist, ValueError) as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """POST /api/drivers/{id}/reject/ — Reject driver (admin)."""
        reason = request.data.get('reason', '')
        try:
            driver = DriverService.reject_driver(pk, reason, request.user)
            return Response(DriverSerializer(driver).data)
        except Driver.DoesNotExist as e:
            return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'])
    def suspend(self, request, pk=None):
        """POST /api/drivers/{id}/suspend/ — Suspend driver (admin)."""
        reason = request.data.get('reason', '')
        try:
            driver = DriverService.suspend_driver(pk, reason, request.user)
            return Response(DriverSerializer(driver).data)
        except Driver.DoesNotExist as e:
            return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)