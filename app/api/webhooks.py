from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
import logging

from app.database.connection import get_db
import app.models.core as models
from app.tasks.notifications import (
    payment_success_notification,
    payment_failed_notification,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/webhooks",
    tags=["Webhooks"]
)


# --- SCHEMAS FOR INCOMING WEBHOOK PAYLOAD ---

class WebhookData(BaseModel):
    invoice_id: str
    customer_id: str
    amount_attempted: float
    currency: str
    status: str
    failure_reason: str | None = None


class PaymentWebhookPayload(BaseModel):
    event_id: str
    type: str
    data: WebhookData


# --- THE WEBHOOK LISTENER ENDPOINT ---

@router.post("/payments")
async def payment_event_webhook(
    payload: PaymentWebhookPayload,
    db: Session = Depends(get_db)
):
    """
    Receives payment events from the mock gateway (or Stripe).

    Updates invoice statuses and subscription access based on
    payment success/failure.

    After the payment transaction is successfully recorded,
    a Celery notification task is queued for the customer.
    """

    logger.info(f"Received webhook event: {payload.type}")

    event_type = payload.type
    data = payload.data

    # ---------------------------------------------------------
    # 1. Validate the Invoice exists in our database
    # ---------------------------------------------------------

    invoice = (
        db.query(models.Invoice)
        .filter(models.Invoice.id == data.invoice_id)
        .first()
    )

    if not invoice:
        logger.error(
            f"Webhook Error: Invoice {data.invoice_id} not found."
        )
        raise HTTPException(
            status_code=404,
            detail="Invoice not found"
        )

    # ---------------------------------------------------------
    # 2. Find the customer
    # ---------------------------------------------------------

    customer = (
        db.query(models.Customer)
        .filter(models.Customer.id == data.customer_id)
        .first()
    )

    if not customer:
        logger.error(
            f"Webhook Error: Customer {data.customer_id} not found."
        )
        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )

    # ---------------------------------------------------------
    # 3. Record the actual Payment Attempt
    # ---------------------------------------------------------

    # For refunds, treat "refunded" as a successful transaction.
    payment_status = (
        models.PaymentStatus.succeeded
        if data.status in ["succeeded", "refunded"]
        else models.PaymentStatus.failed
    )

    new_payment = models.Payment(
        invoice_id=invoice.id,
        customer_id=data.customer_id,
        amount=data.amount_attempted,
        currency=data.currency,
        status=payment_status,
        payment_method="mock_card_processor"
    )

    db.add(new_payment)

    # ---------------------------------------------------------
    # 4. Successful Payment
    # ---------------------------------------------------------

    if event_type == "payment_intent.succeeded":

        # Mark invoice as successfully paid
        invoice.status = models.InvoiceStatus.paid
        invoice.amount_paid = data.amount_attempted

        db.commit()

        logger.info(
            f"SUCCESS: Invoice {invoice.invoice_number} marked as PAID."
        )

        # Queue email only AFTER the database transaction succeeds.
        try:
            payment_success_notification.delay(
                email=customer.email,
                invoice_number=invoice.invoice_number,
                amount=data.amount_attempted,
                currency=data.currency,
            )

            logger.info(
                f"Payment success notification queued for "
                f"{customer.email}"
            )

        except Exception as e:
            # Email queue failure should not undo a successful payment.
            logger.error(
                f"Failed to queue payment success notification: {e}"
            )

    # ---------------------------------------------------------
    # 5. Failed Payment
    # ---------------------------------------------------------

    elif event_type == "payment_intent.failed":

        # Mark invoice as uncollectible
        invoice.status = models.InvoiceStatus.uncollectible

        # Security: Find the linked subscription and freeze
        # their account if currently active.
        if invoice.subscription_id:

            sub = (
                db.query(models.Subscription)
                .filter(
                    models.Subscription.id == invoice.subscription_id
                )
                .first()
            )

            if (
                sub
                and sub.status == models.SubscriptionState.active
            ):
                old_status = sub.status

                sub.status = models.SubscriptionState.past_due

                # Audit Log the automatic downgrade
                audit = models.AuditLog(
                    entity_type="Subscription",
                    entity_id=sub.id,
                    action="AUTO_DOWNGRADED_TO_PAST_DUE",
                    old_value=old_status.value,
                    new_value=sub.status.value
                )

                db.add(audit)

                logger.warning(
                    f"FAILURE: Subscription {sub.id} "
                    f"locked to PAST_DUE due to payment failure."
                )

        db.commit()

        logger.info(
            f"FAILURE: Invoice {invoice.invoice_number} "
           f"marked as UNCOLLECTIBLE."
        )

        # Queue payment failure notification
        try:
            payment_failed_notification.delay(
                email=customer.email,
                invoice_number=invoice.invoice_number,
                amount=data.amount_attempted,
                currency=data.currency,
            )

            logger.info(
                f"Payment failure notification queued for "
                f"{customer.email}"
            )

        except Exception as e:
            # Payment failure must still be recorded even if
            # the email queue temporarily fails.
            logger.error(
                f"Failed to queue payment failure notification: {e}"
            )

    # ---------------------------------------------------------
    # 6. Refunded Payment
    # ---------------------------------------------------------

    elif event_type == "payment_intent.refunded":

        # Mark the negative refund invoice as officially processed
        invoice.status = models.InvoiceStatus.paid
        invoice.amount_paid = data.amount_attempted

        db.commit()

        logger.info(
            f"REFUND SUCCESS: Invoice {invoice.invoice_number} "
            f"marked as PAID OUT to customer."
        )

    # ---------------------------------------------------------
    # 7. Return successful webhook response
    # ---------------------------------------------------------

    return {
        "status": "success",
        "message": "Webhook processed safely"
    }