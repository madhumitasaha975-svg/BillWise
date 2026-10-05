from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "admin"
    CUSTOMER = "customer"


class BillingInterval(StrEnum):
    MONTHLY = "monthly"
    YEARLY = "yearly"


class SubscriptionStatus(StrEnum):
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"


class CycleStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"


class InvoiceStatus(StrEnum):
    DRAFT = "draft"
    OPEN = "open"
    PAID = "paid"
    VOID = "void"


class LineItemKind(StrEnum):
    BASE_FEE = "base_fee"
    PRORATION_CREDIT = "proration_credit"  # negative amount: unused time on old plan
    PRORATION_CHARGE = "proration_charge"  # positive amount: remaining time on new plan


class PaymentStatus(StrEnum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
