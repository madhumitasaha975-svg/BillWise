import json
import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.payment_gateway import compute_hmac_signature
from app.jobs.dunning import process_dunning_retries
from app.main import app
from app.models.enums import InvoiceStatus, PaymentStatus, SubscriptionStatus
from app.models.system import AuditLog
from app.repositories.user_repository import UserRepository
from app.services.dunning_service import DunningService, MAX_DUNNING_ATTEMPTS
from app.services.subscription_service import SubscriptionService


@pytest.mark.anyio
async def test_dunning_payment_failure_moves_to_past_due():
    """Verify that a payment.failed webhook moves an active subscription to PAST_DUE and writes an audit log."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Login with Customer
        login_res = await client.post("/api/auth/login", json={
            "email": "developer@billwise.com",
            "password": "strongpassword123"
        })
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Setup active subscription with an open invoice
        async with SessionLocal() as session:
            users = UserRepository(session)
            user = await users.get_by_email("developer@billwise.com")
            customer = await users.get_customer_by_user_id(user.id)
            service = SubscriptionService(session)

            sub = await service.create_subscription(customer.id, "starter")
            await service.change_status(sub.id, SubscriptionStatus.ACTIVE)
            sub_id = sub.id

            _, invoice = await service.change_plan(sub.id, "pro")
            assert invoice is not None
            invoice_id = str(invoice.id)

        # 3. Create payment order via API
        pay_res = await client.post(f"/api/invoices/{invoice_id}/pay", headers=headers)
        assert pay_res.status_code == 200
        order_id = pay_res.json()["gateway_order_id"]

        # 4. Gateway sends signed payment.failed webhook
        webhook_payload = {
            "id": f"evt_{uuid.uuid4().hex[:12]}",
            "event": "payment.failed",
            "payload": {
                "payment": {
                    "entity": {
                        "id": f"pay_{uuid.uuid4().hex[:12]}",
                        "order_id": order_id,
                        "amount": invoice.total_minor,
                        "currency": "INR",
                        "status": "failed",
                        "error_description": "Card expired or insufficient funds",
                    }
                }
            }
        }
        raw_body = json.dumps(webhook_payload).encode("utf-8")
        sig = compute_hmac_signature(raw_body, settings.razorpay_webhook_secret)

        res = await client.post(
            "/api/webhooks/razorpay",
            content=raw_body,
            headers={"X-Razorpay-Signature": sig},
        )
        assert res.status_code == 200
        assert res.json()["status"] == "processed"

        # 5. Verify database state
        async with SessionLocal() as session:
            service = SubscriptionService(session)
            reloaded_sub = await service.get_subscription(sub_id)
            assert reloaded_sub.status == SubscriptionStatus.PAST_DUE
            print("\n✅ Subscription transitioned ACTIVE -> PAST_DUE on payment failure!")

            reloaded_inv = await service.invoices.get_by_id(uuid.UUID(invoice_id))
            assert reloaded_inv.status == InvoiceStatus.OPEN
            print("✅ Invoice remains OPEN during grace period!")

            # Verify audit log recorded
            stmt = select(AuditLog).where(
                AuditLog.action == "dunning.entered_past_due",
                AuditLog.entity_id == str(sub_id),
            )
            audit = (await session.execute(stmt)).scalar_one_or_none()
            assert audit is not None
            print("✅ Audit log 'dunning.entered_past_due' persisted successfully!")


@pytest.mark.anyio
async def test_dunning_retry_successful_recovery():
    """Verify that a successful retry marks invoice PAID and recovers subscription back to ACTIVE."""
    async with SessionLocal() as session:
        users = UserRepository(session)
        user = await users.get_by_email("developer@billwise.com")
        customer = await users.get_customer_by_user_id(user.id)
        sub_service = SubscriptionService(session)

        sub = await sub_service.create_subscription(customer.id, "business")
        await sub_service.change_status(sub.id, SubscriptionStatus.ACTIVE)
        _, invoice = await sub_service.change_plan(sub.id, "enterprise")
        invoice_id = invoice.id
        await sub_service.change_status(sub.id, SubscriptionStatus.PAST_DUE)
        sub_id = sub.id

        dunning_service = DunningService(session)
        result = await dunning_service.execute_dunning_retry(invoice_id, simulate_success=True)

        assert result["status"] == "recovered"
        assert result["subscription_status"] == "active"
        print("\n✅ Dunning retry recovered subscription back to ACTIVE!")

        reloaded_inv = await sub_service.invoices.get_by_id(invoice_id)
        assert reloaded_inv.status == InvoiceStatus.PAID
        print(f"✅ Invoice {reloaded_inv.number} successfully marked PAID!")

        # Verify audit log
        stmt = select(AuditLog).where(
            AuditLog.action == "dunning.recovered",
            AuditLog.entity_id == str(sub_id),
        )
        audit = (await session.execute(stmt)).scalar_one_or_none()
        assert audit is not None
        print("✅ Audit log 'dunning.recovered' recorded!")


@pytest.mark.anyio
async def test_dunning_exhaustion_suspends_subscription():
    """Verify that exhausting retries transitions subscription to SUSPENDED."""
    async with SessionLocal() as session:
        users = UserRepository(session)
        user = await users.get_by_email("developer@billwise.com")
        customer = await users.get_customer_by_user_id(user.id)
        sub_service = SubscriptionService(session)

        sub = await sub_service.create_subscription(customer.id, "starter")
        await sub_service.change_status(sub.id, SubscriptionStatus.ACTIVE)
        _, invoice = await sub_service.change_plan(sub.id, "pro")
        invoice_id = invoice.id
        await sub_service.change_status(sub.id, SubscriptionStatus.PAST_DUE)
        sub_id = sub.id

        dunning_service = DunningService(session)

        # Attempt 1: Fails
        res1 = await dunning_service.execute_dunning_retry(invoice_id, simulate_success=False)
        assert res1["status"] == "retry_failed"
        assert res1["attempt"] == 1
        print("\n✅ Attempt 1 failed - remaining in grace period (PAST_DUE)")

        # Attempt 2: Fails
        res2 = await dunning_service.execute_dunning_retry(invoice_id, simulate_success=False)
        assert res2["status"] == "retry_failed"
        assert res2["attempt"] == 2
        print("✅ Attempt 2 failed - remaining in grace period (PAST_DUE)")

        # Attempt 3: Fails (Exhaustion limit reached!)
        res3 = await dunning_service.execute_dunning_retry(invoice_id, simulate_success=False)
        assert res3["status"] == "exhausted"
        assert res3["subscription_status"] == "suspended"
        print("✅ Attempt 3 failed - Retries exhausted! Subscription transitioned to SUSPENDED!")

        # Verify subscription in DB is SUSPENDED
        reloaded_sub = await sub_service.get_subscription(sub_id)
        assert reloaded_sub.status == SubscriptionStatus.SUSPENDED

        # Verify audit log
        stmt = select(AuditLog).where(
            AuditLog.action == "dunning.exhausted_suspended",
            AuditLog.entity_id == str(sub_id),
        )
        audit = (await session.execute(stmt)).scalar_one_or_none()
        assert audit is not None
        print("✅ Audit log 'dunning.exhausted_suspended' recorded!")


@pytest.mark.anyio
async def test_dunning_background_worker_job():
    """Verify that process_dunning_retries scans past_due subscriptions and executes retries."""
    async with SessionLocal() as session:
        users = UserRepository(session)
        user = await users.get_by_email("developer@billwise.com")
        customer = await users.get_customer_by_user_id(user.id)
        sub_service = SubscriptionService(session)

        sub = await sub_service.create_subscription(customer.id, "starter")
        await sub_service.change_status(sub.id, SubscriptionStatus.ACTIVE)
        _, invoice = await sub_service.change_plan(sub.id, "pro")
        await sub_service.change_status(sub.id, SubscriptionStatus.PAST_DUE)
        assert invoice is not None

    # Run the background worker
    processed_count = await process_dunning_retries(simulate_success=True)
    assert processed_count >= 1
    print(f"\n✅ Background dunning worker processed {processed_count} invoice(s) successfully!")
