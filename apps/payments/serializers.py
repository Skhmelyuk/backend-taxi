"""
Serializers for payments app.
"""

from rest_framework import serializers
from apps.payments.models import PromoCode, Payment


class PromoCodeValidateSerializer(serializers.Serializer):
    """Serializer for validating promo code."""
    code = serializers.CharField(max_length=50)
    ride_price = serializers.DecimalField(max_digits=10, decimal_places=2)


class PromoCodeSerializer(serializers.ModelSerializer):
    """Serializer for PromoCode model."""
    is_valid = serializers.BooleanField(read_only=True)

    class Meta:
        model = PromoCode
        fields = [
            'id', 'code', 'discount_type', 'discount_percent',
            'discount_amount', 'min_ride_price', 'is_valid',
        ]
        read_only_fields = fields


class PaymentSerializer(serializers.ModelSerializer):
    """Serializer for Payment model."""
    ride_id = serializers.UUIDField(source='ride.id', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'ride_id', 'user_email', 'amount', 'currency',
            'status', 'payment_method', 'provider',
            'provider_transaction_id', 'description',
            'created_at', 'processed_at',
        ]
        read_only_fields = fields


class CreatePaymentSerializer(serializers.Serializer):
    """Serializer for creating a payment."""
    payment_method = serializers.ChoiceField(choices=Payment.PaymentMethod.choices)
    provider = serializers.ChoiceField(
        choices=Payment.Provider.choices, default='liqpay'
    )
    promo_code = serializers.CharField(required=False, allow_blank=True)
    callback_url = serializers.URLField(required=False, allow_blank=True)
