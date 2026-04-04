"""
Views for payments app.
"""

import base64
import json
import logging
from decimal import Decimal

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.payments.models import Payment
from apps.payments.serializers import (
    CreatePaymentSerializer,
    PaymentSerializer,
    PromoCodeValidateSerializer,
)
from apps.payments.services import PaymentService, PromoCodeService, RefundService

logger = logging.getLogger(__name__)


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for Payment model."""

    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if getattr(user, 'role', None) == 'admin':
            return Payment.objects.all()
        return Payment.objects.for_user(user)

    @action(detail=False, methods=['post'])
    def create_payment(self, request):
        """POST /api/v1/payments/create_payment/ — Initiate payment for ride."""
        serializer = CreatePaymentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        ride_id = request.data.get('ride_id')
        if not ride_id:
            return Response(
                {'error': 'ride_id is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            from apps.rides.models import Ride
            ride = Ride.objects.get(id=ride_id, user=request.user)
        except Ride.DoesNotExist:
            return Response(
                {'error': 'Ride not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            d = serializer.validated_data
            result = PaymentService.create_payment(
                ride=ride,
                user=request.user,
                payment_method=d['payment_method'],
                provider=d.get('provider', 'liqpay'),
                callback_url=d.get('callback_url', '') or '',
            )
            return Response(
                {
                    'payment': PaymentSerializer(result['payment']).data,
                    'payment_url': result.get('payment_url'),
                    'status': result['status'],
                },
                status=status.HTTP_201_CREATED,
            )
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=False, methods=['get'])
    def history(self, request):
        """GET /api/v1/payments/history/ — Payment history."""
        payments = PaymentService.get_user_payment_history(request.user)
        return Response(PaymentSerializer(payments, many=True).data)

    @action(detail=False, methods=['post'])
    def validate_promo(self, request):
        """POST /api/v1/payments/validate_promo/ — Validate promo code."""
        serializer = PromoCodeValidateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            discount, promo = PromoCodeService.validate_promo_code(
                serializer.validated_data['code'],
                Decimal(str(serializer.validated_data['ride_price'])),
            )
            return Response({
                'valid': True,
                'code': promo.code,
                'discount': float(discount),
                'discount_type': promo.discount_type,
            })
        except ValueError as e:
            return Response(
                {'valid': False, 'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
    
    @action(detail=True, methods=['post'])
    def refund(self, request, pk=None):
        """POST /api/v1/payments/{id}/refund/ — Request refund (admin or user)."""
        try:
            amount = Decimal(str(request.data.get('amount', 0)))
            reason = request.data.get('reason', '')

            if not amount or amount <= 0:
                return Response({'error': 'Valid amount required'}, status=status.HTTP_400_BAD_REQUEST)
            if not reason:
                return Response({'error': 'Reason required'}, status=status.HTTP_400_BAD_REQUEST)

            refund = RefundService.create_refund(pk, amount, reason)

            return Response({
                'refund_id': str(refund.id),
                'status': refund.status,
                'amount': float(refund.amount),
            })

        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@require_http_methods(['POST'])
def liqpay_callback(request):
    """Webhook endpoint for LiqPay payment callbacks."""
    try:
        data = request.POST.get('data', '')
        signature = request.POST.get('signature', '')

        from apps.payments.providers.liqpay_provider import LiqPayProvider
        provider = LiqPayProvider()

        if not provider.verify_callback({'data': data}, signature):
            logger.warning("Invalid LiqPay callback signature")
            return JsonResponse({'error': 'Invalid signature'}, status=401)

        payload = json.loads(base64.b64decode(data).decode())
        order_id = payload.get('order_id')
        payment_status = payload.get('status')
        transaction_id = payload.get('payment_id')

        logger.info("LiqPay callback: order=%s, status=%s", order_id, payment_status)

        if payment_status in ('success', 'sandbox'):
            PaymentService.confirm_payment(order_id, str(transaction_id))
        elif payment_status in ('failure', 'error', 'reversed'):
            PaymentService.fail_payment(order_id, f"Provider status: {payment_status}")

        return JsonResponse({'status': 'ok'})

    except Exception as e:
        logger.error("LiqPay callback error: %s", e, exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def fondy_callback(request):
    """Webhook endpoint for Fondy payment callbacks."""
    try:
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        response_data = payload.get('response', {})
        order_id = response_data.get('order_id')
        payment_status = response_data.get('order_status')

        logger.info("Fondy callback: order=%s, status=%s", order_id, payment_status)

        if payment_status == 'approved':
            PaymentService.confirm_payment(order_id)
        elif payment_status in ('declined', 'expired'):
            PaymentService.fail_payment(order_id, f"Provider status: {payment_status}")

        return JsonResponse({'status': 'ok'})

    except Exception as e:
        logger.error("Fondy callback error: %s", e, exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)
