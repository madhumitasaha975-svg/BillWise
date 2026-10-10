from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.payment_service import (
    PaymentService,
    WebhookSignatureVerificationError,
)

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


@router.post("/razorpay")
async def handle_razorpay_webhook(
    request: Request,
    session: AsyncSession = Depends(get_db),
    x_razorpay_signature: str = Header(None, alias="X-Razorpay-Signature"),
):
    """
    Server-to-server webhook handler for Razorpay events.
    Verifies cryptographic HMAC-SHA256 signature before processing.
    """
    if not x_razorpay_signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing X-Razorpay-Signature header",
        )

    # Read raw body bytes for exact signature evaluation
    raw_body = await request.body()

    service = PaymentService(session)
    try:
        result = await service.process_webhook_event(raw_body, x_razorpay_signature)
        return result
    except WebhookSignatureVerificationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )