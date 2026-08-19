from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
import app.models.core as models

# We will apply a flat 10% tax rate for this engine
TAX_RATE = 0.10  

def calculate_proration(old_plan_price: float, new_plan_price: float, period_start: datetime, period_end: datetime):
    """Calculates the exact credits and charges for a mid-cycle upgrade."""
    now = datetime.now(timezone.utc)
    
    # Calculate the total days in the current billing cycle
    total_days = (period_end - period_start).days
    if total_days <= 0:
        total_days = 30  # Safe fallback to avoid division by zero
        
    # Calculate how many days are left before the cycle ends
    days_used = (now - period_start).days
    days_remaining = total_days - days_used
    
    if days_remaining < 0:
        days_remaining = 0
        
    # Find the daily cost of both plans
    old_daily_rate = old_plan_price / total_days
    new_daily_rate = new_plan_price / total_days
    
    # Calculate the credit for unused old plan, and charge for new plan
    unused_credit = old_daily_rate * days_remaining
    new_charge = new_daily_rate * days_remaining
    
    net_due = new_charge - unused_credit
    
    return {
        "days_remaining": days_remaining,
        "unused_credit": round(unused_credit, 2),
        "new_charge": round(new_charge, 2),
        "net_due": round(net_due, 2)
    }

def generate_standard_invoice(db: Session, subscription: models.Subscription, plan: models.Plan):
    """Generates a standard renewal invoice (Used by Celery Beat)."""
    subtotal = plan.price
    tax_amount = round(subtotal * TAX_RATE, 2)
    total_due = subtotal + tax_amount
    
    # Create the main Invoice record
    invoice = models.Invoice(
        customer_id=subscription.customer_id,
        subscription_id=subscription.id,
        subtotal=subtotal,
        tax_amount=tax_amount,
        amount_due=total_due,
        status=models.InvoiceStatus.open,
        due_date=datetime.now(timezone.utc) + timedelta(days=7) # <--- ADDED 7 DAY GRACE PERIOD
    )
    db.add(invoice)
    db.flush() # Flushes to DB to generate the unique ID and Invoice Number
    
    # Create the Line Item
    item = models.InvoiceItem(
        invoice_id=invoice.id,
        description=f"{plan.name} - Standard Renewal",
        amount=subtotal
    )
    db.add(item)
    db.commit()
    db.refresh(invoice)
    
    return invoice

def generate_prorated_upgrade_invoice(db: Session, subscription: models.Subscription, old_plan: models.Plan, new_plan: models.Plan):
    """Generates a complex invoice with line items when a user upgrades mid-cycle."""
    proration = calculate_proration(
        old_plan.price, 
        new_plan.price, 
        subscription.current_period_start, 
        subscription.current_period_end
    )
    
    subtotal = proration["net_due"]
    
    # If the user downgrades, the net_due might be negative (we owe them). 
    # For this sprint, we will floor negative invoices at $0.00.
    if subtotal < 0:
        subtotal = 0.0
        
    tax_amount = round(subtotal * TAX_RATE, 2)
    total_due = subtotal + tax_amount
    
    # Create the main Invoice record
    invoice = models.Invoice(
        customer_id=subscription.customer_id,
        subscription_id=subscription.id,
        subtotal=subtotal,
        tax_amount=tax_amount,
        amount_due=total_due,
        status=models.InvoiceStatus.open,
        due_date=datetime.now(timezone.utc) + timedelta(days=7) # <--- ADDED 7 DAY GRACE PERIOD
    )
    db.add(invoice)
    db.flush()
    
    # Line Item 1: Credit for the old plan (Negative Amount)
    credit_item = models.InvoiceItem(
        invoice_id=invoice.id,
        description=f"Credit: Unused time on {old_plan.name} ({proration['days_remaining']} days)",
        amount=-proration["unused_credit"]
    )
    db.add(credit_item)
    
    # Line Item 2: Charge for the new plan (Positive Amount)
    charge_item = models.InvoiceItem(
        invoice_id=invoice.id,
        description=f"Upgrade: Remaining time on {new_plan.name} ({proration['days_remaining']} days)",
        amount=proration["new_charge"]
    )
    db.add(charge_item)
    
    db.commit()
    db.refresh(invoice)
    
    return invoice


def generate_refund_invoice(db: Session, subscription: models.Subscription, plan: models.Plan):
    """Calculates unused time upon immediate cancellation and generates a refund invoice."""
    now = datetime.now(timezone.utc)
    
    # Calculate total days in the cycle
    total_days = (subscription.current_period_end - subscription.current_period_start).days
    if total_days <= 0:
        total_days = 30
        
    # Calculate unused days
    days_used = (now - subscription.current_period_start).days
    days_remaining = total_days - days_used
    
    if days_remaining <= 0:
        return None # No refund due if the cycle is basically over
        
    # Calculate exact refund amount
    daily_rate = plan.price / total_days
    refund_amount = round(daily_rate * days_remaining, 2)
    
    if refund_amount <= 0:
        return None
        
    # Create a negative invoice to represent the refund
    invoice = models.Invoice(
        customer_id=subscription.customer_id,
        subscription_id=subscription.id,
        subtotal=-refund_amount,
        tax_amount=0.0, # Keeping it simple for refunds
        amount_due=-refund_amount,
        status=models.InvoiceStatus.open,
        due_date=now # Refunds are processed immediately
    )
    db.add(invoice)
    db.flush()
    
    # Create the refund line item
    item = models.InvoiceItem(
        invoice_id=invoice.id,
        description=f"Refund: {days_remaining} unused days on {plan.name}",
        amount=-refund_amount
    )
    db.add(item)
    db.commit()
    db.refresh(invoice)
    
    return invoice