"""Seed plans, one admin, one customer. Safe to run repeatedly (get-or-create).

Run from the backend/ folder:  python -m scripts.seed

NOTE: passwords are a placeholder until Module 2 adds real hashing. These two
accounts cannot log in yet; Module 2 step 1 will re-seed with real bcrypt hashes.
"""

import asyncio

from app.core.database import SessionLocal, engine
from app.models import Customer, Plan, User
from app.models.enums import BillingInterval, UserRole
from app.repositories.plan_repository import PlanRepository
from app.repositories.user_repository import UserRepository

PLACEHOLDER_HASH = "!placeholder-replaced-in-module-2"

# price_minor is in paise: 49900 = Rs 499.00
PLANS = [
    {"code": "free", "name": "Free", "price_minor": 0, "trial_days": 0},
    {"code": "starter", "name": "Starter", "price_minor": 49_900, "trial_days": 14},
    {"code": "pro", "name": "Pro", "price_minor": 149_900, "trial_days": 14},
    {"code": "business", "name": "Business", "price_minor": 499_900, "trial_days": 14},
    {"code": "enterprise", "name": "Enterprise", "price_minor": 1_499_900, "trial_days": 0},
]

ADMIN_EMAIL = "admin@billwise.test"
CUSTOMER_EMAIL = "customer@billwise.test"


async def seed() -> None:
    async with SessionLocal() as session:
        plans = PlanRepository(session)
        users = UserRepository(session)

        for data in PLANS:
            if await plans.get_by_code(data["code"]) is None:
                await plans.add(Plan(billing_interval=BillingInterval.MONTHLY, **data))

        if await users.get_by_email(ADMIN_EMAIL) is None:
            await users.add(
                User(email=ADMIN_EMAIL, hashed_password=PLACEHOLDER_HASH, role=UserRole.ADMIN)
            )

        customer_user = await users.get_by_email(CUSTOMER_EMAIL)
        if customer_user is None:
            customer_user = await users.add(
                User(email=CUSTOMER_EMAIL, hashed_password=PLACEHOLDER_HASH, role=UserRole.CUSTOMER)
            )
        if await users.get_customer_by_user_id(customer_user.id) is None:
            await users.add_customer(Customer(user_id=customer_user.id, name="Demo Customer"))

        await session.commit()
    await engine.dispose()
    print("Seed complete: 5 plans, 1 admin, 1 customer.")


if __name__ == "__main__":
    asyncio.run(seed())
