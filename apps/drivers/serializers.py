"""
Serializers for drivers app.
"""

from rest_framework import serializers
from django.contrib.gis.geos import Point
from apps.drivers.models import Driver
from apps.users.serializers import UserSerializer


class LocationSerializer(serializers.Serializer):
    """Serializer for GPS coordinates."""
    latitude = serializers.FloatField(min_value=-90, max_value=90)
    longitude = serializers.FloatField(min_value=-180, max_value=180)


class DriverSerializer(serializers.ModelSerializer):
    """Read serializer for Driver."""
    user = UserSerializer(read_only=True)
    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()
    is_available = serializers.BooleanField(read_only=True)

    class Meta:
        model = Driver
        fields = [
            'id', 'user', 'status', 'availability', 'vehicle_type',
            'vehicle_make', 'vehicle_model', 'vehicle_year', 'vehicle_color',
            'vehicle_plate', 'rating', 'total_rides',
            'latitude', 'longitude', 'location_updated_at',
            'created_at', 'is_available',
        ]
        read_only_fields = [
            'id', 'status', 'rating', 'total_rides', 'created_at', 'location_updated_at',
        ]

    def get_latitude(self, obj) -> float | None:
        if obj.current_location:
            return obj.current_location.y
        return None

    def get_longitude(self, obj) -> float | None:
        if obj.current_location:
            return obj.current_location.x
        return None


class DriverRegistrationSerializer(serializers.ModelSerializer):
    """Write serializer for Driver registration."""

    class Meta:
        model = Driver
        fields = [
            'vehicle_type', 'vehicle_make', 'vehicle_model',
            'vehicle_year', 'vehicle_color', 'vehicle_plate',
            'license_number', 'license_expiry',
        ]

    def validate_vehicle_plate(self, value):
        if Driver.objects.filter(vehicle_plate=value).exists():
            raise serializers.ValidationError('Vehicle plate already registered.')
        return value.upper()

    def validate_license_number(self, value):
        if Driver.objects.filter(license_number=value).exists():
            raise serializers.ValidationError('License number already registered.')
        return value


class DriverLocationSerializer(serializers.Serializer):
    """Serializer for updating driver location."""
    latitude = serializers.FloatField(min_value=-90, max_value=90)
    longitude = serializers.FloatField(min_value=-180, max_value=180)


class DriverAvailabilitySerializer(serializers.Serializer):
    """Serializer for updating driver availability."""
    availability = serializers.ChoiceField(
        choices=Driver.Availability.choices
    )


class DriverDetailSerializer(DriverSerializer):
    """Detailed read serializer with additional stats."""
    distance_km = serializers.SerializerMethodField()

    class Meta(DriverSerializer.Meta):
        fields = DriverSerializer.Meta.fields + [
            'rejection_reason', 'suspension_reason', 'total_earnings', 'distance_km',
        ]

    def get_distance_km(self, obj) -> float | None:
        if hasattr(obj, 'distance') and obj.distance:
            return round(obj.distance.km, 2)
        return None


class DriverListSerializer(serializers.ModelSerializer):
    """Minimal serializer for Driver list."""
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_full_name = serializers.CharField(source='user.full_name', read_only=True)

    class Meta:
        model = Driver
        fields = [
            'id', 'user_email', 'user_full_name', 'status', 'availability',
            'vehicle_type', 'rating', 'total_rides', 'created_at',
        ]
        read_only_fields = fields