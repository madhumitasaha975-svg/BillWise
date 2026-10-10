import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import Customer, Subscription, User
from app.models.cloud import CloudServer
from app.models.enums import SubscriptionStatus
from app.models.system import AuditLog
from app.repositories.user_repository import UserRepository

router = APIRouter(prefix="/api/cloud", tags=["cloud-infrastructure"])

# Quotas by subscription plan code
TIER_LIMITS = {
    "free": {
        "max_servers": 1,
        "max_vcpus_per_server": 1,
        "max_ram_per_server": 2,
        "load_balancer_allowed": False,
        "tier_name": "Free Tier",
    },
    "starter": {
        "max_servers": 2,
        "max_vcpus_per_server": 2,
        "max_ram_per_server": 4,
        "load_balancer_allowed": False,
        "tier_name": "Starter Plan",
    },
    "pro": {
        "max_servers": 5,
        "max_vcpus_per_server": 8,
        "max_ram_per_server": 16,
        "load_balancer_allowed": True,
        "tier_name": "Pro Plan",
    },
    "business": {
        "max_servers": 15,
        "max_vcpus_per_server": 16,
        "max_ram_per_server": 32,
        "load_balancer_allowed": True,
        "tier_name": "Business Plan",
    },
    "enterprise": {
        "max_servers": 50,
        "max_vcpus_per_server": 32,
        "max_ram_per_server": 64,
        "load_balancer_allowed": True,
        "tier_name": "Enterprise Plan",
    },
}


class DeployServerRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    region: str = Field(default="ap-south-1 (Mumbai)")
    vcpus: int = Field(default=2, ge=1, le=32)
    ram_gb: int = Field(default=4, ge=1, le=64)
    has_load_balancer: bool = Field(default=False)


