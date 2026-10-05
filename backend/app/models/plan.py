from sqlalchemy import Boolean, CheckConstraint, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, enum_type
from app.models.enums import BillingInterval


class Plan(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "plans"
    __table_args__ = (
        CheckConstraint("price_minor >= 0", name="ck_plans_price_non_negative"),
        CheckConstraint("trial_days >= 0", name="ck_plans_trial_non_negative"),
    )

    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)  # "pro"
    name: Mapped[str] = mapped_column(String(100))  # "Pro"
    price_minor: Mapped[int] = mapped_column(Integer)  # paise per interval
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    billing_interval: Mapped[BillingInterval] = mapped_column(
        enum_type(BillingInterval, "billing_interval"), default=BillingInterval.MONTHLY
    )
    trial_days: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
