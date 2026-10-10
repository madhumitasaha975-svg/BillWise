import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, enum_type
from app.models.enums import CycleStatus, SubscriptionStatus


class Subscription(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "subscriptions"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("customers.id", ondelete="CASCADE"), index=True
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("plans.id"))
    status: Mapped[SubscriptionStatus] = mapped_column(
        enum_type(SubscriptionStatus, "subscription_status"),
        default=SubscriptionStatus.TRIALING,
        index=True,
    )
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    current_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    current_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    plan: Mapped["Plan"] = relationship()  # noqa: F821
    customer: Mapped["Customer"] = relationship()  # noqa: F821
    billing_cycles: Mapped[list["BillingCycle"]] = relationship(back_populates="subscription")


class BillingCycle(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "billing_cycles"
    __table_args__ = (
        UniqueConstraint("subscription_id", "cycle_number", name="uq_cycle_per_subscription"),
        CheckConstraint("period_end > period_start", name="ck_cycle_period_order"),
    )

    subscription_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("subscriptions.id", ondelete="CASCADE"), index=True
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("plans.id"))  # plan charged
    cycle_number: Mapped[int] = mapped_column(Integer)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[CycleStatus] = mapped_column(
        enum_type(CycleStatus, "cycle_status"), default=CycleStatus.OPEN
    )

    subscription: Mapped["Subscription"] = relationship(back_populates="billing_cycles")