async def _get_customer_and_subscription(session: AsyncSession, user_id: uuid.UUID):
    user_repo = UserRepository(session)
    customer = await user_repo.get_customer_by_user_id(user_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer profile not found")

    stmt = (
        select(Subscription)
        .options(selectinload(Subscription.plan))
        .where(Subscription.customer_id == customer.id)
        .order_by(Subscription.created_at.desc())
    )
    res = await session.execute(stmt)
    subscription = res.scalars().first()
    return customer, subscription


@router.get("/resources")
async def get_cloud_resources(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fetches user's deployed servers, live quota usage, and feature gating limits.
    
    This acts as the consumer of the BillWise decoupled billing engine:
    It checks subscription state and plan code to dynamically gate features.
    """
    customer, sub = await _get_customer_and_subscription(session, current_user.id)

    # Determine plan limits
    plan_code = sub.plan.code.lower() if sub and sub.plan else "free"
    limits = TIER_LIMITS.get(plan_code, TIER_LIMITS["free"])

    # Determine if billing state locks resources
    sub_status = sub.status if sub else None
    is_locked = False
    lock_reason = None

    if sub_status in (SubscriptionStatus.PAST_DUE, SubscriptionStatus.SUSPENDED):
        is_locked = True
        lock_reason = (
            f"Billing Alert: Subscription is {sub_status.value.upper()}. "
            "Cloud resources are throttled until outstanding invoices are settled."
        )
    elif sub_status == SubscriptionStatus.CANCELLED:
        is_locked = True
        lock_reason = "Subscription is CANCELLED. Upgrade to deploy cloud resources."

    # Fetch deployed servers
    stmt = (
        select(CloudServer)
        .where(CloudServer.customer_id == customer.id)
        .order_by(CloudServer.created_at.desc())
    )
    res = await session.execute(stmt)
    servers = res.scalars().all()

    # If subscription is past-due or suspended, display status as THROTTLED
    server_list = [
        {
            "id": str(s.id),
            "name": s.name,
            "region": s.region,
            "vcpus": s.vcpus,
            "ram_gb": s.ram_gb,
            "has_load_balancer": s.has_load_balancer,
            "status": "THROTTLED" if is_locked else s.status,
            "created_at": s.created_at,
        }
        for s in servers
    ]

    total_vcpus = sum(s.vcpus for s in servers)
    total_ram = sum(s.ram_gb for s in servers)
    lb_count = sum(1 for s in servers if s.has_load_balancer)

    return {
        "subscription": {
            "plan_code": plan_code,
            "plan_name": sub.plan.name if sub and sub.plan else "Free Tier",
            "status": sub_status.value if sub_status else "no_subscription",
            "is_locked": is_locked,
            "lock_reason": lock_reason,
        },
        "limits": limits,
        "usage": {
            "server_count": len(servers),
            "total_vcpus": total_vcpus,
            "total_ram_gb": total_ram,
            "load_balancers_count": lb_count,
        },
        "servers": server_list,
    }


@router.post("/servers", status_code=status.HTTP_201_CREATED)
async def deploy_server(
    payload: DeployServerRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Deploys a simulated cloud server after verifying BillWise feature gating rules."""
    customer, sub = await _get_customer_and_subscription(session, current_user.id)

    plan_code = sub.plan.code.lower() if sub and sub.plan else "free"
    limits = TIER_LIMITS.get(plan_code, TIER_LIMITS["free"])

    # 1. Check Subscription Health Gating
    if sub and sub.status in (SubscriptionStatus.PAST_DUE, SubscriptionStatus.SUSPENDED):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Billing Gate: Your subscription is currently {sub.status.value.upper()}. "
                "Cloud server deployment is suspended until payments are recovered."
            ),
        )

    # 2. Check Server Quota
    count_stmt = select(func.count(CloudServer.id)).where(CloudServer.customer_id == customer.id)
    count_res = await session.execute(count_stmt)
    current_count = count_res.scalar() or 0

    if current_count >= limits["max_servers"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Quota Exceeded: Your {limits['tier_name']} allows a maximum of "
                f"{limits['max_servers']} servers. Please upgrade your plan."
            ),
        )

    # 3. Check Specs Quota
    if payload.vcpus > limits["max_vcpus_per_server"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"CPU Limit: Your {limits['tier_name']} allows up to "
                f"{limits['max_vcpus_per_server']} vCPUs per instance."
            ),
        )

    if payload.ram_gb > limits["max_ram_per_server"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"RAM Limit: Your {limits['tier_name']} allows up to "
                f"{limits['max_ram_per_server']} GB RAM per instance."
            ),
        )

    # 4. Check Feature Gating for Premium Add-ons (Load Balancer)
    if payload.has_load_balancer and not limits["load_balancer_allowed"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Feature Gated: Cloud Load Balancers are only available on "
                "Pro, Business, and Enterprise plans. Please upgrade to unlock."
            ),
        )

    # All gates passed: Deploy instance
    new_server = CloudServer(
        customer_id=customer.id,
        name=payload.name,
        region=payload.region,
        vcpus=payload.vcpus,
        ram_gb=payload.ram_gb,
        has_load_balancer=payload.has_load_balancer,
        status="RUNNING",
    )
    session.add(new_server)

    # Record Audit Log
    audit = AuditLog(
        actor_user_id=current_user.id,
        action="cloud.server_deployed",
        entity_type="cloud_server",
        entity_id=str(new_server.id),
        details={
            "server_name": payload.name,
            "region": payload.region,
            "vcpus": payload.vcpus,
            "ram_gb": payload.ram_gb,
            "has_load_balancer": payload.has_load_balancer,
            "plan_code": plan_code,
        },
    )
    session.add(audit)

    await session.commit()
    await session.refresh(new_server)

    return {
        "message": "Cloud instance provisioned successfully",
        "server": {
            "id": str(new_server.id),
            "name": new_server.name,
            "region": new_server.region,
            "vcpus": new_server.vcpus,
            "ram_gb": new_server.ram_gb,
            "has_load_balancer": new_server.has_load_balancer,
            "status": new_server.status,
            "created_at": new_server.created_at,
        },
    }


@router.delete("/servers/{server_id}")
async def terminate_server(
    server_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Terminates a cloud instance and frees quota."""
    customer, _ = await _get_customer_and_subscription(session, current_user.id)

    stmt = select(CloudServer).where(
        CloudServer.id == server_id, CloudServer.customer_id == customer.id
    )
    res = await session.execute(stmt)
    server = res.scalars().first()

    if not server:
        raise HTTPException(status_code=404, detail="Server not found or access denied")

    await session.delete(server)

    audit = AuditLog(
        actor_user_id=current_user.id,
        action="cloud.server_terminated",
        entity_type="cloud_server",
        entity_id=str(server_id),
        details={"server_name": server.name},
    )
    session.add(audit)
    await session.commit()

    return {"message": f"Server {server.name} terminated successfully."}
