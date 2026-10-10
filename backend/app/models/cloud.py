import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin


class CloudServer(UUIDPrimaryKeyMixin, Base):
    """Simulated cloud compute instance for the decoupled SaaS feature gating demo.
    
    Demonstrates how BillWise acts as an external billing microservice:
    a separate application (Cloud Infrastructure Provider) queries BillWise
    to enforce quota limits and lock/unlock premium features (like Load Balancers).
    """

    __tablename__ = "cloud_servers"

    customer_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("customers.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    region: Mapped[str] = mapped_column(String(50), default="ap-south-1")
    vcpus: Mapped[int] = mapped_column(Integer, default=2)
    ram_gb: Mapped[int] = mapped_column(Integer, default=4)
    has_load_balancer: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(30), default="RUNNING")  # RUNNING, THROTTLED, STOPPED
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationship back to customer
    customer: Mapped["Customer"] = relationship("Customer", backref="cloud_servers")
