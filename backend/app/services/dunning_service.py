import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.payment_gateway import get_payment_gateway
from app.models.enums import InvoiceStatus, PaymentStatus, SubscriptionStatus
from app.models.invoice import Invoice
from app.models.payment import Payment
from app.models.subscription import Subscription
from app.models.system import AuditLog
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.payment_repository import PaymentRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.services.subscription_state_machine import assert_transition, can_transition

MAX_DUNNING_ATTEMPTS = 3
RETRY_INTERVAL_DAYS = [1, 3, 5]


class DunningService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.invoices = InvoiceRepository(session)
        self.subscriptions = SubscriptionRepository(session)
        self.payments = PaymentRepository(session)
        self.gateway = get_payment_gateway()

    async def execute_dunning_retry(
        self,
        invoice_id: uuid.UUID,
        simulate_success: bool = False,
        failure_reason: str = "Card declined on automated retry",
    ) -> dict:
        """
        Executes a dunning retry attempt for an open invoice belonging to a PAST_DUE subscription.
        
        - If attempts >= MAX_DUNNING_ATTEMPTS:
            Exhausts retries and transitions subscription PAST_DUE -> SUSPENDED.
        - If retry succeeds:
            Marks invoice PAID, transitions subscription PAST_DUE -> ACTIVE.
        - If retry fails:
            Records failed payment attempt and increments attempt counter. If now at max, suspends.
        """
        invoice = await self.invoices.get_by_id(invoice_id)
        if not invoice:
            raise LookupError(f"Invoice {invoice_id} not found")

        if invoice.status != InvoiceStatus.OPEN:
            return {
                "status": "skipped",
                "reason": f"Invoice is already {invoice.status.value}",
                "invoice_number": invoice.number,
            }

        subscription = await self.subscriptions.get(invoice.subscription_id)
        if not subscription:
            raise LookupError(f"Subscription {invoice.subscription_id} not found")

        # Fetch all existing payment attempts for this invoice
        existing_payments = await self.payments.get_by_invoice_id(invoice.id)
        latest_attempt_number = max(
            [p.attempt_number for p in existing_payments], default=0
        )

        # 1. Check if retries are already exhausted before running a new attempt
        if latest_attempt_number >= MAX_DUNNING_ATTEMPTS:
            if subscription.status == SubscriptionStatus.PAST_DUE:
                assert_transition(subscription.status, SubscriptionStatus.SUSPENDED)
                subscription.status = SubscriptionStatus.SUSPENDED

                audit_entry = AuditLog(
                    action="dunning.exhausted_suspended",
                    entity_type="subscription",
                    entity_id=str(subscription.id),
                    details={
                        "invoice_id": str(invoice.id),
                        "invoice_number": invoice.number,
                        "total_attempts": latest_attempt_number,
                    },
                )
                self.session.add(audit_entry)
                await self.session.commit()

            return {
                "status": "exhausted",
                "subscription_status": subscription.status.value,
                "invoice_number": invoice.number,
                "attempts": latest_attempt_number,
            }

        # 2. Execute the next attempt
        next_attempt_number = latest_attempt_number + 1

        # Register order with gateway
        order_data = await self.gateway.create_order(
            amount_minor=invoice.total_minor,
            currency=invoice.currency,
            receipt=f"{invoice.number}-R{next_attempt_number}",
        )

        payment_attempt = Payment(
            invoice_id=invoice.id,
            amount_minor=invoice.total_minor,
            currency=invoice.currency,
            gateway="razorpay",
            gateway_order_id=order_data["id"],
            status=PaymentStatus.SUCCEEDED if simulate_success else PaymentStatus.FAILED,
            attempt_number=next_attempt_number,
            failure_reason=None if simulate_success else failure_reason,
        )
        await self.payments.add(payment_attempt)

        # 3. Handle Outcome
        if simulate_success:
            # Payment recovered!
            now = datetime.now(timezone.utc)
            invoice.status = InvoiceStatus.PAID
            invoice.paid_at = now

            if subscription.status in (SubscriptionStatus.PAST_DUE, SubscriptionStatus.SUSPENDED):
                if can_transition(subscription.status, SubscriptionStatus.ACTIVE):
                    subscription.status = SubscriptionStatus.ACTIVE

            audit_entry = AuditLog(
                action="dunning.recovered",
                entity_type="subscription",
                entity_id=str(subscription.id),
                details={
                    "invoice_id": str(invoice.id),
                    "invoice_number": invoice.number,
                    "recovered_on_attempt": next_attempt_number,
                    "payment_id": str(payment_attempt.id),
                },
            )
            self.session.add(audit_entry)
            await self.session.commit()

            return {
                "status": "recovered",
                "subscription_status": subscription.status.value,
                "invoice_number": invoice.number,
                "attempt": next_attempt_number,
            }

        else:
            # Retry failed
            # If we reached max attempts on this failed try, suspend immediately!
            if next_attempt_number >= MAX_DUNNING_ATTEMPTS:
                if subscription.status == SubscriptionStatus.PAST_DUE:
                    assert_transition(subscription.status, SubscriptionStatus.SUSPENDED)
                    subscription.status = SubscriptionStatus.SUSPENDED

                audit_entry = AuditLog(
                    action="dunning.exhausted_suspended",
                    entity_type="subscription",
                    entity_id=str(subscription.id),
                    details={
                        "invoice_id": str(invoice.id),
                        "invoice_number": invoice.number,
                        "total_attempts": next_attempt_number,
                        "failure_reason": failure_reason,
                    },
                )
                self.session.add(audit_entry)
                await self.session.commit()

                return {
                    "status": "exhausted",
                    "subscription_status": subscription.status.value,
                    "invoice_number": invoice.number,
                    "attempt": next_attempt_number,
                }

            # Still in grace period
            audit_entry = AuditLog(
                action="dunning.retry_failed",
                entity_type="subscription",
                entity_id=str(subscription.id),
                details={
                    "invoice_id": str(invoice.id),
                    "invoice_number": invoice.number,
                    "attempt": next_attempt_number,
                    "failure_reason": failure_reason,
                },
            )
            self.session.add(audit_entry)
            await self.session.commit()

            return {
                "status": "retry_failed",
                "subscription_status": subscription.status.value,
                "invoice_number": invoice.number,
                "attempt": next_attempt_number,
            }
