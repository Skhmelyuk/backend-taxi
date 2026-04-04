import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.rides.models import Ride
from apps.rides.serializers import (
    RideSerializer, RideCreateSerializer, PriceEstimateSerializer,
    RideCancelSerializer, RideRateSerializer,
)
from apps.rides.services import RideService, PricingService
from core.permissions import IsDriverUser

logger = logging.getLogger(__name__)


class RideViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for Ride model."""

    serializer_class = RideSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if getattr(user, 'role', None) == 'admin':
            return Ride.objects.all()
        elif getattr(user, 'role', None) == 'driver':
            try:
                return Ride.objects.for_driver(user.driver_profile)
            except Exception:
                return Ride.objects.none()
        return Ride.objects.for_user(user)

    @action(detail=False, methods=['post'])
    def create_ride(self, request):
        """POST /api/v1/rides/create_ride/ — Create new ride."""
        serializer = RideCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        d = serializer.validated_data
        try:
            ride = RideService.create_ride(
                user=request.user,
                pickup_lat=d['pickup_lat'], pickup_lon=d['pickup_lon'],
                dropoff_lat=d['dropoff_lat'], dropoff_lon=d['dropoff_lon'],
                pickup_address=d['pickup_address'], dropoff_address=d['dropoff_address'],
                vehicle_type=d['vehicle_type'],
            )
            return Response(RideSerializer(ride).data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def estimate(self, request):
        """POST /api/v1/rides/estimate/ — Price estimate."""
        serializer = PriceEstimateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        d = serializer.validated_data
        estimates = {}
        for vtype in ['economy', 'comfort', 'business']:
            estimates[vtype] = PricingService.get_price_estimate(
                d['pickup_lat'], d['pickup_lon'], d['dropoff_lat'], d['dropoff_lon'], vtype
            )
        return Response({'estimates': estimates})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsDriverUser])
    def accept(self, request, pk=None):
        """POST /api/v1/rides/{id}/accept/ — Driver accepts ride."""
        try:
            driver = request.user.driver_profile
            ride = RideService.accept_ride(pk, driver)
            return Response(RideSerializer(ride).data)
        except (ValueError, Exception) as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsDriverUser])
    def start(self, request, pk=None):
        """POST /api/v1/rides/{id}/start/ — Driver starts ride."""
        try:
            driver = request.user.driver_profile
            ride = RideService.start_ride(pk, driver)
            return Response(RideSerializer(ride).data)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsDriverUser])
    def complete(self, request, pk=None):
        """POST /api/v1/rides/{id}/complete/ — Driver completes ride."""
        try:
            driver = request.user.driver_profile
            distance = request.data.get('actual_distance_km')
            ride = RideService.complete_ride(pk, driver, float(distance) if distance else None)
            return Response(RideSerializer(ride).data)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """POST /api/v1/rides/{id}/cancel/ — Cancel ride."""
        serializer = RideCancelSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            ride = RideService.cancel_ride(
                pk, request.user,
                serializer.validated_data['reason'],
                serializer.validated_data.get('comment', '')
            )
            return Response(RideSerializer(ride).data)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """
        GET /api/v1/rides/{id}/status/ — Lightweight status polling endpoint.
        
        Used by mobile clients to poll ride status every few seconds.
        Returns minimal data to reduce payload size.
        """
        try:
            ride = Ride.objects.get(id=pk)

            # Permission: only ride user, assigned driver, or admin
            user = request.user
            if (user != ride.user and
                    (not hasattr(user, 'driver_profile') or ride.driver != user.driver_profile) and
                    getattr(user, 'role', None) != 'admin'):
                return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

            data = {
                'id': str(ride.id),
                'status': ride.status,
                'driver_location': None,
            }

            # Include driver location if ride is active
            if ride.driver and ride.status in ['accepted', 'in_progress']:
                from apps.drivers.services import LocationCacheService
                cached = LocationCacheService.get_driver_location(str(ride.driver.id))
                if cached:
                    data['driver_location'] = {
                        'latitude': cached['lat'],
                        'longitude': cached['lon'],
                    }
                elif ride.driver.current_location:
                    data['driver_location'] = {
                        'latitude': ride.driver.current_location.y,
                        'longitude': ride.driver.current_location.x,
                    }

            return Response(data)
        except Ride.DoesNotExist:
            return Response({'error': 'Ride not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'])
    def rate(self, request, pk=None):
        """POST /api/v1/rides/{id}/rate/ — Rate completed ride."""
        serializer = RideRateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            ride = RideService.rate_ride(
                pk, request.user,
                serializer.validated_data['rating'],
                serializer.validated_data.get('comment', '')
            )
            return Response(RideSerializer(ride).data)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)