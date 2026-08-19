import io
from datetime import datetime
from reportlab.lib.pagesizes import LETTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import app.models.core as models

def generate_invoice_pdf(invoice: models.Invoice, customer: models.Customer) -> io.BytesIO:
    """
    Generates a professional PDF invoice in-memory.
    Returns a BytesIO buffer that can be directly streamed via FastAPI.
    """
    # 1. Initialize the In-Memory Buffer
    buffer = io.BytesIO()
    
    # 2. Setup the Document Canvas
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=LETTER,
        rightMargin=40, leftMargin=40, topMargin=50, bottomMargin=50
    )
    
    # Setup Styles
    styles = getSampleStyleSheet()
    
    # Custom Brand Styles
    brand_color = colors.HexColor("#36b37e") # BillWise Mint Green
    text_color = colors.HexColor("#1e293b")
    
    title_style = ParagraphStyle(
        'BrandTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=brand_color,
        spaceAfter=20
    )
    
    normal_style = ParagraphStyle(
        'NormalStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=text_color,
        spaceAfter=4
    )
    
    bold_style = ParagraphStyle(
        'BoldStyle',
        parent=styles['Normal'],
        fontSize=10,
        fontName='Helvetica-Bold',
        textColor=text_color,
        spaceAfter=4
    )

    # 3. Build the PDF Elements
    elements = []
    
    # --- HEADER ---
    elements.append(Paragraph("BillWise", title_style))
    elements.append(Paragraph("123 Tech SaaS Blvd, Suite 400", normal_style))
    elements.append(Paragraph("San Francisco, CA 94105", normal_style))
    elements.append(Paragraph("billing@billwise.io", normal_style))
    elements.append(Spacer(1, 20))
    
    # --- INVOICE META DATA ---
    due_date_str = invoice.due_date.strftime("%B %d, %Y") if invoice.due_date else "Due Immediately"
    created_date_str = invoice.created_at.strftime("%B %d, %Y")
    
    elements.append(Paragraph(f"<b>INVOICE NO:</b> {invoice.invoice_number}", normal_style))
    elements.append(Paragraph(f"<b>DATE:</b> {created_date_str}", normal_style))
    elements.append(Paragraph(f"<b>DUE DATE:</b> {due_date_str}", normal_style))
    elements.append(Paragraph(f"<b>STATUS:</b> {invoice.status.value.upper()}", bold_style))
    elements.append(Spacer(1, 20))
    
    # --- CUSTOMER INFO ---
    elements.append(Paragraph("<b>BILLED TO:</b>", bold_style))
    # In a real app you'd use the customer's name, but we only have email in the schema so far
    elements.append(Paragraph(customer.email, normal_style)) 
    elements.append(Spacer(1, 20))
    
    # --- LINE ITEMS TABLE ---
    # Define Table Headers
    table_data = [
        ["Description", "Amount (USD)"]
    ]
    
    # Populate Line Items
    for item in invoice.items:
        # Format amount to 2 decimal places
        formatted_amount = f"${item.amount:,.2f}"
        table_data.append([item.description, formatted_amount])
        
    # Add Subtotal, Tax, and Total Rows
    table_data.append(["", ""]) # Blank spacer row
    table_data.append(["Subtotal:", f"${invoice.subtotal:,.2f}"])
    table_data.append(["Tax (10%):", f"${invoice.tax_amount:,.2f}"])
    table_data.append(["TOTAL DUE:", f"${invoice.amount_due:,.2f}"])
    
    # Create the Table Object
    col_widths = [400, 100] # Adjust widths based on LETTER size
    invoice_table = Table(table_data, colWidths=col_widths)
    
    # Style the Table
    table_style = TableStyle([
        # Header Styling
        ('BACKGROUND', (0, 0), (1, 0), brand_color),
        ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (1, 0), 10),
        
        # Body Styling
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
        ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        
        # Grid line under items
        ('LINEBELOW', (0, 1), (1, -5), 0.5, colors.lightgrey),
        
        # Totals Styling (Bottom 3 rows)
        ('FONTNAME', (0, -3), (1, -1), 'Helvetica-Bold'),
        ('LINEABOVE', (0, -3), (1, -3), 1, colors.black),
        ('TEXTCOLOR', (1, -1), (1, -1), brand_color), # Total Amount in Mint Green
    ])
    
    invoice_table.setStyle(table_style)
    elements.append(invoice_table)
    
    # --- FOOTER ---
    elements.append(Spacer(1, 40))
    elements.append(Paragraph("Thank you for your business!", bold_style))
    elements.append(Paragraph("If you have any questions concerning this invoice, please contact support.", normal_style))
    
    # 4. Build the PDF
    doc.build(elements)
    
    # 5. Reset the buffer's pointer to the beginning before returning
    buffer.seek(0)
    return buffer