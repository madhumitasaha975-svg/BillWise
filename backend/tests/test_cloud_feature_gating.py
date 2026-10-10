import uuid
from datetime import datetime, timedelta, timezone
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from app.main import app
from app.core.database import SessionLocal
from app.models import Customer, Plan, Subscription, User
from app.models.enums import SubscriptionStatus, UserRole
from app.core.security import create_access_token


@pytest.mark.anyio
async def test_cloud_feature_gating_lifecycle():
    """Verify decoupled SaaS architecture feature gating based on subscription tiers."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with SessionLocal() as session:
            # 1. Fetch starter and pro plans
            starter_plan = (await session.execute(select(Plan).where(Plan.code == "starter"))).scalar_one()
            pro_plan = (await session.execute(select(Plan).where(Plan.code == "pro"))).scalar_one()

            # 2. Create a test customer with Starter subscription
            unique_email = f"cloud_user_{uuid.uuid4().hex[:6]}@billwise.com"
            user = User(email=unique_email, hashed_password="pw", role=UserRole.CUSTOMER)
            session.add(user)
            await session.flush()

            customer = Customer(user_id=user.id, name="Cloud Tenant")
            session.add(customer)
            await session.flush()

            now = datetime.now(timezone.utc)
            sub = Subscription(
                customer_id=customer.id,
                plan_id=starter_plan.id,
                status=SubscriptionStatus.ACTIVE,
                current_period_start=now,
                current_period_end=now + timedelta(days=30),
            )
            session.add(sub)
            await session.commit()
            user_id = user.id
            sub_id = sub.id

        token = create_access_token(data={"sub": str(user_id), "role": "customer"})
        headers = {"Authorization": f"Bearer {token}"}

        # 3. Check initial resources: Starter allows 2 servers, NO load balancers
        res = await client.get("/api/cloud/resources", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["subscription"]["plan_code"] == "starter"
        assert data["limits"]["max_servers"] == 2
        assert data["limits"]["load_balancer_allowed"] is False
        print("\n[PASS] Verified Starter tier limits (2 servers, Load Balancer locked)!")

        # 4. Feature Gating: Attempt to deploy server with Load Balancer on Starter -> 403 Forbidden!
        res_lb = await client.post(
            "/api/cloud/servers",
            headers=headers,
            json={"name": "api-gateway", "vcpus": 2, "ram_gb": 4, "has_load_balancer": True},
        )
        assert res_lb.status_code == 403
        assert "Feature Gated" in res_lb.json()["detail"]
        print("[PASS] Feature gating verified: Load balancer blocked on Starter plan with 403!")

        # 5. Deploy valid server 1
        res_s1 = await client.post(
            "/api/cloud/servers",
            headers=headers,
            json={"name": "web-worker-01", "vcpus": 2, "ram_gb": 4, "has_load_balancer": False},
        )
        assert res_s1.status_code == 201
        s1_id = res_s1.json()["server"]["id"]
        print("[PASS] Server 1 deployed successfully within Starter limits!")

        # 6. Deploy valid server 2
        res_s2 = await client.post(
            "/api/cloud/servers",
            headers=headers,
            json={"name": "web-worker-02", "vcpus": 2, "ram_gb": 4, "has_load_balancer": False},
        )
        assert res_s2.status_code == 201
        s2_id = res_s2.json()["server"]["id"]
        print("[PASS] Server 2 deployed successfully (at capacity)!")

        # 7. Quota Gating: Attempt to deploy server 3 -> 403 Forbidden (Quota Exceeded)!
        res_s3 = await client.post(
            "/api/cloud/servers",
            headers=headers,
            json={"name": "web-worker-03", "vcpus": 2, "ram_gb": 4, "has_load_balancer": False},
        )
        assert res_s3.status_code == 403
        assert "Quota Exceeded" in res_s3.json()["detail"]
        print("[PASS] Quota gating verified: 3rd server blocked on Starter plan with 403!")

        # 8. Upgrade subscription to Pro plan
        async with SessionLocal() as session:
            sub_db = await session.get(Subscription, sub_id)
            sub_db.plan_id = pro_plan.id
            await session.commit()

        # 9. Now on Pro: Load Balancers are UNLOCKED!
        res_lb_pro = await client.post(
            "/api/cloud/servers",
            headers=headers,
            json={"name": "pro-lb-cluster", "vcpus": 4, "ram_gb": 8, "has_load_balancer": True},
        )
        assert res_lb_pro.status_code == 201
        assert res_lb_pro.json()["server"]["has_load_balancer"] is True
        print("[PASS] Upgraded to Pro: Load Balancer deployed successfully!")

        # 10. Billing Enforcement: Subscription falls into PAST_DUE
        async with SessionLocal() as session:
            sub_db = await session.get(Subscription, sub_id)
            sub_db.status = SubscriptionStatus.PAST_DUE
            await session.commit()

        # 11. Deployment blocked due to past_due status
        res_past_due = await client.post(
            "/api/cloud/servers",
            headers=headers,
            json={"name": "blocked-server", "vcpus": 2, "ram_gb": 4, "has_load_balancer": False},
        )
        assert res_past_due.status_code == 403
        assert "Billing Gate" in res_past_due.json()["detail"]
        print("[PASS] Billing enforcement verified: New deployments blocked when PAST_DUE!")

        # 12. Terminate server to free quota
        res_del = await client.delete(f"/api/cloud/servers/{s1_id}", headers=headers)
        assert res_del.status_code == 200
        print("[PASS] Terminated server successfully, quota freed!")
