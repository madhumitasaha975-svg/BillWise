from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, JSON, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
import uuid
import random
import string
from datetime import datetime, timezone

# Import Base from your database connection
from app.database.connection import Base

# ==========================================
# HELPER FUNCTIONS
# ==========================================
def generate_invoice_number():
    """Generates a professional invoice number like INV-202608-X7B9"""
    date_str = datetime.now(timezone.utc).strftime("%Y%m")
    rand_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"INV-{date_str}-{rand_str}"

# ==========================================
# 1. ENUMS (State Machine Definitions)
# ==========================================
class SubscriptionState(str, enum.Enum):
    trial = "trial"
    active = "active"
    past_due = "past_due"
    paused = "paused"
    cancelled = "cancelled"

class InvoiceStatus(str, enum.Enum):
    draft = "draft"
    open = "open"
    paid = "paid"
    void = "void"
    uncollectible = "uncollectible"

class PaymentStatus(str, enum.Enum):
    pending = "pending"
    succeeded = "succeeded"
    failed = "failed"
    refunded = "refunded"

# ==========================================
# 2. EXISTING CORE MODELS
# ==========================================
class Customer(Base):
    __tablename__ = "customers"

    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_admin = Column(Boolean, default=False)
    
    # --- NEW COLUMNS FOR PROFILE SECTION ---
    full_name = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    # ---------------------------------------

    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Plan(Base):
    __tablename__ = "plans"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    price = Column(Float, nullable=False)
    currency = Column(String, default="USD")
    billing_interval = Column(String, default="monthly") 
    trial_period_days = Column(Integer, default=0)
    feature_entitlements = Column(JSON, default=list) 
    status = Column(Boolean, default=True) 
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

# ==========================================
# 3. NEW BILLING & SUBSCRIPTION MODELS
# ==========================================
class Subscription(Base):
    __tablename__ = "subscriptions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = Column(String, ForeignKey("customers.id"), nullable=False)
    plan_id = Column(String, ForeignKey("plans.id"), nullable=False)
    
    # Enum-typed subscription status
    status = Column(SQLEnum(SubscriptionState), default=SubscriptionState.trial, nullable=False)
    
    # Timestamps for the state machine logic
    trial_start = Column(DateTime(timezone=True), nullable=True)
    trial_end = Column(DateTime(timezone=True), nullable=True)
    current_period_start = Column(DateTime(timezone=True), nullable=False)
    current_period_end = Column(DateTime(timezone=True), nullable=False)
    
    # Flags for cancellation logic
    cancel_at_period_end = Column(Boolean, default=False)
    canceled_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class BillingCycle(Base):
    __tablename__ = "billing_cycles"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    subscription_id = Column(String, ForeignKey("subscriptions.id"), nullable=False)
    
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    billing_date = Column(DateTime(timezone=True), nullable=False) # When celery beat creates the invoice
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# --- UPGRADED INVOICE MODEL ---
class Invoice(Base):
    __tablename__ = "invoices"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    invoice_number = Column(String, unique=True, index=True, default=generate_invoice_number) # NEW
    
    customer_id = Column(String, ForeignKey("customers.id"), nullable=False)
    subscription_id = Column(String, ForeignKey("subscriptions.id"), nullable=True)
    
    subtotal = Column(Float, default=0.0, nullable=False)   # NEW
    tax_amount = Column(Float, default=0.0, nullable=False) # NEW
    amount_due = Column(Float, nullable=False)              # Final Total
    amount_paid = Column(Float, default=0.0)
    currency = Column(String, default="USD")
    
    status = Column(SQLEnum(InvoiceStatus), default=InvoiceStatus.draft, nullable=False)
    due_date = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # NEW: Link to line items
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")

# --- BRAND NEW INVOICE ITEM MODEL ---
class InvoiceItem(Base):
    __tablename__ = "invoice_items"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    invoice_id = Column(String, ForeignKey("invoices.id"), nullable=False)
    
    description = Column(String, nullable=False) # e.g., "Pro Plan - Monthly" or "Proration Credit"
    amount = Column(Float, nullable=False)       # Can be negative for credits!
    currency = Column(String, default="USD")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    invoice = relationship("Invoice", back_populates="items")

class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    invoice_id = Column(String, ForeignKey("invoices.id"), nullable=False)
    customer_id = Column(String, ForeignKey("customers.id"), nullable=False)
    
    amount = Column(Float, nullable=False)
    currency = Column(String, default="USD")
    status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.pending, nullable=False)
    
    payment_method = Column(String, nullable=True) # e.g., "credit_card", "bank_transfer"
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    entity_type = Column(String, nullable=False) # e.g., "Subscription", "Plan"
    entity_id = Column(String, nullable=False)   # The ID of the item changed
    action = Column(String, nullable=False)      # e.g., "TRIAL_TO_ACTIVE", "CANCELLED"
    
    old_value = Column(String, nullable=True)
    new_value = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())