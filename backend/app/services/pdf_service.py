import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.models.enums import InvoiceStatus, LineItemKind
from app.models.invoice import Invoice


def format_currency(paise: int, currency: str = "INR") -> str:
    """Format integer minor units (paise) into human-readable currency (e.g. Rs. 1,499.00)."""
    sign = "-" if paise < 0 else ""
    abs_paise = abs(paise)
    rupees = abs_paise / 100.0
    return f"{sign}Rs. {rupees:,.2f}"


class PDFInvoiceGenerator:
    """Generates professional, printable PDF invoices entirely in-memory using ReportLab."""

    @staticmethod
    def generate(invoice: Invoice, customer_name: str, customer_email: str) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        styles = getSampleStyleSheet()
        elements = []

        # Color Palette
        brand_blue = colors.HexColor("#2563EB")
        dark_text = colors.HexColor("#0F172A")
        muted_text = colors.HexColor("#64748B")
        paid_green = colors.HexColor("#10B981")
        due_amber = colors.HexColor("#F59E0B")
        bg_light = colors.HexColor("#F8FAFC")

        # Custom Typographic Styles
        title_style = ParagraphStyle(
            "Title",
            parent=styles["Heading1"],
            fontSize=22,
            leading=26,
            textColor=brand_blue,
            fontName="Helvetica-Bold",
        )
        muted_style = ParagraphStyle(
            "Muted",
            parent=styles["Normal"],
            fontSize=9,
            leading=12,
            textColor=muted_text,
        )
        body_style = ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
            textColor=dark_text,
        )
        body_bold = ParagraphStyle(
            "BodyBold",
            parent=body_style,
            fontName="Helvetica-Bold",
        )
        badge_style = ParagraphStyle(
            "Badge",
            parent=styles["Normal"],
            fontSize=14,
            leading=16,
            fontName="Helvetica-Bold",
            alignment=2,  # Right aligned
            textColor=paid_green if invoice.status == InvoiceStatus.PAID else due_amber,
        )

        # -------------------------------------------------------------
        # 1. Header: Platform Name & Status Badge
        # -------------------------------------------------------------
        header_table = Table(
            [
                [
                    Paragraph("BILLWISE", title_style),
                    Paragraph(f"[{invoice.status.value.upper()}]", badge_style),
                ],
                [
                    Paragraph("Modern Subscription Billing Platform<br/>GSTIN: 29ABCDE1234F1Z5", muted_style),
                    Paragraph(f"<b>Invoice #:</b> {invoice.number}", ParagraphStyle("InvNo", parent=body_style, alignment=2)),
                ]
            ],
            colWidths=[3.5 * inch, 3.5 * inch],
        )
        header_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 16))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#E2E8F0"), spaceAfter=16))

        # -------------------------------------------------------------
        # 2. Metadata: Billed To & Dates
        # -------------------------------------------------------------
        created_date_str = invoice.created_at.strftime("%B %d, %Y") if invoice.created_at else "N/A"
        paid_date_str = invoice.paid_at.strftime("%B %d, %Y") if invoice.paid_at else "Pending"

        meta_table = Table(
            [
                [
                    Paragraph("<b>BILLED TO:</b>", muted_style),
                    Paragraph("<b>PAYMENT DETAILS:</b>", muted_style),
                ],
                [
                    Paragraph(f"<b>{customer_name}</b><br/>{customer_email}", body_style),
                    Paragraph(f"<b>Invoice Date:</b> {created_date_str}<br/><b>Payment Date:</b> {paid_date_str}<br/><b>Currency:</b> {invoice.currency}", body_style),
                ]
            ],
            colWidths=[3.5 * inch, 3.5 * inch],
        )
        meta_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BACKGROUND", (0, 0), (-1, -1), bg_light),
            ("PADDING", (0, 0), (-1, -1), 10),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ]))
        elements.append(meta_table)
        elements.append(Spacer(1, 20))

        # -------------------------------------------------------------
        # 3. Itemized Line Items Table
        # -------------------------------------------------------------
        line_item_data = [
            [
                Paragraph("<b>DESCRIPTION</b>", body_bold),
                Paragraph("<b>KIND</b>", body_bold),
                Paragraph("<b>AMOUNT</b>", ParagraphStyle("RightBold", parent=body_bold, alignment=2)),
            ]
        ]

        for item in invoice.line_items:
            kind_label = {
                LineItemKind.BASE_FEE: "Base Fee",
                LineItemKind.PRORATION_CHARGE: "Proration Charge",
                LineItemKind.PRORATION_CREDIT: "Proration Credit",
            }.get(item.kind, item.kind.value)

            line_item_data.append([
                Paragraph(item.description, body_style),
                Paragraph(kind_label, muted_style),
                Paragraph(format_currency(item.amount_minor, invoice.currency), ParagraphStyle("RightAmt", parent=body_style, alignment=2)),
            ])

        items_table = Table(line_item_data, colWidths=[4.0 * inch, 1.5 * inch, 1.5 * inch])
        items_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
            ("TEXTCOLOR", (0, 0), (-1, 0), dark_text),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        elements.append(items_table)
        elements.append(Spacer(1, 16))

        # -------------------------------------------------------------
        # 4. Financial Totals Section
        # -------------------------------------------------------------
        totals_table = Table(
            [
                ["Subtotal:", format_currency(invoice.subtotal_minor, invoice.currency)],
                ["Tax (GST 18%):", format_currency(invoice.tax_minor, invoice.currency)],
                ["Total Amount:", format_currency(invoice.total_minor, invoice.currency)],
            ],
            colWidths=[5.5 * inch, 1.5 * inch],
        )
        totals_table.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("TEXTCOLOR", (0, 0), (-1, -1), dark_text),
            ("FONTNAME", (0, 2), (-1, 2), "Helvetica-Bold"),
            ("FONTSIZE", (0, 2), (-1, 2), 12),
            ("TEXTCOLOR", (0, 2), (-1, 2), brand_blue),
            ("LINEABOVE", (0, 2), (-1, 2), 1, brand_blue),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(totals_table)
        elements.append(Spacer(1, 30))

        # -------------------------------------------------------------
        # 5. Footer & Compliance Note
        # -------------------------------------------------------------
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CBD5E1"), spaceAfter=10))
        elements.append(Paragraph(
            "This is an electronically generated tax invoice. No signature is required.<br/>"
            "Thank you for choosing BillWise! For billing questions, email support@billwise.com.",
            ParagraphStyle("Footer", parent=muted_style, alignment=1)  # Centered
        ))

        # Build PDF in RAM
        doc.build(elements)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes
