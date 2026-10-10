from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import require_admin
from app.core.database import get_db
from app.jobs.dunning import process_dunning_retries
from app.jobs.renewals import process_due_renewals
from app.models import Customer, Invoice, Plan, Subscription, User
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


@router.get("/analytics")
async def get_admin_analytics(session: AsyncSession = Depends(get_db)):
    """Comprehensive financial analytics, plan breakdowns, and billing schedule for Chart.js & Calendar."""
    # 1. Active MRR Calculation (sum of active subscription plan price)
    mrr_stmt = (
        select(func.sum(Plan.price_minor))
        .select_from(Subscription)
        .join(Plan, Subscription.plan_id == Plan.id)
        .where(Subscription.status == SubscriptionStatus.ACTIVE)
    )
    mrr_res = await session.execute(mrr_stmt)
    mrr_minor = mrr_res.scalar() or 0
    arr_minor = mrr_minor * 12

    # 2. Plan Distribution (count of subscriptions per plan)
    plan_dist_stmt = (
        select(Plan.name, func.count(Subscription.id))
        .select_from(Plan)
        .outerjoin(Subscription, Plan.id == Subscription.plan_id)
        .group_by(Plan.name)
    )
    plan_dist_res = await session.execute(plan_dist_stmt)
    plan_distribution = [
        {"plan_name": row[0], "count": row[1]}
        for row in plan_dist_res.all()
    ]

    # 3. Subscription Status Distribution
    status_dist_stmt = (
        select(Subscription.status, func.count(Subscription.id))
        .group_by(Subscription.status)
    )
    status_dist_res = await session.execute(status_dist_stmt)
    status_distribution = [
        {"status": row[0].value if hasattr(row[0], "value") else str(row[0]), "count": row[1]}
        for row in status_dist_res.all()
    ]

    # 4. Interactive Billing Schedule / Calendar (upcoming renewals in next 30 days)
    cal_stmt = (
        select(Subscription)
        .options(
            selectinload(Subscription.plan),
            selectinload(Subscription.customer).selectinload(Customer.user),
        )
        .where(Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.PAST_DUE]))
        .order_by(Subscription.current_period_end.asc())
        .limit(30)
    )
    cal_res = await session.execute(cal_stmt)
    calendar_events = []
    for s in cal_res.scalars().all():
        calendar_events.append({
            "id": str(s.id),
            "customer_name": s.customer.name if s.customer else "Unknown",
            "customer_email": s.customer.user.email if s.customer and s.customer.user else "Unknown",
            "plan_name": s.plan.name if s.plan else "Unknown",
            "renewal_date": s.current_period_end,
            "renewal_amount_minor": s.plan.price_minor if s.plan else 0,
            "status": s.status.value,
        })

    # 5. Simulated 6-Month MRR Growth Trend for Chart.js
    base_mrr = mrr_minor if mrr_minor > 0 else 149900
    months = ["May", "Jun", "Jul", "Aug", "Sep", "Oct"]
    growth_multipliers = [0.45, 0.58, 0.72, 0.85, 0.94, 1.0]
    revenue_trend = [
        {
            "month": m,
            "mrr_minor": int(base_mrr * mult),
            "invoiced_minor": int(base_mrr * mult * 1.18),  # including GST
        }
        for m, mult in zip(months, growth_multipliers)
    ]

    return {
        "mrr_minor": mrr_minor,
        "arr_minor": arr_minor,
        "plan_distribution": plan_distribution,
        "status_distribution": status_distribution,
        "revenue_trend": revenue_trend,
        "billing_calendar": calendar_events,
    }
