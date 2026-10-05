import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, enum_type
from app.models.enums import InvoiceStatus, LineItemKind


class Invoice(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "invoices"

    number: Mapped[str] = mapped_column(String(50), unique=True)  # "INV-2026-000001"
    customer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("customers.id"), index=True
    )
    subscription_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("subscriptions.id"), index=True
    )
    billing_cycle_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("billing_cycles.id")
    )
    status: Mapped[InvoiceStatus] = mapped_column(
        enum_type(InvoiceStatus, "invoice_status"), default=InvoiceStatus.DRAFT, index=True
    )
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    subtotal_minor: Mapped[int] = mapped_column(Integer, default=0)
    tax_minor: Mapped[int] = mapped_column(Integer, default=0)
    total_minor: Mapped[int] = mapped_column(Integer, default=0)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    line_items: Mapped[list["InvoiceLineItem"]] = relationship(back_populates="invoice")
    payments: Mapped[list["Payment"]] = relationship(back_populates="invoice")  # noqa: F821


class InvoiceLineItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "invoice_line_items"

    invoice_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("invoices.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[LineItemKind] = mapped_column(enum_type(LineItemKind, "line_item_kind"))
    description: Mapped[str] = mapped_column(String(255))
    amount_minor: Mapped[int] = mapped_column(Integer)  # signed: credits are negative

    invoice: Mapped["Invoice"] = relationship(back_populates="line_items")
