"""
Factory for payment provider instances.
"""

from apps.payments.providers.base import PaymentProvider
from apps.payments.providers.liqpay_provider import LiqPayProvider
from apps.payments.providers.cash_provider import CashProvider


def get_payment_provider(provider_name: str) -> PaymentProvider:
    """Get payment provider instance by name."""
    providers: dict[str, type[PaymentProvider]] = {
        'liqpay': LiqPayProvider,
        'cash': CashProvider,
    }
    provider_class = providers.get(provider_name)
    if not provider_class:
        raise ValueError(f"Unknown payment provider: {provider_name}")
    return provider_class()
