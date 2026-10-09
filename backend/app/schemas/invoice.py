from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from app.models.enums import InvoiceStatus, LineItemKind


class InvoiceLineItemResponse(BaseModel):
    id: UUID
    kind: LineItemKind
    description: str
    amount_minor: int

    model_config = ConfigDict(from_attributes=True)


class InvoiceResponse(BaseModel):
    id: UUID
    number: str
    customer_id: UUID
    subscription_id: UUID
    status: InvoiceStatus
    currency: str
    subtotal_minor: int
    tax_minor: int
    total_minor: int
    due_at: datetime | None
    paid_at: datetime | None
    created_at: datetime
    line_items: list[InvoiceLineItemResponse] = []

    model_config = ConfigDict(from_attributes=True)