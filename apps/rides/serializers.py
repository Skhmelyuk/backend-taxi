from rest_framework import serializers
from apps.rides.models import Ride


class RideCreateSerializer(serializers.Serializer):
    """Serializer for ride creation."""
    pickup_lat = serializers.FloatField(min_value=-90, max_value=90)
    pickup_lon = serializers.FloatField(min_value=-180, max_value=180)
    dropoff_lat = serializers.FloatField(min_value=-90, max_value=90)
    dropoff_lon = serializers.FloatField(min_value=-180, max_value=180)
    pickup_address = serializers.CharField(max_length=500)
    dropoff_address = serializers.CharField(max_length=500)
    vehicle_type = serializers.ChoiceField(choices=Ride.VehicleType.choices)
    promo_code = serializers.CharField(required=False, allow_blank=True)


class RideSerializer(serializers.ModelSerializer):
    """Read serializer for Ride."""
    user_email = serializers.CharField(source='user.email', read_only=True)
    driver_info = serializers.SerializerMethodField()
    pickup_lat = serializers.SerializerMethodField()
    pickup_lon = serializers.SerializerMethodField()
    dropoff_lat = serializers.SerializerMethodField()
    dropoff_lon = serializers.SerializerMethodField()

    class Meta:
        model = Ride
        fields = [
            'id', 'user_email', 'driver_info', 'status', 'vehicle_type',
            'pickup_lat', 'pickup_lon', 'pickup_address',
            'dropoff_lat', 'dropoff_lon', 'dropoff_address',
            'estimated_distance', 'estimated_duration', 'estimated_price',
            'final_distance', 'final_duration', 'final_price',
            'discount', 'rating', 'user_comment',
            'cancellation_reason', 'cancellation_comment',
            'created_at', 'accepted_at', 'started_at', 'completed_at', 'cancelled_at',
        ]
        read_only_fields = fields

    def get_driver_info(self, obj):
        if obj.driver:
            return {
                'id': str(obj.driver.id),
                'name': obj.driver.user.full_name,
                'rating': float(obj.driver.rating),
                'vehicle': f"{obj.driver.vehicle_make} {obj.driver.vehicle_model}",
                'plate': obj.driver.vehicle_plate,
            }
        return None

    def get_pickup_lat(self, obj): return obj.pickup_location.y
    def get_pickup_lon(self, obj): return obj.pickup_location.x
    def get_dropoff_lat(self, obj): return obj.dropoff_location.y
    def get_dropoff_lon(self, obj): return obj.dropoff_location.x


class PriceEstimateSerializer(serializers.Serializer):
    """Serializer for price estimate request."""
    pickup_lat = serializers.FloatField()
    pickup_lon = serializers.FloatField()
    dropoff_lat = serializers.FloatField()
    dropoff_lon = serializers.FloatField()
    vehicle_type = serializers.ChoiceField(choices=Ride.VehicleType.choices)


class RideCancelSerializer(serializers.Serializer):
    """Serializer for ride cancellation."""
    reason = serializers.ChoiceField(choices=Ride.CancellationReason.choices)
    comment = serializers.CharField(required=False, allow_blank=True)


class RideRateSerializer(serializers.Serializer):
    """Serializer for ride rating."""
    rating = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(required=False, allow_blank=True)