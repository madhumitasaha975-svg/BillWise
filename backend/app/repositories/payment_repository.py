import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment import Payment


class PaymentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, payment: Payment) -> Payment:
        """Insert a new payment attempt record."""
        self.session.add(payment)
        await self.session.flush()
        return payment

    async def get_by_id(self, payment_id: uuid.UUID) -> Payment | None:
        result = await self.session.execute(
            select(Payment).where(Payment.id == payment_id)
        )
        return result.scalar_one_or_none()

    async def get_by_gateway_order_id(self, order_id: str) -> Payment | None:
        """Find payment by gateway order identifier (e.g. order_fake_...)."""
        result = await self.session.execute(
            select(Payment).where(Payment.gateway_order_id == order_id)
        )
        return result.scalar_one_or_none()

    async def get_by_invoice_id(self, invoice_id: uuid.UUID) -> list[Payment]:
        """Fetch all payment attempts for an invoice (including retries)."""
        result = await self.session.execute(
            select(Payment)
            .where(Payment.invoice_id == invoice_id)
            .order_by(Payment.created_at.desc())
        )
        return list(result.scalars().all())