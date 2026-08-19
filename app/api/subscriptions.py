from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel
from jose import jwt, JWTError
import httpx

# Database
from app.database.connection import get_db

# Models
import app.models.core as models

# Billing engine
from app.core import billing_math

# Celery notification task
from app.tasks.notifications import subscription_created_notification


router = APIRouter(
    prefix="/subscriptions",
    tags=["Subscriptions"]
)


# =========================================================
# DEPENDENCIES
# =========================================================

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_customer(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Decode the JWT and return the authenticated customer.
    """

    try:
        payload = jwt.decode(
            token,
            "",
            options={"verify_signature": False}
        )

        email = payload.get("sub")

        if email is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid token payload"
            )

    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid token format"
        )

    customer = (
        db.query(models.Customer)
        .filter(models.Customer.email == email)
        .first()
    )

    if not customer:
        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )

    return customer


# =========================================================
# SCHEMAS
# =========================================================

class SubscriptionCreate(BaseModel):
    plan_id: str


class CancelRequest(BaseModel):
    immediate: bool = False


# =========================================================
# 1. CREATE SUBSCRIPTION
# =========================================================

@router.post(
    "/",
    status_code=status.HTTP_201_CREATED
)
def create_subscription(
    sub_data: SubscriptionCreate,
    db: Session = Depends(get_db),
    customer: models.Customer = Depends(get_current_customer)
):
    """
    Create a new subscription.

    Flow:

        Customer
            ↓
        Subscription
            ↓
        Initial Invoice
            ↓
        Celery Notification
            ↓
        Email
    """

    # -----------------------------------------------------
    # Find the requested plan
    # -----------------------------------------------------

    plan = (
        db.query(models.Plan)
        .filter(models.Plan.id == sub_data.plan_id)
        .first()
    )

    if not plan:
        raise HTTPException(
            status_code=404,
            detail="Plan not found"
        )

    # -----------------------------------------------------
    # Calculate subscription dates
    # -----------------------------------------------------

    now = datetime.now(timezone.utc)

    sub_status = models.SubscriptionState.active

    trial_start = None
    trial_end = None

    if plan.trial_period_days and plan.trial_period_days > 0:

        sub_status = models.SubscriptionState.trial

        trial_start = now

        trial_end = (
            now + timedelta(days=plan.trial_period_days)
        )

        current_period_end = trial_end

    else:

        if plan.billing_interval == "annual":

            current_period_end = (
                now + timedelta(days=365)
            )

        else:

            current_period_end = (
                now + timedelta(days=30)
            )

    # -----------------------------------------------------
    # Create subscription
    # -----------------------------------------------------

    new_sub = models.Subscription(
        customer_id=customer.id,
        plan_id=plan.id,
        status=sub_status,
        trial_start=trial_start,
        trial_end=trial_end,
        current_period_start=now,
        current_period_end=current_period_end
    )

    db.add(new_sub)
    db.commit()
    db.refresh(new_sub)

    # -----------------------------------------------------
    # Generate initial invoice
    # -----------------------------------------------------

    try:

        billing_math.generate_standard_invoice(
            db,
            new_sub,
            plan
        )

    except Exception as e:

        print(
            f"Error generating initial invoice: {e}"
        )

    # -----------------------------------------------------
    # Queue subscription-created email
    #
    # IMPORTANT:
    # We use Celery here.
    #
    # FastAPI does NOT wait for Gmail SMTP.
    # -----------------------------------------------------

    try:

        subscription_created_notification.delay(
            email=customer.email,
            plan_name=plan.name,
            end_date=new_sub.current_period_end.isoformat()
        )

        print(
            f"Subscription notification queued for "
            f"{customer.email}"
        )

    except Exception as e:

        # Email failure should NOT break subscription creation.
        print(
            f"Error queueing subscription notification: {e}"
        )

    # -----------------------------------------------------
    # Audit log
    # -----------------------------------------------------

    audit = models.AuditLog(
        entity_type="Subscription",
        entity_id=new_sub.id,
        action=f"CREATED_AS_{sub_status.value.upper()}"
    )

    db.add(audit)
    db.commit()

    # -----------------------------------------------------
    # Return subscription
    # -----------------------------------------------------

    return new_sub


# =========================================================
# 2. GET MY SUBSCRIPTIONS
# =========================================================

@router.get("/me")
def get_my_subscriptions(
    db: Session = Depends(get_db),
    customer: models.Customer = Depends(get_current_customer)
):
    """
    Return the authenticated customer's subscriptions.
    """

    subscriptions = (
        db.query(models.Subscription)
        .filter(
            models.Subscription.customer_id == customer.id
        )
        .order_by(
            models.Subscription.created_at.desc()
        )
        .all()
    )

    return subscriptions


# =========================================================
# 3. GET ALL SUBSCRIPTIONS
# =========================================================

@router.get("/all")
def get_all_subscriptions(
    db: Session = Depends(get_db)
):
    """
    Admin endpoint returning all subscriptions.
    """

    subscriptions = (
        db.query(models.Subscription)
        .all()
    )

    return subscriptions


# =========================================================
# 4. CHANGE PLAN
# =========================================================

@router.put("/{sub_id}/change_plan")
def change_subscription_plan(
    sub_id: str,
    new_plan_id: str,
    db: Session = Depends(get_db),
    customer: models.Customer = Depends(get_current_customer)
):
    """
    Upgrade or downgrade an existing subscription.
    """

    # -----------------------------------------------------
    # Find subscription
    # -----------------------------------------------------

    sub = (
        db.query(models.Subscription)
        .filter(
            models.Subscription.id == sub_id,
            models.Subscription.customer_id == customer.id
        )
        .first()
    )

    if not sub:
        raise HTTPException(
            status_code=404,
            detail="Subscription not found"
        )

    # -----------------------------------------------------
    # Find new plan
    # -----------------------------------------------------

    new_plan = (
        db.query(models.Plan)
        .filter(models.Plan.id == new_plan_id)
        .first()
    )

    if not new_plan:
        raise HTTPException(
            status_code=404,
            detail="New plan not found"
        )

    # -----------------------------------------------------
    # Find old plan
    # -----------------------------------------------------

    old_plan = (
        db.query(models.Plan)
        .filter(models.Plan.id == sub.plan_id)
        .first()
    )

    if not old_plan:
        raise HTTPException(
            status_code=404,
            detail="Current plan not found"
        )

    old_plan_id = sub.plan_id

    # -----------------------------------------------------
    # Generate prorated invoice
    # -----------------------------------------------------

    invoice = billing_math.generate_prorated_upgrade_invoice(
        db,
        sub,
        old_plan,
        new_plan
    )

    # -----------------------------------------------------
    # Update subscription
    # -----------------------------------------------------

    sub.plan_id = new_plan.id

    db.commit()

    # -----------------------------------------------------
    # Audit
    # -----------------------------------------------------

    audit = models.AuditLog(
        entity_type="Subscription",
        entity_id=sub.id,
        action="PLAN_CHANGED",
        old_value=old_plan_id,
        new_value=new_plan.id
    )

    db.add(audit)
    db.commit()

    return {
        "message": "Plan updated successfully",
        "new_plan_id": new_plan.id,
        "invoice_generated": (
            invoice.invoice_number
            if invoice
            else None
        )
    }


# =========================================================
# 5. PAUSE SUBSCRIPTION
# =========================================================

@router.put("/{sub_id}/pause")
def pause_subscription(
    sub_id: str,
    db: Session = Depends(get_db),
    customer: models.Customer = Depends(get_current_customer)
):
    """
    Pause an active subscription.
    """

    sub = (
        db.query(models.Subscription)
        .filter(
            models.Subscription.id == sub_id,
            models.Subscription.customer_id == customer.id
        )
        .first()
    )

    if not sub:
        raise HTTPException(
            status_code=404,
            detail="Subscription not found"
        )

    if sub.status == models.SubscriptionState.cancelled:

        raise HTTPException(
            status_code=400,
            detail="Cannot pause a cancelled subscription"
        )

    old_status = sub.status

    sub.status = models.SubscriptionState.paused

    db.commit()

    # -----------------------------------------------------
    # Audit
    # -----------------------------------------------------

    audit = models.AuditLog(
        entity_type="Subscription",
        entity_id=sub.id,
        action="PAUSED",
        old_value=old_status.value,
        new_value=sub.status.value
    )

    db.add(audit)
    db.commit()

    return {
        "message": "Subscription paused successfully"
    }


# =========================================================
# 6. RESUME SUBSCRIPTION
# =========================================================

@router.put("/{sub_id}/resume")
def resume_subscription(
    sub_id: str,
    db: Session = Depends(get_db),
    customer: models.Customer = Depends(get_current_customer)
):
    """
    Resume a paused subscription.
    """

    sub = (
        db.query(models.Subscription)
        .filter(
            models.Subscription.id == sub_id,
            models.Subscription.customer_id == customer.id
        )
        .first()
    )

    if not sub:
        raise HTTPException(
            status_code=404,
            detail="Subscription not found"
        )

    if sub.status != models.SubscriptionState.paused:

        raise HTTPException(
            status_code=400,
            detail="Subscription is not paused"
        )

    now = datetime.now(timezone.utc)

    new_status = models.SubscriptionState.active

    # If trial has not expired, restore trial status.
    if sub.trial_end and sub.trial_end > now:

        new_status = models.SubscriptionState.trial

    old_status = sub.status

    sub.status = new_status

    db.commit()

    # -----------------------------------------------------
    # Audit
    # -----------------------------------------------------

    audit = models.AuditLog(
        entity_type="Subscription",
        entity_id=sub.id,
        action="RESUMED",
        old_value=old_status.value,
        new_value=new_status.value
    )

    db.add(audit)
    db.commit()

    return {
        "message": "Subscription resumed successfully",
        "status": new_status
    }


# =========================================================
# 7. CANCEL SUBSCRIPTION
# =========================================================

@router.put("/{sub_id}/cancel")
def cancel_subscription(
    sub_id: str,
    req: CancelRequest,
    db: Session = Depends(get_db),
    customer: models.Customer = Depends(get_current_customer)
):
    """
    Cancel a subscription either:

    immediate=True
        → cancel immediately
        → generate refund invoice
        → trigger mock bank refund

    immediate=False
        → continue until current billing period ends
    """

    # -----------------------------------------------------
    # Find subscription
    # -----------------------------------------------------

    sub = (
        db.query(models.Subscription)
        .filter(
            models.Subscription.id == sub_id,
            models.Subscription.customer_id == customer.id
        )
        .first()
    )

    if not sub:
        raise HTTPException(
            status_code=404,
            detail="Subscription not found"
        )

    old_status = sub.status

    now = datetime.now(timezone.utc)

    # =====================================================
    # IMMEDIATE CANCELLATION
    # =====================================================

    if req.immediate:

        sub.status = models.SubscriptionState.cancelled

        sub.canceled_at = now

        action = "CANCELLED_IMMEDIATELY"

        # -------------------------------------------------
        # Find plan
        # -------------------------------------------------

        plan = (
            db.query(models.Plan)
            .filter(models.Plan.id == sub.plan_id)
            .first()
        )

        if plan:

            # ---------------------------------------------
            # Generate refund invoice
            # ---------------------------------------------

            refund_invoice = (
                billing_math.generate_refund_invoice(
                    db,
                    sub,
                    plan
                )
            )

            # ---------------------------------------------
            # Trigger mock-bank refund
            # ---------------------------------------------

            if refund_invoice:

                try:

                    httpx.post(
                        "http://127.0.0.1:8000/mock-bank/refund",
                        json={
                            "invoice_id": refund_invoice.id,
                            "customer_id": sub.customer_id,
                            "amount": abs(
                                refund_invoice.amount_due
                            )
                        }
                    )

                except Exception as e:

                    print(
                        f"Error triggering refund: {e}"
                    )

    # =====================================================
    # END-OF-PERIOD CANCELLATION
    # =====================================================

    else:

        sub.cancel_at_period_end = True

        action = "SET_TO_CANCEL_AT_PERIOD_END"

    # -----------------------------------------------------
    # Save subscription change
    # -----------------------------------------------------

    db.commit()

    # -----------------------------------------------------
    # Audit log
    # -----------------------------------------------------

    audit = models.AuditLog(
        entity_type="Subscription",
        entity_id=sub.id,
        action=action,
        old_value=old_status.value,
        new_value=sub.status.value
    )

    db.add(audit)

    db.commit()

    return {
        "message": "Cancellation processed",
        "subscription_status": sub.status,
        "cancel_at_period_end": sub.cancel_at_period_end
    }