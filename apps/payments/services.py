"""
Business logic services for payments app.
"""

import logging
from decimal import Decimal
from typing import TYPE_CHECKING

from django.db import transaction
from django.utils import timezone

from apps.payments.models import Payment
from apps.payments.providers.factory import get_payment_provider

if TYPE_CHECKING:
    from apps.payments.models import PromoCode
    from apps.rides.models import Ride
    from apps.users.models import User

logger = logging.getLogger(__name__)


class PaymentService:

    @staticmethod
    def create_payment(
        ride: 'Ride',
        user: 'User',
        payment_method: str = 'card',
        provider: str = 'liqpay',
        callback_url: str = ''
    ) -> dict:
        """Initiate payment for a ride."""
        with transaction.atomic():
            if ride.status != 'completed':
                raise ValueError('Ride must be completed before payment')
            if Payment.objects.filter(ride=ride, status='success').exists():
                raise ValueError('Ride already paid')

            amount = ride.final_price or ride.estimated_price
            if not amount:
                raise ValueError('No price set for ride')

            payment = Payment.objects.create(
                ride=ride,
                user=user,
                amount=amount,
                currency='UAH',
                status=Payment.Status.PENDING,
                payment_method=payment_method,
                provider=provider,
                description=f'Taxi ride {ride.id}',
            )

        if provider == 'cash':
            payment.status = Payment.Status.SUCCESS
            payment.processed_at = timezone.now()
            payment.provider_transaction_id = f'cash_{payment.id}'
            payment.save(update_fields=['status', 'processed_at', 'provider_transaction_id'])
            logger.info("Cash payment completed: %s", payment.id)
            return {'payment': payment, 'payment_url': None, 'status': 'success'}

        try:
            provider_instance = get_payment_provider(provider)
            result = provider_instance.create_payment(
                amount=amount,
                currency='UAH',
                description=f'Taxi ride {ride.id}',
                order_id=str(payment.id),
                callback_url=callback_url or 'https://taxi-api.example.com/api/payments/callback/',
            )
            payment.provider_transaction_id = result['transaction_id']
            payment.provider_data = result.get('data', {})
            payment.status = Payment.Status.PROCESSING
            payment.save(update_fields=['provider_transaction_id', 'provider_data', 'status'])

            logger.info("Payment initiated: %s via %s", payment.id, provider)
            return {
                'payment': payment,
                'payment_url': result.get('payment_url'),
                'status': 'processing',
            }

        except Exception as e:
            payment.status = Payment.Status.FAILED
            payment.error_message = str(e)
            payment.failed_at = timezone.now()
            payment.save(update_fields=['status', 'error_message', 'failed_at'])
            logger.error("Payment creation failed: %s", e)
            raise

    @staticmethod
    @transaction.atomic
    def confirm_payment(
        payment_id: str,
        provider_transaction_id: str | None = None
    ) -> Payment:
        """Confirm successful payment."""
        payment = Payment.objects.select_for_update().get(id=payment_id)
        if payment.status == Payment.Status.SUCCESS:
            return payment

        payment.status = Payment.Status.SUCCESS
        payment.processed_at = timezone.now()
        if provider_transaction_id:
            payment.provider_transaction_id = provider_transaction_id
        payment.save(update_fields=['status', 'processed_at', 'provider_transaction_id'])

        logger.info("Payment confirmed: %s", payment.id)
        return payment

    @staticmethod
    @transaction.atomic
    def fail_payment(payment_id: str, error: str = '') -> Payment:
        """Mark payment as failed."""
        payment = Payment.objects.select_for_update().get(id=payment_id)
        payment.status = Payment.Status.FAILED
        payment.error_message = error
        payment.failed_at = timezone.now()
        payment.save(update_fields=['status', 'error_message', 'failed_at'])
        logger.warning("Payment failed: %s — %s", payment.id, error)
        return payment

    @staticmethod
    def get_payment_for_ride(ride: 'Ride') -> Payment | None:
        """Get successful payment for a ride."""
        return Payment.objects.filter(ride=ride, status='success').first()

    @staticmethod
    def get_user_payment_history(user: 'User', limit: int = 20) -> list[Payment]:
        """Get user payment history."""
        return list(
            Payment.objects.for_user(user)
            .select_related('ride')
            .order_by('-created_at')[:limit]
        )


