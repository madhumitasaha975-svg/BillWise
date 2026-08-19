from app.database.base import Base
from app.models import (
    AuditLog,
    BillingCycle,
    Customer,
    Invoice,
    InvoiceLineItem,
    Payment,
    PaymentRetry,
    Plan,
    Subscription,
)


def test_billing_models_are_registered():
    expected_tables = {
        "customers",
        "plans",
        "subscriptions",
        "billing_cycles",
        "invoices",
        "invoice_line_items",
        "payments",
        "payment_retries",
        "audit_logs",
    }

    assert expected_tables.issubset(set(Base.metadata.tables.keys()))
