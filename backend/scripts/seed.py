"""Seed plans, one admin, one customer. Safe to run repeatedly (idempotent get-or-create/update).

Run from the backend/ folder:  python -m scripts.seed
"""

import asyncio

from app.core.database import SessionLocal, engine
from app.core.security import hash_password
from app.models import Customer, Plan, User
from app.models.enums import BillingInterval, UserRole
from app.repositories.plan_repository import PlanRepository
from app.repositories.user_repository import UserRepository

# 5 Default SaaS Subscription Plans
# price_minor is in paise: 49900 = Rs 499.00
PLANS = [
    {"code": "free", "name": "Free", "price_minor": 0, "trial_days": 0},
    {"code": "starter", "name": "Starter", "price_minor": 49_900, "trial_days": 14},
    {"code": "pro", "name": "Pro", "price_minor": 149_900, "trial_days": 14},
    {"code": "business", "name": "Business", "price_minor": 499_900, "trial_days": 14},
    {"code": "enterprise", "name": "Enterprise", "price_minor": 1_499_900, "trial_days": 0},
]

ADMIN_EMAIL = "admin@billwise.com"
ADMIN_PASSWORD = "admin123"

CUSTOMER_EMAIL = "customer@billwise.com"
CUSTOMER_PASSWORD = "customer123"


async def seed() -> None:
    async with SessionLocal() as session:
        plans = PlanRepository(session)
        users = UserRepository(session)

        # 1. Seed Plans
        for data in PLANS:
            if await plans.get_by_code(data["code"]) is None:
                await plans.add(Plan(billing_interval=BillingInterval.MONTHLY, **data))

        # 2. Seed Admin User
        admin_user = await users.get_by_email(ADMIN_EMAIL)
        admin_hash = hash_password(ADMIN_PASSWORD)
        if admin_user is None:
            await users.add(
                User(email=ADMIN_EMAIL, hashed_password=admin_hash, role=UserRole.ADMIN)
            )
        else:
            admin_user.hashed_password = admin_hash

        # 3. Seed Customer User & Profile
        customer_user = await users.get_by_email(CUSTOMER_EMAIL)
        customer_hash = hash_password(CUSTOMER_PASSWORD)
        if customer_user is None:
            customer_user = await users.add(
                User(email=CUSTOMER_EMAIL, hashed_password=customer_hash, role=UserRole.CUSTOMER)
            )
        else:
            customer_user.hashed_password = customer_hash

        # Ensure Customer profile exists
        if await users.get_customer_by_user_id(customer_user.id) is None:
            await users.add_customer(Customer(user_id=customer_user.id, name="Demo Customer"))

        await session.commit()
    await engine.dispose()
    print("✅ Seed complete: 5 plans, 1 admin (admin123), 1 customer (customer123).")


if __name__ == "__main__":
    asyncio.run(seed())
