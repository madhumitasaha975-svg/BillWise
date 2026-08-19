from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

# 1. Imports mapping to your exact project structure
from app.database.connection import get_db 
from app.models.core import Plan  
from app.schemas.customer import PlanCreate, PlanRead
from app.core.security import get_admin_user

# 2. Set up the FastAPI router
router = APIRouter(
    prefix="/plans",
    tags=["Subscription Plans"]
)

# --- NEW: SCHEMA FOR UPDATING PLANS ---
# We define this here for quick edits. 'Optional' means the frontend 
# can send just the price, just the name, or everything!
class PlanUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    feature_entitlements: Optional[List[str]] = None

# ==========================================
# 3. ROUTES
# ==========================================

@router.post("/", response_model=PlanRead, status_code=status.HTTP_201_CREATED)
def create_subscription_plan(
    plan: PlanCreate, 
    db: Session = Depends(get_db),
    current_admin = Depends(get_admin_user)  # 🔒 Phase 3 Gatekeeper!
):
    """
    Create a new subscription plan. (Admin Only)
    """
    # Check if a plan with this name already exists
    existing_plan = db.query(Plan).filter(Plan.name == plan.name).first()
    if existing_plan:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A plan with this name already exists."
        )

    # Convert Pydantic schema to an SQLAlchemy model
    new_plan = Plan(**plan.model_dump())
    
    # Save to database
    db.add(new_plan)
    db.commit()
    db.refresh(new_plan)
    
    return new_plan


@router.get("/", response_model=List[PlanRead])
def list_subscription_plans(db: Session = Depends(get_db)):
    """
    List all available subscription plans. (Publicly viewable)
    """
    # Anyone can view plans, so we don't include the admin dependency here
    plans = db.query(Plan).all()
    return plans

# ==========================================
# NEW ROUTES: UPDATE & DELETE
# ==========================================

@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_plan(
    plan_id: str, 
    db: Session = Depends(get_db), 
    current_admin = Depends(get_admin_user) # 🔒 Admin Only
):
    """
    Delete a subscription plan. (Admin Only)
    """
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    db.delete(plan)
    db.commit()
    return None

@router.put("/{plan_id}", response_model=PlanRead)
def update_plan(
    plan_id: str, 
    plan_update: PlanUpdate, 
    db: Session = Depends(get_db), 
    current_admin = Depends(get_admin_user) # 🔒 Admin Only
):
    """
    Update an existing subscription plan. (Admin Only)
    """
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    # exclude_unset=True ensures we ONLY update the fields the frontend actually sent over
    update_data = plan_update.model_dump(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(plan, key, value)
        
    db.commit()
    db.refresh(plan)
    return plan