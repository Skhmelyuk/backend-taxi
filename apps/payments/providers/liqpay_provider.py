"""
LiqPay payment provider integration.
"""

import base64
import hashlib
import json
import logging
from decimal import Decimal
from typing import Dict, Any

from django.conf import settings

from apps.payments.providers.base import PaymentProvider

logger = logging.getLogger(__name__)


class LiqPayProvider(PaymentProvider):
    """LiqPay payment provider integration."""

    def __init__(self) -> None:
        self.public_key = settings.LIQPAY_PUBLIC_KEY
        self.private_key = settings.LIQPAY_PRIVATE_KEY
        self.sandbox = getattr(settings, 'LIQPAY_SANDBOX', True)

    def _sign(self, data: str) -> str:
        sign_str = self.private_key + data + self.private_key
        return base64.b64encode(hashlib.sha1(sign_str.encode()).digest()).decode()

    def _encode_data(self, params: dict) -> str:
        return base64.b64encode(json.dumps(params).encode()).decode()

    def create_payment(
        self,
        amount: Decimal,
        currency: str,
        description: str,
        order_id: str,
        callback_url: str,
        **kwargs: Any
    ) -> Dict[str, Any]:
        params = {
            'version': 3,
            'public_key': self.public_key,
            'action': 'pay',
            'amount': str(amount),
            'currency': currency,
            'description': description,
            'order_id': order_id,
            'result_url': callback_url,
            'server_url': callback_url,
        }
        if self.sandbox:
            params['sandbox'] = 1

        data = self._encode_data(params)
        signature = self._sign(data)

        payment_url = f"https://www.liqpay.ua/api/3/checkout?data={data}&signature={signature}"

        return {
            'payment_url': payment_url,
            'transaction_id': order_id,
            'data': {'data': data, 'signature': signature},
        }

    def verify_payment(self, transaction_id: str) -> Dict[str, Any]:
        logger.info("Verifying LiqPay payment: %s", transaction_id)
        return {'status': 'unknown', 'transaction_id': transaction_id}

    def refund_payment(self, transaction_id: str, amount: Decimal) -> Dict[str, Any]:
        logger.info(
            "Refunding LiqPay payment: %s, amount: %s",
            transaction_id,
            amount,
        )
        return {'refund_id': None, 'status': 'processing'}

    def verify_callback(self, data: Dict[str, Any], signature: str) -> bool:
        try:
            expected = self._sign(data.get('data', ''))
            return expected == signature
        except Exception:
            return False
