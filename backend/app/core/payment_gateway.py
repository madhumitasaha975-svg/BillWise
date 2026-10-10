import hashlib
import hmac
import uuid
from typing import Protocol
from app.core.config import settings


class PaymentGateway(Protocol):
    """Protocol defining common gateway operations."""

    async def create_order(self, amount_minor: int, currency: str, receipt: str) -> dict:
        ...

    def verify_webhook_signature(self, body: bytes, signature: str) -> bool:
        ...


def compute_hmac_signature(body: bytes, secret: str) -> str:
    """Compute HMAC-SHA256 signature for a raw body."""
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


class FakePaymentGateway:
    """
    Offline mock gateway simulator for local development and automated testing.
    Generates realistic order IDs and validates signatures using standard HMAC-SHA256.
    """

    async def create_order(self, amount_minor: int, currency: str, receipt: str) -> dict:
        order_id = f"order_fake_{uuid.uuid4().hex[:14]}"
        return {
            "id": order_id,
            "amount": amount_minor,
            "currency": currency,
            "receipt": receipt,
            "status": "created",
        }

    def verify_webhook_signature(self, body: bytes, signature: str) -> bool:
        expected = compute_hmac_signature(body, settings.razorpay_webhook_secret)
        return hmac.compare_digest(expected, signature)


class RazorpayGateway:
    """Live integration with Razorpay test/production mode."""

    def __init__(self):
        import razorpay
        self.client = razorpay.Client(
            auth=(settings.razorpay_key_id, settings.razorpay_key_secret)
        )

    async def create_order(self, amount_minor: int, currency: str, receipt: str) -> dict:
        import asyncio
        data = {
            "amount": amount_minor,
            "currency": currency,
            "receipt": receipt,
            "payment_capture": 1,
        }
        # Run sync SDK network call in a background thread to prevent blocking asyncio
        return await asyncio.to_thread(self.client.order.create, data=data)

    def verify_webhook_signature(self, body: bytes, signature: str) -> bool:
        expected = compute_hmac_signature(body, settings.razorpay_webhook_secret)
        return hmac.compare_digest(expected, signature)


def get_payment_gateway() -> PaymentGateway:
    """Factory: returns FakePaymentGateway if fake_gateway_mode is enabled, else Razorpay."""
    if settings.fake_gateway_mode:
        return FakePaymentGateway()
    return RazorpayGateway()