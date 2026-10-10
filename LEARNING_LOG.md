# LEARNING LOG

## Day 1 - Module 1 (Foundations)
- **Why async SQLAlchemy**: Database queries are I/O-bound. Instead of blocking the single Python process while waiting for PostgreSQL disk or network responses, async lets the server pause (`await`) and handle hundreds of concurrent user requests in the background.
- **Why Alembic instead of create_all()**: `Base.metadata.create_all()` only works on an empty database. In production, when adding new columns or updating relations, `create_all()` cannot alter existing tables without dropping data. Alembic tracks incremental migrations via `alembic_version` like Git commits for database schemas.
- **Why a state machine for subscription status**: Billing contracts must follow strict legal and business transitions (e.g. `trialing` -> `active` -> `past_due` -> `suspended` or `cancelled`). A state machine prevents corrupted states, such as jumping directly from `active` to `suspended` without payment retries or resurrecting a `cancelled` subscription.
- **Why money is stored as integer paise**: Floating-point numbers have binary precision rounding errors (e.g., `0.1 + 0.2 = 0.30000000000000004`). In financial software, storing amounts in minor units (paise/cents) as integers guarantees exact addition, subtraction, and zero precision drift during billing audits.
- **One thing that confused me today**: Python's import system with `python scripts/seed.py` vs `python -m scripts.seed`, and why SQLAlchemy's async engine needs the `greenlet` C-extension to bridge Python coroutines with lower-level database drivers.

---

## Day 2 - Module 2 (Auth, RBAC, Idempotency)
- **Password Hashing (bcrypt)**: Passwords must never be encrypted (two-way); they must be one-way hashed with a random salt. Salt prevents rainbow table dictionary attacks by ensuring identical passwords yield completely different cryptographic hashes.
- **Stateless Authentication (JWT)**: JSON Web Tokens consist of Header, Payload, and Signature. Because tokens are digitally signed with a server secret (`HS256`), the backend can verify user identity and roles in memory without querying the database on every single incoming API request.
- **Access vs Refresh Tokens**: Access tokens are short-lived (30 mins) to limit the blast radius if intercepted over insecure networks. Refresh tokens are long-lived (7 days) and used exclusively to issue new access tokens, allowing immediate revocation if a user is compromised.
- **Backend-Enforced RBAC**: Frontend UI hiding is not security. Role enforcement must happen at the router/dependency layer (`require_admin`) so that unauthorized actors attempting direct HTTP requests receive `403 Forbidden`.
- **Idempotency in Payments**: Network timeouts cause clients to retry requests. By passing an `Idempotency-Key` header with a SHA-256 hash of the request body, the backend can safely replay cached responses on duplicate requests and prevent double-charging customers. Reusing the same key with a different payload correctly triggers `409 Conflict`.

---

## Day 3 - Module 3 (Billing & Proration)
- **The Proration Formula**: When changing plans mid-cycle, we calculate the unused fraction of the billing period: credit the customer for unused time on the old plan (`-unused_credit`), and charge for the remaining time on the new plan (`+remaining_charge`). The net amount due is billed immediately.
- **Transparent Line Items**: Invoices cannot show arbitrary totals. Every proration invoice itemizes `PRORATION_CHARGE` and `PRORATION_CREDIT` separately so financial audits and customer statements match to the exact paisa.
- **Eager Loading vs. MissingGreenlet**: In async SQLAlchemy, accessing relationship properties (like `invoice.line_items`) cannot run implicit background SQL queries. Trying to access un-loaded relations triggers `MissingGreenlet`. Eager loading via `selectinload` fetches relations up front within the coroutine.
- **Database Connection Lifecycle (NullPool)**: In testing, `pytest` creates a new async event loop for every test. Standard connection pooling holds onto open database sockets tied to closed event loops, crashing with `RuntimeError: Event loop is closed`. Using `NullPool` ensures connections are closed cleanly per session/test.
- **Automated Period Rollover**: Subscriptions must advance periods automatically (`current_period_start = current_period_end`). Scheduled background jobs query subscriptions past their period end and generate sequential `BASE_FEE` renewal invoices.

