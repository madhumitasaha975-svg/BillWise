from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from app.models.enums import BillingInterval, SubscriptionStatus
from app.schemas.invoice import InvoiceResponse


class PlanSummaryResponse(BaseModel):
    id: UUID
    code: str
    name: str
    price_minor: int
    billing_interval: BillingInterval

    model_config = ConfigDict(from_attributes=True)


class SubscriptionResponse(BaseModel):
    id: UUID
    customer_id: UUID
    plan_id: UUID
    status: SubscriptionStatus
    trial_ends_at: datetime | None
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool
    plan: PlanSummaryResponse

    model_config = ConfigDict(from_attributes=True)


class ChangePlanRequest(BaseModel):
    new_plan_code: str


class ChangePlanResponse(BaseModel):
    subscription: SubscriptionResponse
    invoice: InvoiceResponse | None = None