from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Read serializer."""
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'phone_number', 'first_name', 'last_name',
            'full_name', 'profile_image', 'role', 'is_verified', 'created_at',
        ]
        read_only_fields = ['id', 'email', 'role', 'is_verified', 'created_at']


class UserDetailSerializer(serializers.ModelSerializer):
    """Detailed read serializer with statistics."""
    full_name = serializers.CharField(read_only=True)
    rides_count = serializers.SerializerMethodField()
    total_spent = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'phone_number', 'first_name', 'last_name',
            'full_name', 'profile_image', 'role', 'is_verified', 'is_active',
            'created_at', 'updated_at', 'last_login',
            'rides_count', 'total_spent', 'average_rating',
        ]
        read_only_fields = [
            'id', 'email', 'role', 'is_verified', 'is_active',
            'created_at', 'updated_at', 'last_login',
        ]

    def get_rides_count(self, obj) -> int:
        return 0  # Буде реалізовано в Plan 04

    def get_total_spent(self, obj) -> float:
        return 0.0  # Буде реалізовано в Plan 04

    def get_average_rating(self, obj) -> float:
        return 0.0  # Буде реалізовано в Plan 04


class UserUpdateSerializer(serializers.ModelSerializer):
    """Write serializer — update profile."""

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone_number', 'profile_image']

    def validate_phone_number(self, value):
        if value:
            from core.validators import validate_phone_number
            validate_phone_number(value)
        return value

    def update(self, instance, validated_data):
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.phone_number = validated_data.get('phone_number', instance.phone_number)
        instance.profile_image = validated_data.get('profile_image', instance.profile_image)
        instance.save()
        return instance


class FCMTokenSerializer(serializers.Serializer):
    """Serializer for FCM token update."""
    fcm_token = serializers.CharField(required=True, max_length=500)

    def validate_fcm_token(self, value):
        if not value or len(value) < 10:
            raise serializers.ValidationError('Invalid FCM token')
        return value


class UserListSerializer(serializers.ModelSerializer):
    """Minimal serializer for admin list view."""
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'full_name', 'role', 'is_active', 'is_verified', 'created_at']
        read_only_fields = ['id', 'email', 'full_name', 'role', 'is_active', 'is_verified', 'created_at']