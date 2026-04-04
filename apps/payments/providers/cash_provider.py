"""
Cash payment provider (no actual processing needed).
"""

import logging
from decimal import Decimal
from typing import Any, Dict

from apps.payments.providers.base import PaymentProvider

logger = logging.getLogger(__name__)


class CashProvider(PaymentProvider):
    """Cash payment provider (no actual processing needed)."""

    def create_payment(
        self,
        amount: Decimal,
        currency: str,
        description: str,
        order_id: str,
        callback_url: str,
        **kwargs: Any
    ) -> Dict[str, Any]:
        return {
            'payment_url': None,
            'transaction_id': f'cash_{order_id}',
            'data': {'method': 'cash'},
        }

    def verify_payment(self, transaction_id: str) -> Dict[str, Any]:
        return {'status': 'success', 'transaction_id': transaction_id}

    def refund_payment(self, transaction_id: str, amount: Decimal) -> Dict[str, Any]:
        return {
            'refund_id': f'refund_{transaction_id}',
            'status': 'success',
        }

    def verify_callback(self, data: Dict[str, Any], signature: str) -> bool:
        return True
