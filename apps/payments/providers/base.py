"""
Abstract base class for payment providers.
"""

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Dict, Any


class PaymentProvider(ABC):
    """Abstract base class for payment providers."""

    @abstractmethod
    def create_payment(
        self,
        amount: Decimal,
        currency: str,
        description: str,
        order_id: str,
        callback_url: str,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Create payment. Returns {payment_url, transaction_id, data}."""
        pass

    @abstractmethod
    def verify_payment(self, transaction_id: str) -> Dict[str, Any]:
        """Verify payment status. Returns {status, amount, currency}."""
        pass

    @abstractmethod
    def refund_payment(self, transaction_id: str, amount: Decimal) -> Dict[str, Any]:
        """Initiate refund. Returns {refund_id, status}."""
        pass

    @abstractmethod
    def verify_callback(self, data: Dict[str, Any], signature: str) -> bool:
        """Verify callback signature from provider."""
        pass
