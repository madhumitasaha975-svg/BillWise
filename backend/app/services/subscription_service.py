import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Subscription
from app.models.enums import BillingInterval, SubscriptionStatus
from app.repositories.plan_repository import PlanRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.services.subscription_state_machine import assert_transition


class PlanNotFoundError(Exception):
    pass


class SubscriptionService:
    """Business logic for subscriptions. Talks to the DB only through repositories."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.subscriptions = SubscriptionRepository(session)
        self.plans = PlanRepository(session)

    async def create_subscription(self, customer_id: uuid.UUID, plan_code: str) -> Subscription:
        plan = await self.plans.get_by_code(plan_code)
        if plan is None or not plan.is_active:
            raise PlanNotFoundError(plan_code)

        now = datetime.now(UTC)
        has_trial = plan.trial_days > 0
        period_days = 365 if plan.billing_interval == BillingInterval.YEARLY else 30
        # Module 3 replaces this simple "+30 days" with real calendar-month logic.
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
        assert_transition(subscription.status, target)  # raises if illegal
        subscription.status = target
        if target == SubscriptionStatus.CANCELLED:
            subscription.cancelled_at = datetime.now(UTC)
        await self.session.commit()
        return subscription
