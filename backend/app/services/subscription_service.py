import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.billing_math import calculate_proration
from app.models import Invoice, InvoiceLineItem, Subscription
from app.models.enums import (
    BillingInterval,
    InvoiceStatus,
    LineItemKind,
    SubscriptionStatus,
)
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.plan_repository import PlanRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.services.subscription_state_machine import assert_transition


class PlanNotFoundError(Exception):
    pass


class InvalidSubscriptionStateError(Exception):
    pass


class SubscriptionService:
    """Business logic for subscriptions and proration. Talks to DB only via repositories."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.subscriptions = SubscriptionRepository(session)
        self.plans = PlanRepository(session)
        self.invoices = InvoiceRepository(session)

    async def create_subscription(self, customer_id: uuid.UUID, plan_code: str) -> Subscription:
        plan = await self.plans.get_by_code(plan_code)
        if plan is None or not plan.is_active:
            raise PlanNotFoundError(plan_code)

        now = datetime.now(timezone.utc)
        has_trial = plan.trial_days > 0
        from datetime import timedelta
        period_days = 365 if plan.billing_interval == BillingInterval.YEARLY else 30

        subscription = Subscription(
            customer_id=customer_id,
            plan_id=plan.id,
            status=SubscriptionStatus.TRIALING if has_trial else SubscriptionStatus.ACTIVE,
            trial_ends_at=now + timedelta(days=plan.trial_days) if has_trial else None,
            current_period_start=now,
            current_period_end=now + timedelta(days=plan.trial_days if has_trial else period_days),
        )
        await self.subscriptions.add(subscription)
        await self.session.commit()
        return await self.subscriptions.get(subscription.id)

    async def get_subscription(self, subscription_id: uuid.UUID) -> Subscription | None:
        return await self.subscriptions.get(subscription_id)

    async def change_status(
        self, subscription_id: uuid.UUID, target: SubscriptionStatus
    ) -> Subscription:
        subscription = await self.subscriptions.get(subscription_id)
        if subscription is None:
            raise LookupError(f"Subscription {subscription_id} not found")
        assert_transition(subscription.status, target)
        subscription.status = target
        if target == SubscriptionStatus.CANCELLED:
            subscription.cancelled_at = datetime.now(timezone.utc)
        await self.session.commit()
        return subscription

    async def change_plan(
        self,
        subscription_id: uuid.UUID,
        new_plan_code: str,
        effective_at: datetime | None = None,
    ) -> tuple[Subscription, Invoice | None]:
        """
        Switch subscription to a new plan mid-cycle.
        Calculates proration, generates an itemized invoice, and updates the plan.
        """
        subscription = await self.subscriptions.get(subscription_id)
        if subscription is None:
            raise LookupError(f"Subscription {subscription_id} not found")

        if subscription.status not in (SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING):
            raise InvalidSubscriptionStateError(
                f"Cannot change plan for subscription in '{subscription.status}' status"
            )

        new_plan = await self.plans.get_by_code(new_plan_code)
        if new_plan is None or not new_plan.is_active:
            raise PlanNotFoundError(new_plan_code)

        if new_plan.id == subscription.plan_id:
            raise ValueError(f"Subscription is already on plan '{new_plan_code}'")

        old_plan = subscription.plan
        now = effective_at or datetime.now(timezone.utc)
        invoice: Invoice | None = None

        # Only calculate proration and bill if the subscription is actively paying
        if subscription.status == SubscriptionStatus.ACTIVE:
            calc = calculate_proration(
                old_plan_name=old_plan.name,
                old_plan_price_minor=old_plan.price_minor,
                new_plan_name=new_plan.name,
                new_plan_price_minor=new_plan.price_minor,
                period_start=subscription.current_period_start,
                period_end=subscription.current_period_end,
                change_at=now,
            )

            # Generate Invoice with itemized line items
            invoice_number = await self.invoices.generate_invoice_number()
            invoice = Invoice(
                number=invoice_number,
                customer_id=subscription.customer_id,
                subscription_id=subscription.id,
                status=InvoiceStatus.PAID if calc.net_amount_due_minor <= 0 else InvoiceStatus.OPEN,
                currency="INR",
                subtotal_minor=calc.net_amount_due_minor,
                tax_minor=0,
                total_minor=max(0, calc.net_amount_due_minor),
                due_at=now,
            )

            line_items = [
                InvoiceLineItem(
                    kind=(
                        LineItemKind.PRORATION_CHARGE
                        if item.amount_minor >= 0
                        else LineItemKind.PRORATION_CREDIT
                    ),
                    description=item.description,
                    amount_minor=item.amount_minor,
                )
                for item in calc.line_items
            ]

            await self.invoices.add(invoice, line_items)

                    # Update subscription to the new plan
        subscription.plan_id = new_plan.id
        subscription.plan = new_plan
        await self.session.commit()

        # Reload subscription and invoice with eager-loaded relationships
        updated_sub = await self.subscriptions.get(subscription.id)
        if invoice is not None:
            invoice = await self.invoices.get_by_id(invoice.id)

        return updated_sub, invoice
    

    async def renew_subscription(
        self,
        subscription_id: uuid.UUID,
        effective_at: datetime | None = None,
    ) -> tuple[Subscription, Invoice | None]:
        """
        Process end-of-period renewal:
        - If cancel_at_period_end is True, marks subscription CANCELLED.
        - Otherwise, rolls the billing period forward and generates a renewal invoice.
        """
        subscription = await self.subscriptions.get(subscription_id)
        if subscription is None:
            raise LookupError(f"Subscription {subscription_id} not found")

        if subscription.status != SubscriptionStatus.ACTIVE:
            return subscription, None

        now = effective_at or datetime.now(timezone.utc)

        # 1. Handle scheduled cancellation
        if subscription.cancel_at_period_end:
            subscription.status = SubscriptionStatus.CANCELLED
            subscription.cancelled_at = now
            await self.session.commit()
            return subscription, None

        # 2. Advance the period window (e.g. +30 days or +365 days)
        from datetime import timedelta
        period_days = 365 if subscription.plan.billing_interval == BillingInterval.YEARLY else 30
        new_start = subscription.current_period_end
        new_end = new_start + timedelta(days=period_days)

        subscription.current_period_start = new_start
        subscription.current_period_end = new_end

        # 3. Generate the Renewal Invoice
        invoice_number = await self.invoices.generate_invoice_number()
        invoice = Invoice(
            number=invoice_number,
            customer_id=subscription.customer_id,
            subscription_id=subscription.id,
            status=InvoiceStatus.OPEN,
            currency="INR",
            subtotal_minor=subscription.plan.price_minor,
            tax_minor=0,
            total_minor=subscription.plan.price_minor,
            due_at=new_start,
        )

        line_items = [
            InvoiceLineItem(
                kind=LineItemKind.BASE_FEE,
                description=f"Renewal fee for {subscription.plan.name} plan",
                amount_minor=subscription.plan.price_minor,
            )
        ]

        await self.invoices.add(invoice, line_items)
        await self.session.commit()

        # Eagerly reload
        updated_sub = await self.subscriptions.get(subscription.id)
        reloaded_invoice = await self.invoices.get_by_id(invoice.id)
        return updated_sub, reloaded_invoice