---

## Day 4 - Module 4 (Payment Gateway & Webhooks)
- **Why Webhooks over Polling**: Payment gateways (Razorpay, Stripe) complete transactions asynchronously (user authentication, OTP, 3D Secure). Rather than the client or server polling the gateway API thousands of times every second, the gateway pushes an HTTP POST callback (webhook) directly to our server when the event occurs.
- **Never Trust Frontend Payment Callbacks**: If the frontend redirects to `success` or sends "payment succeeded", an attacker could easily forge this request via Postman without ever paying. The server must strictly wait for an authentic, signed server-to-server webhook from the payment gateway before updating invoice or subscription status.
- **HMAC-SHA256 Signature Verification**: To verify that a webhook genuinely originated from Razorpay (and not a malicious actor posting fake JSON), Razorpay computes `HMAC-SHA256(request_body, shared_secret)` and sends the signature in the `X-Razorpay-Signature` header. Our server recalculates the exact same HMAC in constant time (`hmac.compare_digest`) to prevent timing attacks.
- **Webhook Idempotency**: Payment gateways use retry policies when they don't receive an immediate 200 OK (e.g. temporary network blips). Therefore, a webhook may be delivered multiple times. We store processed `event_id`s in a `WebhookEvent` table; if an event is already recorded, we acknowledge with `200 OK` and skip processing to avoid duplicate accounting entries.
- **Gateway Abstraction Layer**: By defining a `PaymentGateway` protocol, the application business logic interacts with clean domain interfaces (`create_order`, `verify_webhook_signature`). We can switch between `FakePaymentGateway` for fast local testing and `RazorpayGateway` in production with a single configuration flag without modifying any service code.

---

## Day 5 (Part 1) - Module 5 (Dunning Engine & Failed Payment Recovery)
- **Involuntary vs. Voluntary Churn**: Voluntary churn happens when a customer deliberately clicks cancel. Involuntary churn happens when a legitimate paying customer is booted out because their card expired or their bank had a temporary 2-minute outage. Dunning protects against involuntary churn by granting a grace period and retrying smartly.
- **Grace Period State (`PAST_DUE`)**: When a renewal or proration charge fails, moving the subscription immediately to `SUSPENDED` causes customer outrage. Transitioning to `PAST_DUE` keeps service accessible while automated retry jobs re-attempt payment on Days 1, 3, and 5.
- **State Machine Protection**: Our strict state machine rules prevent illegal jumps (e.g. `trialing -> past_due` was prevented because you cannot owe debt on an unactivated trial). Subscriptions must move `ACTIVE -> PAST_DUE -> SUSPENDED` (if exhausted) or `PAST_DUE -> ACTIVE` (if recovered).
- **Immutable Audit Trails**: Financial systems require complete accountability. Every dunning action (`entered_past_due`, `retry_failed`, `recovered`, `exhausted_suspended`) writes an immutable record to the `audit_logs` table with details of attempt numbers, invoice numbers, and error reasons for customer support and audit reviews.

---

## Day 5 (Part 2) - Module 6 (PDF Invoice Generation & Secure Downloads)
- **In-Memory Streaming vs. Disk Storage**: Saving static PDF files to disk causes SSD exhaustion, container synchronization issues in multi-server clouds, and stale cache bugs. By generating the document in RAM using `io.BytesIO` and streaming directly with FastAPI's `Response(content=pdf_bytes, media_type="application/pdf")`, the backend remains completely stateless.
- **ReportLab Flowables Architecture**: ReportLab constructs documents via Flowables (`Paragraph`, `Spacer`, `Table`, `HRFlowable`) inside a `SimpleDocTemplate`. `TableStyle` allows programmatic borders, cell padding, background colors, and column widths for clean tabular accounting statements.
- **Insecure Direct Object Reference (IDOR) Defense**: Financial invoices contain sensitive PII and billing amounts. When exposing `/api/invoices/{id}/pdf`, the backend must explicitly verify that the invoice's `customer_id` matches the authenticated caller's profile. Unauthorized requests from other tenants must be rejected with `403 Forbidden`.


