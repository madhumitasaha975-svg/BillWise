from datetime import datetime, timedelta, timezone
from app.database.connection import SessionLocal
import app.models.core as models

def seed_database():
    db = SessionLocal()
    try:
        # 1. Create a Dummy Customer
        customer = models.Customer(
            email="test_billing@example.com",
            hashed_password="fakehash"
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)

        # 2. Create a Dummy Plan
        plan = models.Plan(
            name="Test Pro Plan",
            price=49.99,
            billing_interval="monthly"
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)

        # 3. Create an ACTIVE subscription that expired 5 minutes ago!
        now = datetime.now(timezone.utc)
        subscription = models.Subscription(
            customer_id=customer.id,
            plan_id=plan.id,
            status=models.SubscriptionState.active,
            current_period_start=now - timedelta(days=30),
            current_period_end=now - timedelta(minutes=5) # Past due!
        )
        db.add(subscription)
        db.commit()
        db.refresh(subscription)

        print("\n" + "="*40)
        print("✅ DATABASE SEEDED SUCCESSFULLY")
        print(f"Customer: {customer.email}")
        print(f"Plan: {plan.name} (${plan.price})")
        print(f"Subscription ID: {subscription.id}")
        print("⏳ Status: ACTIVE but PAST DUE (Expired 5 mins ago)")
        print("="*40 + "\n")

    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()