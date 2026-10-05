import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, enum_type
from app.models.enums import PaymentStatus


class Payment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One *attempt* to pay an invoice. An invoice can have many (retries)."""

    __tablename__ = "payments"
    __table_args__ = (CheckConstraint("amount_minor >= 0", name="ck_payments_amount_non_negative"),)

    invoice_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("invoices.id"), index=True)
    amount_minor: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    status: Mapped[PaymentStatus] = mapped_column(
        enum_type(PaymentStatus, "payment_status"), default=PaymentStatus.PENDING, index=True
    )
    gateway: Mapped[str] = mapped_column(String(30), default="razorpay")
    gateway_order_id: Mapped[str | None] = mapped_column(String(100), index=True)
    gateway_payment_id: Mapped[str | None] = mapped_column(String(100), unique=True)
    failure_reason: Mapped[str | None] = mapped_column(String(255))
    attempt_number: Mapped[int] = mapped_column(Integer, default=1)

    invoice: Mapped["Invoice"] = relationship(back_populates="payments")  # noqa: F821
