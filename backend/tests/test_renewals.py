from datetime import datetime, timedelta, timezone
import pytest
from app.core.database import SessionLocal
from app.jobs.renewals import process_due_renewals
from app.models.enums import LineItemKind, SubscriptionStatus
from app.repositories.user_repository import UserRepository
from app.services.subscription_service import SubscriptionService


@pytest.mark.anyio
async def test_subscription_automatic_renewal():
    """
    Test the renewal engine:
    1. Customer creates a subscription.
    2. We simulate time jumping forward past current_period_end.
    3. process_due_renewals runs.
    4. Asserts period rolled forward and renewal invoice with BASE_FEE was generated.
    """
    async with SessionLocal() as session:
        users = UserRepository(session)
        user = await users.get_by_email("customer@billwise.test")
        assert user is not None
        customer = await users.get_customer_by_user_id(user.id)

        service = SubscriptionService(session)
        sub = await service.create_subscription(customer.id, "starter")
        await service.change_status(sub.id, SubscriptionStatus.ACTIVE)
        sub_id = sub.id
        old_end = sub.current_period_end

    # Simulate running the background job 1 hour after the period expired
    future_time = old_end + timedelta(hours=1)
    renewed_count = await process_due_renewals(reference_time=future_time)
    assert renewed_count >= 1

    # Verify updated subscription in database
    async with SessionLocal() as session:
        service = SubscriptionService(session)
        renewed_sub = await service.get_subscription(sub_id)
        assert renewed_sub.current_period_start == old_end
        assert renewed_sub.current_period_end > old_end
        print(f"\n✅ Subscription period advanced to: {renewed_sub.current_period_end}")

        # Verify renewal invoice
        invoices = await service.invoices.get_by_subscription_id(sub_id)
        latest_inv = invoices[0]
        assert latest_inv.line_items[0].kind == LineItemKind.BASE_FEE
        print(f"✅ Renewal invoice generated: {latest_inv.number} for Rs {latest_inv.total_minor / 100:.2f}")