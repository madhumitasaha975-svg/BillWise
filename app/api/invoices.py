from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

# Import database connection and models
from app.database.connection import get_db
import app.models.core as models
from app.api.subscriptions import get_current_customer

from fastapi.responses import StreamingResponse
from app.core import pdf_generator

router = APIRouter(
    prefix="/invoices",
    tags=["Invoices"]
)

# 1. GET ALL INVOICES (Admin View)
@router.get("/")
def get_all_invoices(db: Session = Depends(get_db)):
    """Fetches all invoices in the system for admin overview."""
    invoices = db.query(models.Invoice).all()
    return invoices

# 2. GET MY INVOICES (Customer View)
@router.get("/me")
def get_my_invoices(
    db: Session = Depends(get_db),
    customer: models.Customer = Depends(get_current_customer)
):
    """Fetches invoices belonging to the currently logged in customer."""
    invoices = db.query(models.Invoice).filter(models.Invoice.customer_id == customer.id).all()
    return invoices


# --- DOWNLOAD INVOICE PDF ---
@router.get("/{invoice_id}/pdf")
def download_invoice_pdf(
    invoice_id: str, 
    db: Session = Depends(get_db), 
    customer: models.Customer = Depends(get_current_customer)
):
    # 1. Fetch the invoice and ensure it belongs to the logged-in customer
    invoice = db.query(models.Invoice).filter(
        models.Invoice.id == invoice_id,
        models.Invoice.customer_id == customer.id
    ).first()
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
        
    # 2. Generate the PDF in-memory
    pdf_buffer = pdf_generator.generate_invoice_pdf(invoice, customer)
    
    # 3. Stream the file directly to the user's browser
    return StreamingResponse(
        pdf_buffer, 
        media_type="application/pdf", 
        headers={
            "Content-Disposition": f"attachment; filename={invoice.invoice_number}.pdf"
        }
    )