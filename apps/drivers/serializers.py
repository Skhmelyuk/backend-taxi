"""
Serializers for drivers app.
"""

from rest_framework import serializers
from django.contrib.gis.geos import Point
from apps.drivers.models import Driver, DriverDocument
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


class DriverDocumentSerializer(serializers.ModelSerializer):
    """Read serializer for driver documents."""
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = DriverDocument
        fields = [
            'id', 'doc_type', 'status', 'notes', 'expires_at',
            'file_url', 'uploaded_at', 'reviewed_at', 'reviewer_id',
        ]
        read_only_fields = fields

    def get_file_url(self, obj) -> str | None:
        request = self.context.get('request')
        if obj.file and hasattr(obj.file, 'url'):
            url = obj.file.url
            if request:
                return request.build_absolute_uri(url)
            return url
        return None


class DriverDocumentUploadSerializer(serializers.Serializer):
    """Serializer for uploading or replacing driver documents."""

    doc_type = serializers.ChoiceField(choices=DriverDocument.DocumentType.choices)
    file = serializers.FileField()
    expires_at = serializers.DateField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True)


class DriverDocumentReviewSerializer(serializers.Serializer):
    """Serializer for reviewing driver documents."""

    document_id = serializers.UUIDField()
    status = serializers.ChoiceField(choices=DriverDocument.VerificationStatus.choices)
    notes = serializers.CharField(required=False, allow_blank=True)


class DriverDetailSerializer(DriverSerializer):
    """Detailed read serializer with additional stats."""
    distance_km = serializers.SerializerMethodField()
    documents = serializers.SerializerMethodField()

    class Meta(DriverSerializer.Meta):
        fields = DriverSerializer.Meta.fields + [
            'rejection_reason', 'suspension_reason', 'total_earnings', 'distance_km',
            'documents',
        ]

    def get_distance_km(self, obj) -> float | None:
        if hasattr(obj, 'distance') and obj.distance:
            return round(obj.distance.km, 2)
        return None

    def get_documents(self, obj):
        documents = obj.documents.all()
        serializer = DriverDocumentSerializer(
            documents,
            many=True,
            context=self.context,
        )
        return serializer.data


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