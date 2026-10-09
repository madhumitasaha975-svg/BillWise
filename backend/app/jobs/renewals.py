from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import SessionLocal
from app.models import Subscription
from app.models.enums import SubscriptionStatus
from app.services.subscription_service import SubscriptionService


async def process_due_renewals(reference_time: datetime | None = None) -> int:
    """
    Scans for all active subscriptions whose current_period_end <= reference_time
    and executes their renewal. Returns the count of renewed subscriptions.
    """
    now = reference_time or datetime.now(timezone.utc)
    renewed_count = 0

    async with SessionLocal() as session:
        # 1. Query all active subscriptions that are due for renewal
        stmt = (
            select(Subscription.id)
            .where(
                Subscription.status == SubscriptionStatus.ACTIVE,
                Subscription.current_period_end <= now,
            )
        )
        result = await session.execute(stmt)
        due_subscription_ids = result.scalars().all()

        # 2. Renew each due subscription
        service = SubscriptionService(session)
        for sub_id in due_subscription_ids:
            sub, invoice = await service.renew_subscription(sub_id, effective_at=now)
            if invoice:
                renewed_count += 1
                print(f"🔄 Renewed subscription {sub.id}: generated invoice {invoice.number}")

    return renewed_count