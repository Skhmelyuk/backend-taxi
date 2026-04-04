import factory
from factory.django import DjangoModelFactory
from decimal import Decimal
from apps.payments.models import Payment, PromoCode
from apps.users.tests.factories import UserFactory
from apps.rides.tests.factories import CompletedRideFactory


class PaymentFactory(DjangoModelFactory):
    """Factory for Payment model. Creates a successful cash payment by default."""
    class Meta:
        model = Payment

    ride = factory.SubFactory(CompletedRideFactory)
    user = factory.LazyAttribute(lambda o: o.ride.user)
    amount = Decimal('115.0')
    currency = 'UAH'
    status = Payment.Status.SUCCESS
    payment_method = Payment.PaymentMethod.CASH
    provider = Payment.Provider.CASH
    provider_transaction_id = factory.Sequence(lambda n: f'cash_{n:010d}')
    description = 'Test payment'


class PendingPaymentFactory(PaymentFactory):
    """Factory for a pending payment."""
    status = Payment.Status.PENDING
    provider = Payment.Provider.LIQPAY
    payment_method = Payment.PaymentMethod.CARD
    provider_transaction_id = None


class PromoCodeFactory(DjangoModelFactory):
    """Factory for PromoCode model."""
    class Meta:
        model = PromoCode

    code = factory.Sequence(lambda n: f'PROMO{n:04d}')
    discount_percent = Decimal('10.0')
    is_active = True