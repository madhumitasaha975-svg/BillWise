from uuid import UUID
from pydantic import BaseModel, ConfigDict
from app.models.enums import PaymentStatus


class PaymentOrderResponse(BaseModel):
    id: UUID
    invoice_id: UUID
    amount_minor: int
    currency: str
    status: PaymentStatus
    gateway: str
    gateway_order_id: str
    gateway_key_id: str

    model_config = ConfigDict(from_attributes=True)