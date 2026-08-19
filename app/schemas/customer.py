from pydantic import BaseModel, EmailStr
from typing import List, Optional
from uuid import UUID
from datetime import datetime

# ==========================================
# CUSTOMER / AUTHENTICATION SCHEMAS
# ==========================================

# 1. Schema for data coming IN from the frontend (Registration)
class CustomerCreate(BaseModel):
    email: EmailStr
    password: str

# 2. Schema for data going OUT to the frontend
class CustomerResponse(BaseModel):
    id: str
    email: EmailStr

    # This tells Pydantic to read the data even if it is not a standard dictionary
    # (SQLAlchemy models return objects, not dictionaries)
    model_config = {"from_attributes": True}

class GoogleToken(BaseModel):
    token: str


# ==========================================
# SUBSCRIPTION PLAN SCHEMAS (PHASE 2)
# ==========================================

# Shared properties for all Plan operations
class PlanBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    currency: str = "USD"
    billing_interval: str = "monthly"  # 'monthly' or 'annual'
    trial_period_days: int = 0
    feature_entitlements: List[str] = []
    status: bool = True

# Properties required when an Admin creates a new plan
class PlanCreate(PlanBase):
    pass

# Properties allowed when an Admin updates an existing plan
# We don't inherit from PlanBase here because we want EVERY field to be optional
class PlanUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    billing_interval: Optional[str] = None
    trial_period_days: Optional[int] = None
    feature_entitlements: Optional[List[str]] = None
    status: Optional[bool] = None

# Properties returned to the frontend (includes DB-generated fields)
class PlanRead(PlanBase):
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = {"from_attributes": True}