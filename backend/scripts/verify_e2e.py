"""TEMPORARY end-to-end check for Module 1. Run after migrate + seed:

    python -m scripts.verify_e2e

Creates a subscription for the seeded customer, reads it back, then proves the
state machine blocks an illegal change against the real database.
"""

import asyncio

from app.core.database import SessionLocal, engine
from app.models.enums import SubscriptionStatus
from app.repositories.user_repository import UserRepository
from app.services.subscription_service import SubscriptionService
from app.services.subscription_state_machine import IllegalTransitionError


async def main() -> None:
    async with SessionLocal() as session:
        user = await UserRepository(session).get_by_email("customer@billwise.test")
        assert user is not None, "Run `python -m scripts.seed` first"
        customer = await UserRepository(session).get_customer_by_user_id(user.id)

        service = SubscriptionService(session)
        created = await service.create_subscription(customer.id, "pro")
        print(f"CREATED  id={created.id} plan={created.plan.code} status={created.status.value}")

        fetched = await service.get_subscription(created.id)
        assert fetched is not None and fetched.id == created.id
        print(f"READ     status={fetched.status.value} period_end={fetched.current_period_end:%Y-%m-%d}")
        assert fetched.current_period_end.tzinfo is not None, "datetime must be timezone-aware"

        await service.change_status(created.id, SubscriptionStatus.ACTIVE)
        print("MOVED    trialing -> active  (legal)")

        try:
            await service.change_status(created.id, SubscriptionStatus.SUSPENDED)
        except IllegalTransitionError as exc:
            print(f"BLOCKED  {exc}")
        else:
            raise AssertionError("active -> suspended should have been blocked")

    await engine.dispose()
    print("\nModule 1 end-to-end check PASSED")


if __name__ == "__main__":
    asyncio.run(main())
