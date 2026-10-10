from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import Subscription, User
from app.models.enums import UserRole
from app.repositories.user_repository import UserRepository
from app.schemas.subscription import (
    ChangePlanRequest,
    ChangePlanResponse,
    SubscriptionResponse,
)
from app.services.subscription_service import (
    InvalidSubscriptionStateError,
    PlanNotFoundError,
    SubscriptionService,
)

router = APIRouter(prefix="/api/subscriptions", tags=["subscriptions"])


@router.get("/me", response_model=SubscriptionResponse | None)
async def get_my_subscription(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fetches the current user's latest subscription."""
    user_repo = UserRepository(session)
    customer = await user_repo.get_customer_by_user_id(current_user.id)
    if not customer:
        return None

    stmt = (
        select(Subscription)
        .options(selectinload(Subscription.plan))
        .where(Subscription.customer_id == customer.id)
        .order_by(Subscription.created_at.desc())
    )
    result = await session.execute(stmt)
    return result.scalars().first()



@router.get("/{subscription_id}", response_model=SubscriptionResponse)
async def get_subscription(
    subscription_id: UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = SubscriptionService(session)
    sub = await service.get_subscription(subscription_id)
    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")

    # If the user is a customer, ensure they own this subscription
    if current_user.role != UserRole.ADMIN:
        customer = await UserRepository(session).get_customer_by_user_id(current_user.id)
        if not customer or sub.customer_id != customer.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this subscription",
            )

    return sub


@router.post("/{subscription_id}/change-plan", response_model=ChangePlanResponse)
async def change_plan(
    subscription_id: UUID,
    data: ChangePlanRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = SubscriptionService(session)
    sub = await service.get_subscription(subscription_id)
    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")

    # Authorize ownership
    if current_user.role != UserRole.ADMIN:
        customer = await UserRepository(session).get_customer_by_user_id(current_user.id)
        if not customer or sub.customer_id != customer.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to modify this subscription",
            )

    try:
        updated_sub, invoice = await service.change_plan(
            subscription_id=subscription_id,
            new_plan_code=data.new_plan_code,
        )
        return ChangePlanResponse(subscription=updated_sub, invoice=invoice)
    except PlanNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Plan not found: {e}")
    except (InvalidSubscriptionStateError, ValueError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))