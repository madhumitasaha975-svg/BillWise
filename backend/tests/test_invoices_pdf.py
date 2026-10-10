import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import SessionLocal
from app.main import app
from app.models.enums import InvoiceStatus, LineItemKind, SubscriptionStatus
from app.models.invoice import Invoice, InvoiceLineItem
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.user_repository import UserRepository
from app.services.pdf_service import PDFInvoiceGenerator
from app.services.subscription_service import SubscriptionService


@pytest.mark.anyio
async def test_pdf_generator_in_memory():
    """Verify that PDFInvoiceGenerator returns valid PDF binary bytes directly from RAM."""
    # Create an in-memory sample invoice with line items
    sample_invoice = Invoice(
        number="INV-2026-999999",
        status=InvoiceStatus.PAID,
        currency="INR",
        subtotal_minor=149900,
        tax_minor=26982,
        total_minor=176882,
    )
    sample_invoice.line_items = [
        InvoiceLineItem(
            kind=LineItemKind.BASE_FEE,
            description="Pro Plan Monthly Subscription",
            amount_minor=149900,
        ),
        InvoiceLineItem(
            kind=LineItemKind.PRORATION_CREDIT,
            description="Unused time on Starter Plan",
            amount_minor=-50000,
        ),
    ]

    pdf_bytes = PDFInvoiceGenerator.generate(
        invoice=sample_invoice,
        customer_name="Alice Developer",
        customer_email="alice@billwise.com",
    )

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    # Every valid PDF file starts with magic byte sequence %PDF
    assert pdf_bytes.startswith(b"%PDF")
    print("\n✅ PDF generated in-memory with valid %PDF magic header!")


@pytest.mark.anyio
async def test_download_invoice_pdf_http_endpoint():
    """Verify GET /api/invoices/{id}/pdf endpoint streams PDF with correct headers and IDOR security."""
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

        # 2. Create subscription & invoice
        async with SessionLocal() as session:
            users = UserRepository(session)
            user = await users.get_by_email("developer@billwise.com")
            customer = await users.get_customer_by_user_id(user.id)
            service = SubscriptionService(session)

            sub = await service.create_subscription(customer.id, "starter")
            await service.change_status(sub.id, SubscriptionStatus.ACTIVE)
            _, invoice = await service.change_plan(sub.id, "pro")
            assert invoice is not None
            invoice_id = str(invoice.id)
            invoice_number = invoice.number

        # 3. Download PDF via authenticated API
        pdf_res = await client.get(f"/api/invoices/{invoice_id}/pdf", headers=headers)
        assert pdf_res.status_code == 200
        assert pdf_res.headers["content-type"] == "application/pdf"
        assert f'filename="{invoice_number}.pdf"' in pdf_res.headers["content-disposition"]
        assert pdf_res.content.startswith(b"%PDF")
        print(f"✅ Downloaded invoice PDF: {invoice_number}.pdf ({len(pdf_res.content)} bytes)")

        # 4. IDOR Attack Prevention: Register a second customer and log in
        attacker_email = f"attacker_{uuid.uuid4().hex[:6]}@billwise.com"
        attacker_pwd = "attackerpassword123"
        reg_res = await client.post("/api/auth/register", json={
            "email": attacker_email,
            "password": attacker_pwd,
            "name": "Attacker Bob",
        })
        assert reg_res.status_code == 201

        attacker_login_res = await client.post("/api/auth/login", json={
            "email": attacker_email,
            "password": attacker_pwd,
        })
        assert attacker_login_res.status_code == 200
        attacker_token = attacker_login_res.json()["access_token"]
        attacker_headers = {"Authorization": f"Bearer {attacker_token}"}

        # Attacker attempts to download Customer A's invoice -> MUST BE REJECTED 403!
        idor_res = await client.get(f"/api/invoices/{invoice_id}/pdf", headers=attacker_headers)
        assert idor_res.status_code == 403
        assert idor_res.json()["detail"] == "Not authorized to download this invoice"
        print("✅ IDOR protection verified: Attacker blocked with 403 Forbidden!")

        # 5. Admin Authorization: Admin can download any customer's invoice
        admin_login = await client.post("/api/auth/login", json={
            "email": "admin@billwise.com",
            "password": "admin123"
        })
        assert admin_login.status_code == 200
        admin_token = admin_login.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        admin_res = await client.get(f"/api/invoices/{invoice_id}/pdf", headers=admin_headers)
        assert admin_res.status_code == 200
        assert admin_res.content.startswith(b"%PDF")
        print("✅ Admin permission verified: Admin successfully downloaded invoice PDF!")
