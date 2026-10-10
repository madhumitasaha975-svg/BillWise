import json
import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.payment_gateway import compute_hmac_signature
from app.main import app
from app.models.enums import InvoiceStatus, PaymentStatus, SubscriptionStatus
from app.repositories.user_repository import UserRepository
from app.services.subscription_service import SubscriptionService


@pytest.mark.anyio
async def test_full_payment_and_webhook_flow():
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

        # 2. Create an invoice by subscribing and upgrading
        async with SessionLocal() as session:
            users = UserRepository(session)
            user = await users.get_by_email("developer@billwise.com")
            customer = await users.get_customer_by_user_id(user.id)
            service = SubscriptionService(session)

            sub = await service.create_subscription(customer.id, "starter")
            await service.change_status(sub.id, SubscriptionStatus.ACTIVE)
            sub_id = sub.id

            # Upgrade to Pro to generate an open invoice
            _, invoice = await service.change_plan(sub.id, "pro")
            assert invoice is not None
            invoice_id = str(invoice.id)

        # 3. Checkout: Create payment order via POST /api/invoices/{id}/pay
        pay_res = await client.post(f"/api/invoices/{invoice_id}/pay", headers=headers)
        assert pay_res.status_code == 200
        pay_data = pay_res.json()
        order_id = pay_data["gateway_order_id"]
        assert order_id.startswith("order_fake_")
        assert pay_data["status"] == "pending"
        print(f"\n✅ Order created on gateway: {order_id}")

        # 4. FORGED SIGNATURE ATTACK: Send webhook with fake signature -> must fail with 400!
        webhook_event_id = f"evt_{uuid.uuid4().hex[:12]}"
        webhook_payload = {
            "id": webhook_event_id,
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": f"pay_{uuid.uuid4().hex[:12]}",
                        "order_id": order_id,
                        "amount": invoice.total_minor,
                        "currency": "INR",
                        "status": "captured",
                    }
                }
            }
        }
        raw_body = json.dumps(webhook_payload).encode("utf-8")

        res_forged = await client.post(
            "/api/webhooks/razorpay",
            content=raw_body,
            headers={"X-Razorpay-Signature": "forged_hacker_signature_123"},
        )
        assert res_forged.status_code == 400
        print("✅ Forged webhook rejected with 400 Bad Request!")

        # 5. LEGITIMATE WEBHOOK: Compute valid HMAC-SHA256 signature and send
        valid_signature = compute_hmac_signature(raw_body, settings.razorpay_webhook_secret)
        res_legit = await client.post(
            "/api/webhooks/razorpay",
            content=raw_body,
            headers={"X-Razorpay-Signature": valid_signature},
        )
        assert res_legit.status_code == 200
        assert res_legit.json()["status"] == "processed"
        print("✅ Legitimate webhook verified and processed!")

        # 6. Verify database state changed (Invoice -> PAID, Subscription -> ACTIVE)
        async with SessionLocal() as session:
            service = SubscriptionService(session)
            paid_inv = await service.invoices.get_by_id(uuid.UUID(invoice_id))
            assert paid_inv.status == InvoiceStatus.PAID
            assert paid_inv.paid_at is not None
            print(f"✅ Invoice {paid_inv.number} updated to PAID!")

            reloaded_sub = await service.get_subscription(sub_id)
            assert reloaded_sub.status == SubscriptionStatus.ACTIVE
            print("✅ Subscription confirmed in ACTIVE state!")

        # 7. IDEMPOTENT REPLAY: Send the exact same webhook again -> must be ignored!
        res_dup = await client.post(
            "/api/webhooks/razorpay",
            content=raw_body,
            headers={"X-Razorpay-Signature": valid_signature},
        )
        assert res_dup.status_code == 200
        assert res_dup.json()["status"] == "ignored"
        assert res_dup.json()["reason"] == "duplicate_event"
        print("✅ Duplicate webhook replay caught and safely ignored!")