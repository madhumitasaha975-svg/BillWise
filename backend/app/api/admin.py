from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import require_admin
from app.core.database import get_db
from app.jobs.dunning import process_dunning_retries
from app.jobs.renewals import process_due_renewals
from app.models import Invoice, Subscription, User
from app.models.enums import InvoiceStatus, SubscriptionStatus
from app.models.system import AuditLog

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/metrics")
async def get_admin_metrics(session: AsyncSession = Depends(get_db)):
    """Aggregates high-level financial & subscription health metrics."""
    # 1. Total Subscriptions & Status Breakdown
    sub_count_res = await session.execute(select(func.count(Subscription.id)))
    total_subs = sub_count_res.scalar() or 0

    active_subs_res = await session.execute(
        select(func.count(Subscription.id)).where(Subscription.status == SubscriptionStatus.ACTIVE)
    )
    active_subs = active_subs_res.scalar() or 0

    past_due_res = await session.execute(
        select(func.count(Subscription.id)).where(Subscription.status == SubscriptionStatus.PAST_DUE)
    )
    past_due_subs = past_due_res.scalar() or 0

    suspended_res = await session.execute(
        select(func.count(Subscription.id)).where(Subscription.status == SubscriptionStatus.SUSPENDED)
    )
    suspended_subs = suspended_res.scalar() or 0

    # 2. Total Invoices & Revenue Collected
    inv_count_res = await session.execute(select(func.count(Invoice.id)))
    total_invoices = inv_count_res.scalar() or 0

    rev_res = await session.execute(
        select(func.sum(Invoice.total_minor)).where(Invoice.status == InvoiceStatus.PAID)
    )
    total_revenue_minor = rev_res.scalar() or 0

    return {
        "total_subscriptions": total_subs,
        "active_subscriptions": active_subs,
        "past_due_subscriptions": past_due_subs,
        "suspended_subscriptions": suspended_subs,
        "total_invoices": total_invoices,
        "total_revenue_minor": total_revenue_minor,
    }


@router.get("/subscriptions")
async def list_all_subscriptions(session: AsyncSession = Depends(get_db)):
    """Lists recent subscriptions across all tenants."""
    stmt = (
        select(Subscription)
        .options(selectinload(Subscription.plan))
        .order_by(Subscription.created_at.desc())
        .limit(50)
    )
    result = await session.execute(stmt)
    subs = result.scalars().all()
    return [
        {
            "id": str(s.id),
            "customer_id": str(s.customer_id),
            "plan_name": s.plan.name if s.plan else "Unknown",
            "plan_price_minor": s.plan.price_minor if s.plan else 0,
            "status": s.status.value,
            "current_period_start": s.current_period_start,
            "current_period_end": s.current_period_end,
            "created_at": s.created_at,
        }
        for s in subs
    ]


@router.get("/audit-logs")
async def list_audit_logs(session: AsyncSession = Depends(get_db)):
    """Lists recent audit events (dunning transitions, plan changes, etc.)."""
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(30)
    result = await session.execute(stmt)
    logs = result.scalars().all()
    return [
        {
            "id": str(log.id),
            "action": log.action,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "details": log.details,
            "created_at": log.created_at,
        }
        for log in logs
    ]


@router.post("/trigger-renewals")
async def trigger_renewals_job():
    """Manually triggers the background subscription renewal scanner."""
    renewed = await process_due_renewals()
    return {"message": "Renewal scan completed", "renewed_count": renewed}


@router.post("/trigger-dunning")
async def trigger_dunning_job():
    """Manually triggers the automated dunning retry worker."""
    retried = await process_dunning_retries(simulate_success=True)
    return {"message": "Dunning retry scan completed", "retried_count": retried}
