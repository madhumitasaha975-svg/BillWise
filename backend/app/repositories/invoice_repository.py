import uuid
from datetime import datetime, timezone
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.invoice import Invoice, InvoiceLineItem


class InvoiceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def generate_invoice_number(self) -> str:
        """Generate sequential, human-friendly invoice numbers like INV-2026-000001."""
        year = datetime.now(timezone.utc).year
        # Count existing invoices for this year to get the next sequential number
        result = await self.session.execute(
            select(func.count(Invoice.id)).where(Invoice.number.like(f"INV-{year}-%"))
        )
        count = result.scalar() or 0
        return f"INV-{year}-{count + 1:06d}"

    async def add(self, invoice: Invoice, line_items: list[InvoiceLineItem]) -> Invoice:
        """Persist an invoice along with its itemized line items."""
        self.session.add(invoice)
        await self.session.flush()  # Ensures invoice.id is generated for foreign keys

        for item in line_items:
            item.invoice_id = invoice.id
            self.session.add(item)

        await self.session.flush()
        return invoice

    async def get_by_id(self, invoice_id: uuid.UUID) -> Invoice | None:
        """Fetch an invoice and eagerly load its line items."""
        result = await self.session.execute(
            select(Invoice)
            .options(selectinload(Invoice.line_items))
            .where(Invoice.id == invoice_id)
        )
        return result.scalar_one_or_none()

    async def get_by_subscription_id(self, subscription_id: uuid.UUID) -> list[Invoice]:
        """Fetch all invoices for a given subscription."""
        result = await self.session.execute(
            select(Invoice)
            .options(selectinload(Invoice.line_items))
            .where(Invoice.subscription_id == subscription_id)
            .order_by(Invoice.created_at.desc())
        )
        return list(result.scalars().all())