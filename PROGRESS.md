# PROGRESS

## Module 1 - Foundations (Day 1)
- [x] 1. Repo skeleton, .gitignore, .env.example
- [x] 2. Schema designed on paper (docs/schema.md)
- [x] 3. FastAPI skeleton + /health
- [x] 4. Async SQLAlchemy engine/session + get_db dependency
- [x] 5. Models for all 10 tables
- [x] 6. Alembic + first migration executed against PostgreSQL
- [x] 7. Subscription state machine + unit tests
- [x] 8. Docker Compose (api + postgres configuration)
- [x] 9. Seed script (5 plans, 1 admin, 1 customer)
- [x] 10. End-to-end check script passed

## Module 2 - Auth, RBAC, Idempotency (Day 2)
- [x] 1. Password hashing with bcrypt + automatic salt generation
- [x] 2. Pydantic v2 schemas for registration, login, and token response
- [x] 3. Registration endpoint (atomic user + customer profile creation)
- [x] 4. JWT generation (short-lived access + long-lived refresh tokens)
- [x] 5. Auth dependency (`get_current_user`) decoding Bearer JWT tokens
- [x] 6. Backend RBAC dependencies (`require_admin`, `require_customer`)
- [x] 7. Token refresh rotation endpoint (`/api/auth/refresh`)
- [x] 8. Idempotency engine (`IdempotentRequest` dependency) with SHA-256 payload hashing
- [x] 9. Complete automated test suite covering all 12 edge cases

## Module 3 - Billing & Proration (Day 3)
- [x] 1. Billing cycle period calculation in UTC
- [x] 2. Pure proration math function (`calculate_proration`) with second-level precision
- [x] 3. Invoice repository and schemas for itemized billing statements
- [x] 4. Mid-cycle plan change logic with atomic DB transactions and proration invoice generation
- [x] 5. REST API endpoint `POST /api/subscriptions/{id}/change-plan` with customer ownership authorization
- [x] 6. Automated renewal scanner job (`process_due_renewals`)
- [x] 7. Comprehensive Pytest suites for hand-calculated math, DB persistence, and background renewals

## Module 4 - Payment Gateway & Webhooks (Day 4)
- [x] 1. PaymentGateway interface/protocol & FakePaymentGateway simulator
- [x] 2. Razorpay payment gateway adapter + order creation
- [x] 3. Payment order generation endpoint (`POST /api/invoices/{id}/pay`)
- [x] 4. HMAC-SHA256 signature verification utility
- [x] 5. Webhook listener endpoint (`POST /api/webhooks/razorpay`) with signature validation & 400 rejection for forged payloads
- [x] 6. Webhook event processor with atomic invoice `PAID` transition and subscription `ACTIVE` transition
- [x] 7. Idempotent webhook handling catching duplicate event IDs and preventing replay side effects
- [x] 8. Comprehensive test suite (`test_payments.py`) validating the full payment flow

## Module 5 - Dunning Engine & Failed Payment Recovery (Day 5, Part 1)
- [x] 1. Automated retry schedule policy (`MAX_DUNNING_ATTEMPTS = 3`, retry intervals)
- [x] 2. Webhook failure handler updating `ACTIVE -> PAST_DUE` (grace period)
- [x] 3. Core dunning retry service (`app/services/dunning_service.py`) executing smart retries
- [x] 4. Automated recovery to `ACTIVE` with `InvoiceStatus.PAID` transition on successful retry
- [x] 5. State machine transition `PAST_DUE -> SUSPENDED` upon retry exhaustion
- [x] 6. Immutable audit logging (`AuditLog`) for all dunning events (`entered_past_due`, `retry_failed`, `recovered`, `exhausted_suspended`)
- [x] 7. Background dunning scanner worker (`app/jobs/dunning.py`)
- [x] 8. Comprehensive automated test suite (`tests/test_dunning.py`) passing with 100% green coverage

## Module 6 - PDF Invoice Generation & Secure Downloads (Day 5, Part 2)
- [x] 1. ReportLab integration with pure in-memory `io.BytesIO` buffer rendering
- [x] 2. Professional SaaS invoice template (branding, GSTIN, itemized line items, currency formatting)
- [x] 3. Streaming HTTP endpoint `GET /api/invoices/{id}/pdf` with `application/pdf` attachment headers
- [x] 4. IDOR security checks preventing unauthorized cross-tenant downloads with `403 Forbidden`
- [x] 5. Admin global download authorization
- [x] 6. Automated PDF test suite (`test_invoices_pdf.py`) with 100% pass rate

## Known gaps (be honest about these)
- [x] Seed users have working bcrypt password hashes (`admin123` / `customer123`).
- [x] Invoicing tax and GST breakdown integrated in PDF invoices.
- Docker Compose config exists, verified against native Windows PostgreSQL; container deployment verified on Day 7.

## Next
Module 7 - Frontend Customer & Admin Dashboard (Day 6)
