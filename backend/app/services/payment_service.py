import json
import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.payment_gateway import get_payment_gateway
from app.models import Payment
from app.models.enums import InvoiceStatus, PaymentStatus, SubscriptionStatus
from app.models.system import IdempotencyKey
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.payment_repository import PaymentRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.services.subscription_state_machine import can_transition


class WebhookSignatureVerificationError(Exception):
    pass


class PaymentService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.payments = PaymentRepository(session)
        self.invoices = InvoiceRepository(session)
        self.subscriptions = SubscriptionRepository(session)
        self.gateway = get_payment_gateway()

    async def create_payment_order_for_invoice(self, invoice_id: uuid.UUID) -> Payment:
        """Register an order with the payment gateway and persist a PENDING payment record."""
        invoice = await self.invoices.get_by_id(invoice_id)
        if not invoice:
            raise LookupError(f"Invoice {invoice_id} not found")

        if invoice.status == InvoiceStatus.PAID:
            raise ValueError(f"Invoice {invoice.number} is already paid")

        # 1. Create order on the gateway
        order_data = await self.gateway.create_order(
            amount_minor=invoice.total_minor,
            currency=invoice.currency,
            receipt=invoice.number,
        )

        # 2. Persist Payment attempt record
        payment = Payment(
            invoice_id=invoice.id,
            amount_minor=invoice.total_minor,
            currency=invoice.currency,
            gateway="razorpay",
            gateway_order_id=order_data["id"],
            status=PaymentStatus.PENDING,
        )
        await self.payments.add(payment)
        await self.session.commit()
        return payment

    async def process_webhook_event(self, raw_body: bytes, signature: str) -> dict:
        """
        Securely handle Razorpay webhook events:
        1. Verify HMAC-SHA256 signature
        2. Idempotent check (skip duplicates)
        3. Transition payment, invoice, and subscription state
        """
        # 1. Cryptographic signature check
        if not self.gateway.verify_webhook_signature(raw_body, signature):
            raise WebhookSignatureVerificationError("Invalid webhook signature")

        event_data = json.loads(raw_body.decode("utf-8"))
        event_id = event_data.get("id") or f"evt_{uuid.uuid4().hex[:12]}"
        event_name = event_data.get("event")

        # 2. Check if event was already processed (Idempotency)
        stmt = select(IdempotencyKey).where(IdempotencyKey.key == event_id)
        result = await self.session.execute(stmt)
        if result.scalar_one_or_none():
            return {"status": "ignored", "reason": "duplicate_event", "event_id": event_id}

        # 3. Handle Payment Captured (Successful payment)
        if event_name == "payment.captured":
            payload_entity = event_data["payload"]["payment"]["entity"]
            order_id = payload_entity.get("order_id")
            gateway_payment_id = payload_entity.get("id")

            payment = await self.payments.get_by_gateway_order_id(order_id)
            if payment and payment.status != PaymentStatus.SUCCEEDED:
                # Update Payment
                payment.status = PaymentStatus.SUCCEEDED
                payment.gateway_payment_id = gateway_payment_id

                # Update Invoice
                invoice = await self.invoices.get_by_id(payment.invoice_id)
                if invoice:
                    now = datetime.now(timezone.utc)
                    invoice.status = InvoiceStatus.PAID
                    invoice.paid_at = now

                    # Transition Subscription to ACTIVE if needed
                    subscription = await self.subscriptions.get(invoice.subscription_id)
                    if subscription and subscription.status in (
                        SubscriptionStatus.TRIALING,
                        SubscriptionStatus.PAST_DUE,
                    ):
                        if can_transition(subscription.status, SubscriptionStatus.ACTIVE):
                            subscription.status = SubscriptionStatus.ACTIVE

        # 4. Handle Payment Failed
        elif event_name == "payment.failed":
            payload_entity = event_data["payload"]["payment"]["entity"]
            order_id = payload_entity.get("order_id")
            error_desc = payload_entity.get("error_description", "Payment declined")

            payment = await self.payments.get_by_gateway_order_id(order_id)
            if payment:
                payment.status = PaymentStatus.FAILED
                payment.failure_reason = error_desc

                # Move active subscription to PAST_DUE
                invoice = await self.invoices.get_by_id(payment.invoice_id)
                if invoice:
                    subscription = await self.subscriptions.get(invoice.subscription_id)
                    if subscription and subscription.status == SubscriptionStatus.ACTIVE:
                        if can_transition(subscription.status, SubscriptionStatus.PAST_DUE):
                            subscription.status = SubscriptionStatus.PAST_DUE

        # 5. Record event in IdempotencyKey table so duplicates are caught
        idem_record = IdempotencyKey(
            key=event_id,
            request_path="/api/webhooks/razorpay",
            request_hash="webhook_verified",
            response_status=200,
            response_body={"processed": True, "event": event_name},
        )
        self.session.add(idem_record)
        await self.session.commit()

        return {"status": "processed", "event_id": event_id, "event": event_name}