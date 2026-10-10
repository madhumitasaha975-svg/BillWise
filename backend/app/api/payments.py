from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models import User
from app.models.enums import UserRole
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.user_repository import UserRepository
from app.schemas.payment import PaymentOrderResponse
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/api/invoices", tags=["payments"])


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