class PromoCodeService:

    @staticmethod
    def validate_promo_code(code: str, ride_price: Decimal) -> tuple[Decimal, 'PromoCode']:
        """
        Validate promo code and return (discount_amount, promo_code_obj).
        Raises ValueError if invalid.
        """
        from apps.payments.models import PromoCode
        try:
            promo = PromoCode.objects.get(code=code.upper())
        except PromoCode.DoesNotExist:
            raise ValueError(f"Promo code '{code}' not found")

        if not promo.is_valid:
            raise ValueError(f"Promo code '{code}' is expired or inactive")

        if ride_price < promo.min_ride_price:
            raise ValueError(
                f"Minimum ride price for this promo is {promo.min_ride_price} UAH"
            )

        return PromoCodeService.calculate_discount(ride_price, promo), promo

    @staticmethod
    def calculate_discount(price: Decimal, promo: 'PromoCode') -> Decimal:
        """Calculate discount amount."""
        from apps.payments.models import PromoCode
        if promo.discount_type == PromoCode.DiscountType.PERCENTAGE:
            discount = price * promo.discount_percent / 100
        else:
            discount = promo.discount_amount

        if promo.max_discount:
            discount = min(discount, promo.max_discount)

        return min(discount, price)

    @staticmethod
    def apply_promo_code(code: str, ride_price: Decimal) -> tuple[Decimal, Decimal, 'PromoCode']:
        """Apply promo code, increment usage. Returns (discounted_price, discount, promo)."""
        discount, promo = PromoCodeService.validate_promo_code(code, ride_price)
        promo.usage_count += 1
        promo.save(update_fields=['usage_count'])
        final_price = max(ride_price - discount, Decimal('0'))
        return final_price, discount, promo


class RefundService:

    @staticmethod
    def create_refund(payment_id: str, amount: Decimal, reason: str) -> 'Refund':
        """Initiate refund for a payment."""
        from apps.payments.models import Refund
        with transaction.atomic():
            payment = Payment.objects.select_for_update().get(id=payment_id)

            if payment.status not in [Payment.Status.SUCCESS, Payment.Status.PARTIAL_REFUND]:
                raise ValueError(f"Cannot refund payment with status: {payment.status}")

            if amount > payment.amount:
                raise ValueError(f"Refund amount {amount} exceeds payment amount {payment.amount}")

            refund = Refund.objects.create(
                payment=payment,
                amount=amount,
                reason=reason,
                status='processing',
            )

        if payment.provider == 'cash':
            with transaction.atomic():
                refund.status = 'success'
                refund.processed_at = timezone.now()
                refund.provider_refund_id = f'cash_refund_{refund.id}'
                refund.save(update_fields=['status', 'processed_at', 'provider_refund_id'])
                payment.status = Payment.Status.REFUNDED
                payment.refunded_at = timezone.now()
                payment.save(update_fields=['status', 'refunded_at'])
        else:
            try:
                provider = get_payment_provider(payment.provider)
                result = provider.refund_payment(
                    payment.provider_transaction_id, amount
                )
                refund.provider_refund_id = result.get('refund_id', '')
                refund.save(update_fields=['provider_refund_id'])
            except Exception as e:
                refund.status = 'failed'
                refund.save(update_fields=['status'])
                logger.error(f"Refund failed: {e}")
                raise

        logger.info(f"Refund created: {refund.id} for payment {payment_id}")
        return refund

    @staticmethod
    def get_refund_status(refund_id: str) -> dict:
        """Get refund status."""
        from apps.payments.models import Refund
        refund = Refund.objects.get(id=refund_id)
        return {
            'id': str(refund.id),
            'status': refund.status,
            'amount': float(refund.amount),
            'reason': refund.reason,
            'processed_at': refund.processed_at,
        }
