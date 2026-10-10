from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models import Invoice, User
from app.models.enums import UserRole
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.user_repository import UserRepository
from app.schemas.payment import PaymentOrderResponse
from app.services.payment_service import PaymentService
from app.services.pdf_service import PDFInvoiceGenerator

router = APIRouter(prefix="/api/invoices", tags=["invoices"])


@router.get("/me")
async def get_my_invoices(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fetches all invoices belonging to the logged-in customer."""
    user_repo = UserRepository(session)
    customer = await user_repo.get_customer_by_user_id(current_user.id)
    if not customer:
        return []

    stmt = (
        select(Invoice)
        .options(selectinload(Invoice.line_items))
        .where(Invoice.customer_id == customer.id)
        .order_by(Invoice.created_at.desc())
    )
    result = await session.execute(stmt)
    invoices = result.scalars().all()
    return [
        {
            "id": str(inv.id),
            "number": inv.number,
            "status": inv.status.value,
            "currency": inv.currency,
            "subtotal_minor": inv.subtotal_minor,
            "tax_minor": inv.tax_minor,
            "total_minor": inv.total_minor,
            "created_at": inv.created_at,
            "paid_at": inv.paid_at,
            "line_items": [
                {
                    "description": item.description,
                    "kind": item.kind.value,
                    "amount_minor": item.amount_minor,
                }
                for item in inv.line_items
            ],
        }
        for inv in invoices
    ]



@router.post("/{invoice_id}/pay", response_model=PaymentOrderResponse)
async def create_payment_order(
    invoice_id: UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Initiates checkout by creating a payment order with the gateway."""
    invoice_repo = InvoiceRepository(session)
    invoice = await invoice_repo.get_by_id(invoice_id)
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

    # Authorize customer ownership
    if current_user.role != UserRole.ADMIN:
        customer = await UserRepository(session).get_customer_by_user_id(current_user.id)
        if not customer or invoice.customer_id != customer.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to pay this invoice",
            )

    service = PaymentService(session)
    try:
        payment = await service.create_payment_order_for_invoice(invoice_id)
        return PaymentOrderResponse(
            id=payment.id,
            invoice_id=payment.invoice_id,
            amount_minor=payment.amount_minor,
            currency=payment.currency,
            status=payment.status,
            gateway=payment.gateway,
            gateway_order_id=payment.gateway_order_id,
            gateway_key_id=settings.razorpay_key_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{invoice_id}/pdf")
async def download_invoice_pdf(
    invoice_id: UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generates and streams an authenticated, professional PDF tax invoice."""
    invoice_repo = InvoiceRepository(session)
    user_repo = UserRepository(session)

    invoice = await invoice_repo.get_by_id(invoice_id)
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

    # IDOR Protection: Customers can only download their own invoices
    customer = None
    if current_user.role != UserRole.ADMIN:
        customer = await user_repo.get_customer_by_user_id(current_user.id)
        if not customer or invoice.customer_id != customer.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to download this invoice",
            )
        customer_email = current_user.email
    else:
        customer = await user_repo.get_customer_by_id(invoice.customer_id)
        customer_email = "customer@billwise.com"

    customer_name = customer.name if customer else "Valued Customer"

    # Generate PDF in RAM
    pdf_bytes = PDFInvoiceGenerator.generate(
        invoice=invoice,
        customer_name=customer_name,
        customer_email=customer_email,
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{invoice.number}.pdf"',
        },
    )