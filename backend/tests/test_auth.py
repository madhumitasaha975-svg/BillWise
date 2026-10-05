import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.mark.anyio
async def test_auth_full_lifecycle():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Register a new user
        reg_payload = {
            "email": "developer@billwise.com",
            "password": "strongpassword123",
            "name": "Madhumita"
        }
        res_reg = await client.post("/api/auth/register", json=reg_payload)
        if res_reg.status_code == 201:
            data = res_reg.json()
            assert data["email"] == "developer@billwise.com"
            assert data["role"] == "customer"
            assert "id" in data
            print("\n✅ Registration successful!")

        # 2. Duplicate registration must fail with 400
        res_dup = await client.post("/api/auth/register", json=reg_payload)
        assert res_dup.status_code == 400
        print("✅ Duplicate registration blocked with 400!")

        # 3. Wrong password must fail with 401
        res_wrong = await client.post("/api/auth/login", json={
            "email": "developer@billwise.com",
            "password": "wrongpassword"
        })
        assert res_wrong.status_code == 401
        print("✅ Invalid password blocked with 401!")

        # 4. Correct login returns tokens
        res_login = await client.post("/api/auth/login", json={
            "email": "developer@billwise.com",
            "password": "strongpassword123"
        })
        assert res_login.status_code == 200
        tokens = res_login.json()
        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]
        print("✅ Login successful, tokens received!")

        # 5. Protected route /api/auth/me WITHOUT token must fail
        res_no_auth = await client.get("/api/auth/me")
        assert res_no_auth.status_code in (401, 403)
        print("✅ Protected route without token blocked!")

        # 6. Protected route /api/auth/me WITH Bearer token succeeds
        res_me = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert res_me.status_code == 200
        assert res_me.json()["email"] == "developer@billwise.com"
        print("✅ Protected route with Bearer token passed!")

        # 7. Refresh token endpoint issues new access token
        res_refresh = await client.post("/api/auth/refresh", json={
            "refresh_token": refresh_token
        })
        assert res_refresh.status_code == 200
        assert "access_token" in res_refresh.json()
        print("✅ Token refresh succeeded!")

        # 8. RBAC TEST: Customer tries to access /api/auth/admin-only -> 403 Forbidden!
        res_admin = await client.get(
            "/api/auth/admin-only",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert res_admin.status_code == 403
        print("✅ RBAC passed: Customer blocked from admin route with 403!")

        # 9. IDEMPOTENCY TEST: Missing Idempotency-Key -> 400 Bad Request
        res_no_key = await client.post("/api/auth/test-charge", json={"amount": 149900})
        assert res_no_key.status_code == 400
        print("✅ Idempotency passed: Missing key rejected with 400!")

        # 10. IDEMPOTENCY TEST: Initial charge with unique key -> 200 OK
        idem_key = f"key-{uuid.uuid4()}"
        charge_payload = {"amount": 149900}
        res_charge1 = await client.post(
            "/api/auth/test-charge",
            json=charge_payload,
            headers={"Idempotency-Key": idem_key}
        )
        assert res_charge1.status_code == 200
        assert res_charge1.json()["status"] == "paid"
        print("✅ Idempotency passed: First charge processed!")

        # 11. IDEMPOTENCY TEST: Replaying exact same request returns cached response!
        res_charge2 = await client.post(
            "/api/auth/test-charge",
            json=charge_payload,
            headers={"Idempotency-Key": idem_key}
        )
        assert res_charge2.status_code == 200
        assert res_charge2.headers.get("X-Cache-Lookup") == "HIT-IDEMPOTENT"
        print("✅ Idempotency passed: Replay caught and safe cached response returned!")

        # 12. IDEMPOTENCY TEST: Reusing same key with DIFFERENT payload -> 409 Conflict!
        res_tampered = await client.post(
            "/api/auth/test-charge",
            json={"amount": 999900},  # Different amount!
            headers={"Idempotency-Key": idem_key}
        )
        assert res_tampered.status_code == 409
        print("✅ Idempotency passed: Tampered payload with reused key rejected with 409!")