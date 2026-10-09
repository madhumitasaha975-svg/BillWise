from datetime import datetime, timedelta, timezone
import pytest
from app.core.billing_math import calculate_proration
from app.core.database import SessionLocal
from app.models.enums import LineItemKind, SubscriptionStatus
from app.repositories.user_repository import UserRepository
from app.services.subscription_service import SubscriptionService


def test_proration_formula_hand_calculated():
    """
    Test proration math with hand-calculated expected values.
    Cycle: 30 days. Starter: Rs 1500 (150,000 paise). Pro: Rs 3000 (300,000 paise).
    Upgrade at day 10 -> 20 days remaining (2/3 of cycle).
    Unused Starter: 150000 * (20/30) = 100000 paise.
    Remaining Pro:  300000 * (20/30) = 200000 paise.
    Net Due:        200000 - 100000  = 100000 paise.
    """
    start = datetime(2026, 10, 1, 0, 0, 0, tzinfo=timezone.utc)
    end = start + timedelta(days=30)
    change = start + timedelta(days=10)

    res = calculate_proration(
        old_plan_name="Starter",
        old_plan_price_minor=150000,
        new_plan_name="Pro",
        new_plan_price_minor=300000,
        period_start=start,
        period_end=end,
        change_at=change,
    )

    assert res.unused_credit_minor == 100000
    assert res.remaining_charge_minor == 200000
    assert res.net_amount_due_minor == 100000
    assert len(res.line_items) == 2


@pytest.mark.anyio
async def test_subscription_change_plan_end_to_end():
    """
    Test mid-cycle plan upgrade in PostgreSQL:
    1. Customer creates a subscription.
    2. Customer upgrades from Starter to Pro.
    3. Verifies DB updates plan_id and generates proration invoice with line items.
    """
    async with SessionLocal() as session:
        # Get customer user from seeds
        users = UserRepository(session)
        user = await users.get_by_email("customer@billwise.test")
        assert user is not None, "Run seed first"
        customer = await users.get_customer_by_user_id(user.id)

        service = SubscriptionService(session)

        # 1. Create Starter subscription (active, no trial)
        sub = await service.create_subscription(customer.id, "starter")
        await service.change_status(sub.id, SubscriptionStatus.ACTIVE)

        # 2. Upgrade to Pro mid-cycle (simulate 10 days into 30-day period)
        change_date = sub.current_period_start + timedelta(days=10)
        updated_sub, invoice = await service.change_plan(
            subscription_id=sub.id,
            new_plan_code="pro",
            effective_at=change_date,
        )

        # 3. Assert plan changed
        assert updated_sub.plan.code == "pro"
        print(f"\n✅ Subscription upgraded to: {updated_sub.plan.name}")

        # 4. Assert invoice and line items were created in DB
        assert invoice is not None
        assert invoice.number.startswith("INV-")
        assert len(invoice.line_items) == 2
        print(f"✅ Generated Invoice: {invoice.number}")
        print(f"✅ Total Due: Rs {invoice.total_minor / 100:.2f}")

        kinds = [item.kind for item in invoice.line_items]
        assert LineItemKind.PRORATION_CHARGE in kinds
        assert LineItemKind.PRORATION_CREDIT in kinds
        print("✅ Line items include both PRORATION_CHARGE and PRORATION_CREDIT!")

from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.mark.anyio
async def test_subscription_change_plan_http_api():
    """
    Test the REST API endpoint: POST /api/subscriptions/{id}/change-plan
    1. Authenticates customer via JWT.
    2. Calls the plan change endpoint.
    3. Verifies HTTP 200 response with updated plan and proration invoice.
    4. Verifies invalid plan returns 404.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Login with our customer from Day 2
        login_res = await client.post("/api/auth/login", json={
            "email": "developer@billwise.com",
            "password": "strongpassword123"
        })
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Get the customer's ID and create a subscription
        async with SessionLocal() as session:
            users = UserRepository(session)
            user = await users.get_by_email("developer@billwise.com")
            customer = await users.get_customer_by_user_id(user.id)
            service = SubscriptionService(session)
            sub = await service.create_subscription(customer.id, "starter")
            await service.change_status(sub.id, SubscriptionStatus.ACTIVE)
            sub_id = str(sub.id)

        # 3. Call HTTP POST /api/subscriptions/{id}/change-plan
        res_change = await client.post(
            f"/api/subscriptions/{sub_id}/change-plan",
            json={"new_plan_code": "business"},
            headers=headers,
        )
        assert res_change.status_code == 200
        data = res_change.json()
        assert data["subscription"]["plan"]["code"] == "business"
        assert data["invoice"] is not None
        assert data["invoice"]["number"].startswith("INV-")
        print("\n✅ HTTP API: Successfully upgraded to Business plan via POST /api/subscriptions/{id}/change-plan!")

        # 4. Invalid plan code returns 404
        res_invalid = await client.post(
            f"/api/subscriptions/{sub_id}/change-plan",
            json={"new_plan_code": "galaxy_plan_does_not_exist"},
            headers=headers,
        )
        assert res_invalid.status_code == 404
        print("✅ HTTP API: Non-existent plan rejected with 404 Not Found!")