# 🎓 BillWise Placement & System Design Interview Preparation Guide

This guide compiles every core technical and system design question you can be asked in an interview about the BillWise codebase, organized day-by-day and module-by-module.

---

# 📅 DAY 1 — MODULE 1: FOUNDATIONS & ARCHITECTURE

### Q1: "Walk me through the architecture of BillWise. How does a request flow through your system?"
> **Answer:**
> "BillWise follows a strict **Layered (N-Tier) Architecture** to ensure clean separation of concerns:
> 1. **Routers (`app/api/`)**: Handle HTTP concerns only. They parse query params, validate request bodies via Pydantic schemas, and call the service layer. Routers contain zero business logic and zero SQL.
> 2. **Services (`app/services/`)**: The core business logic layer. They implement domain rules (e.g. checking whether a subscription transition is legal or calculating proration) and orchestrate data fetching via repositories. Services contain zero direct SQL.
> 3. **Repositories (`app/repositories/`)**: The database access layer. Only repositories execute SQLAlchemy ORM queries or touch database models.
> 4. **Database (PostgreSQL)**: Holds the normalized relational data.
>
> This separation makes our code modular, testable (we can unit test services by mocking repositories), and maintainable."

---

### Q2: "Why do you store monetary values in integer minor units (paise) instead of `float` or `double`?"
> **Answer:**
> "Floating-point numbers in computer architecture are represented using binary fractions (IEEE 754). Many decimal numbers cannot be represented exactly in binary (for example, `0.1 + 0.2` evaluates to `0.30000000000000004` in Python).
> Over thousands of billing cycles, invoices, and proration calculations, floating-point rounding errors accumulate, leading to balance mismatches, audit failures, and customer disputes.
> By storing currency in **minor units (paise or cents) as integers**, all additions, subtractions, and taxes are mathematically exact, eliminating precision drift."

---

### Q3: "Why did you choose asynchronous Python (FastAPI + asyncpg + async SQLAlchemy) instead of synchronous frameworks like Flask or Django?"
> **Answer:**
> "Subscription billing platforms are heavily **I/O-bound**. When the backend queries PostgreSQL, writes an audit log, or calls an external payment gateway like Razorpay, the server's CPU spends most of its time waiting for the network or disk to respond.
> In a synchronous server, a worker thread is blocked during that wait time, requiring thousands of threads or processes to handle scale.
> Using Python's `asyncio` with `asyncpg` and SQLAlchemy 2.0 AsyncSession, whenever a database query is awaited (`await session.execute(...)`), Python releases the thread to handle other incoming user requests. This allows a single BillWise server process to handle thousands of concurrent requests with low memory overhead."

---

### Q4: "What is the difference between `Base.metadata.create_all()` and Alembic database migrations?"
> **Answer:**
> "`Base.metadata.create_all()` is a naive development tool. It only checks if a table exists, and if not, creates it. It **cannot alter** existing tables in a running system. If you add a column, rename an index, or modify a constraint, `create_all()` does nothing. Dropping and recreating tables in production wipes out customer data.
> **Alembic** is a schema version control system (like Git for databases). Each schema modification is recorded as an incremental migration file with an `upgrade()` and `downgrade()` function. PostgreSQL stores an `alembic_version` table to track applied migrations, enabling safe zero-downtime schema deployments and rollbacks."

---

### Q5: "What is the difference between `alembic revision --autogenerate` and `alembic upgrade head`?"
> **Answer:**
> * `alembic revision --autogenerate -m "..."` is a **code generation step**. It inspects our SQLAlchemy models (`Base.metadata`), compares them against the current state of PostgreSQL, and writes a new Python migration script in `alembic/versions/`. It does **not** touch or alter any tables in PostgreSQL. This allows developers to review the generated DDL before execution.
> * `alembic upgrade head` is the **execution step**. It connects to PostgreSQL, reads `alembic_version`, runs the unapplied `upgrade()` scripts inside a transaction, and updates `alembic_version` to the newest migration ID (`head`)."

---

### Q6: "What is the difference between a SQLAlchemy Model and a Pydantic Schema? Why do we need both?"
> **Answer:**
> "They solve two completely different problems:
> * **SQLAlchemy Models (`app/models/`)**: Define the **storage layer** (table names, column types, primary keys, foreign key constraints, indexes).
> * **Pydantic Schemas (`app/schemas/`)**: Define the **network API contract** (request validation, response serialization, documentation in Swagger).
>
> We need both for security and decoupling. For instance, when a user registers, the incoming Pydantic schema expects a plain-text `password`. However, the SQLAlchemy model stores `hashed_password`. When returning a user profile response, the Pydantic schema excludes `hashed_password` completely, ensuring sensitive credentials are never leaked over the wire."

---

### Q7: "Why is a strict State Machine used for subscription status? Why is jumping directly from `active` to `suspended` forbidden?"
> **Answer:**
> "Subscriptions represent legally binding financial agreements. If statuses could change arbitrarily, bugs or race conditions could corrupt customer data (e.g. resurrecting a `cancelled` subscription or double-billing).
> We forbid `active -> suspended` directly because of the **dunning cycle**:
> * If a renewal payment fails, the subscription moves to `past_due`.
> * During `past_due`, the customer keeps service access while automated retry jobs re-attempt payment over a grace period (e.g., Days 1, 3, 5).
> * Only when retries are exhausted does the subscription transition from `past_due -> suspended`.
> Transitioning directly to `suspended` would abruptly cut off customers due to temporary bank network blips, causing massive, unnecessary customer churn."

---

### Q8: "In `app/core/database.py`, what is the purpose of `get_db()` having a `yield` statement and `session.rollback()` inside a `try/except` block?"
> **Answer:**
> "`get_db()` is implemented as a **FastAPI dependency with yield** to manage database session lifecycles on a per-request basis:
> 1. When an HTTP request enters, FastAPI calls `get_db()`, instantiates an isolated `AsyncSession`, and hands it to the router via `yield session`.
> 2. The router and service perform their business operations.
> 3. If an unhandled exception occurs, execution drops into the `except` block, triggering `await session.rollback()` to ensure no partially mutated or corrupted data remains in the database.
> 4. Finally, the `async with SessionLocal()` context manager guarantees the connection is released back to the engine's connection pool, preventing connection starvation."

---

### Q9: "Why was the `greenlet` library required when running async SQLAlchemy on Python 3.13?"
> **Answer:**
> "SQLAlchemy was originally engineered as a synchronous ORM. In version 2.0, SQLAlchemy added the `asyncio` extension on top of its existing architecture.
> To allow the synchronous ORM internals to communicate with Python's asynchronous event loop without rewriting the entire core engine from scratch, SQLAlchemy uses `greenlet` (a lightweight coroutine context switcher) to bridge coroutine execution. Without `greenlet`, SQLAlchemy cannot safely context-switch during query evaluation."

---

### Q10: "Why did `python scripts/seed.py` fail with `ModuleNotFoundError: No module named 'app'`, while `python -m scripts.seed` worked?"
> **Answer:**
> "When running `python scripts/seed.py`, Python automatically sets the script's directory (`scripts/`) as the first entry in `sys.path`. Since `app/` is one directory up, Python cannot find it.
> When using the `-m` (module) flag (`python -m scripts.seed`), Python runs the module using the **current working directory** as the root of `sys.path`. This makes both `app` and `scripts` importable at the top level."

---

# 📅 DAY 2 — MODULE 2: AUTH, RBAC & IDEMPOTENCY

### Q11: "Why should password hashing use a slow algorithm like `bcrypt` instead of fast cryptographic hashes like SHA-256 or MD5?"
> **Answer:**
> "Fast hash algorithms like SHA-256 and MD5 were designed for high-throughput checksums. Dedicated GPUs and ASICs can compute billions of SHA-256 hashes per second, making them trivial to crack via brute-force dictionary attacks if a database is dumped.
> `bcrypt`, by contrast, is intentionally **computationally expensive** (CPU & memory intensive) and includes a configurable 'work factor' (cost). Computing one bcrypt hash takes ~100 milliseconds on purpose. To a single user logging in, 100ms is imperceptible. But to an attacker attempting 100 billion guesses, it makes brute-forcing mathematically infeasible.
> Furthermore, `bcrypt` automatically generates and embeds a cryptographic salt into the hash, neutralizing pre-computed rainbow table attacks."

---

### Q12: "What is a 'Salt' in password hashing and what attack does it neutralize?"
> **Answer:**
> "A salt is cryptographically random data generated and concatenated with the plaintext password before hashing.
> Without a salt, two users with identical passwords (`'password123'`) would produce the exact same hash in the database. Attackers take advantage of this by pre-computing millions of common password hashes in lookup tables known as **Rainbow Tables**.
> With unique salts, even identical passwords produce completely unique hashes, completely neutralizing rainbow table lookup attacks."

---

### Q13: "Explain how JSON Web Tokens (JWT) work. What are its three parts?"
> **Answer:**
> "A JWT is a compact, URL-safe means of representing claims securely between two parties. It consists of three parts separated by dots (`.`):
> 1. **Header**: Contains the metadata and signing algorithm (e.g. `{"alg": "HS256", "typ": "JWT"}`).
> 2. **Payload (Claims)**: The data payload in JSON format (e.g. `{"sub": "user_id", "role": "customer", "exp": 1791233492, "type": "access"}`).
> 3. **Signature**: A cryptographic signature calculated as:
>    $$\text{HMAC-SHA256}(\text{Base64Url}(\text{Header}) + "." + \text{Base64Url}(\text{Payload}), \text{SECRET\_KEY})$$
>
> If an attacker attempts to alter the payload (e.g. changing `"role": "customer"` to `"role": "admin"`), the signature check fails against the server's private secret, and the request is rejected with `401 Unauthorized`."

---

### Q14: "Why use stateless JWT authentication instead of traditional database session tokens?"
> **Answer:**
> "In traditional session-based auth, every API request requires querying a `sessions` table in the database or Redis cache to verify if the user is authenticated. At 50,000 requests per second, that creates 50,000 database read operations.
> JWT is **stateless**. The token itself carries the user ID, role, and expiration timestamp. The backend verifies the token mathematically in memory using the symmetric secret key in sub-milliseconds without querying the database, enabling effortless horizontal scaling across multiple server instances."

---

### Q15: "What is the difference between an Access Token and a Refresh Token, and why do we issue two tokens instead of one?"
> **Answer:**
> "It's an engineering balance between **security** and **user experience**:
> * **Access Token**: Short-lived (e.g. 30 minutes) and sent on every API call in the `Authorization: Bearer <token>` header. Because it is short-lived, if intercepted over an insecure connection, the attacker has a very small window of opportunity before it expires.
> * **Refresh Token**: Long-lived (e.g. 7 days) and used exclusively at `/api/auth/refresh` to obtain a fresh access token without forcing the user to re-enter their credentials.
>
> If a user's account is compromised, the refresh token can be revoked or invalidated on the server. The attacker is permanently locked out as soon as the current 30-minute access token expires."

---

### Q16: "Why must Role-Based Access Control (RBAC) be enforced on the backend rather than the frontend?"
> **Answer:**
> "The frontend is an untrusted client environment running on the user's browser. Hiding an 'Admin Dashboard' link or disabling an 'Upgrade Plan' button in React provides zero real security; anyone can open Postman or DevTools and send a direct `POST` or `DELETE` request to your API.
> In BillWise, RBAC is strictly enforced at the API route layer using dependency injection (`require_admin = require_role(UserRole.ADMIN)`). If the decoded JWT role does not match, FastAPI intercepts the request immediately and returns `403 Forbidden` before any business logic or SQL executes."

---

### Q17: "What is Idempotency, and why is it critical in billing and payment processing?"
> **Answer:**
> "An operation is idempotent if performing it once produces the exact same side-effects as performing it multiple times.
> In payments, network drops between the client and server create a dangerous ambiguity:
> 1. A customer clicks 'Pay ₹1,499'.
> 2. The server charges the card successfully.
> 3. But before the `200 OK` response reaches the customer, their mobile network drops for 2 seconds.
> 4. The client thinks the request failed and retries the request.
>
> **Without idempotency**, the server would process the second request and charge the customer a second time (double-charge).
> **With idempotency**, the client attaches a unique `Idempotency-Key` header. The server records the key and the response. When the retry arrives with the same key, the server skips the payment logic and immediately returns the cached `200 OK` response."

---

### Q18: "How does the BillWise Idempotency Engine detect payload tampering when an Idempotency-Key is reused?"
> **Answer:**
> "Our `IdempotentRequest` dependency calculates a **SHA-256 hash of the incoming request body** (`request_hash`) and stores it alongside the `Idempotency-Key`.
> If a subsequent request arrives with an existing key, we compare the new request's hash against the stored hash:
> * If the hashes match, it's a legitimate network retry: we safely replay the cached response.
> * If the hashes differ, it means the client or an attacker attempted to reuse an existing idempotency key with different parameters (e.g. changing the amount or plan): our system rejects it with **`409 Conflict`**."

---

### Q19: "Why did the legacy `passlib` library break in Python 3.13, and what modern alternative did you use?"
> **Answer:**
> "`passlib` historically relied on the Unix `crypt` module in Python's standard library. In Python 3.13, the core development team officially removed `crypt` (PEP 594), causing `passlib` to crash with `ModuleNotFoundError: No module named 'crypt'`.
> In BillWise, we use the modern `bcrypt` library directly, which compiles native C extensions and operates independently of legacy standard library modules."

---

### Q20: "Why did `developer@billwise.test` throw a `422 Unprocessable Entity` in Pydantic v2?"
> **Answer:**
> "In Pydantic v2, `EmailStr` uses the underlying `email-validator` library. Under RFC 2606 and RFC 6761, `.test`, `.example`, and `.invalid` are officially reserved special-use top-level domains. `email-validator` strictly checks TLD validity to prevent bogus registrations. Using standard domain formats like `developer@billwise.com` satisfies RFC compliance."

---

# 📅 DAY 3 — MODULE 3: BILLING & PRORATION

### Q21: "Explain how proration works in a SaaS subscription platform with a concrete example."
> **Answer:**
> "Proration accounts for mid-cycle plan changes fairly by dividing the billing cycle based on the exact time used:
> 1. Suppose a customer pays ₹1,500/month (150,000 paise) for **Starter** on a 30-day billing cycle (Oct 1 to Oct 31).
> 2. On Oct 11 (10 days in), they upgrade to **Pro** at ₹3,000/month (300,000 paise).
> 3. **Unused Credit on Old Plan**: The customer has 20 unused days left on Starter:
>    $$\text{Credit} = 150,000 \times \frac{20}{30} = 100,000 \text{ paise (₹1,000)}$$
> 4. **Remaining Charge on New Plan**: The customer will use Pro for the remaining 20 days:
>    $$\text{Charge} = 300,000 \times \frac{20}{30} = 200,000 \text{ paise (₹2,000)}$$
> 5. **Net Amount Due Immediately**:
>    $$\text{Net Due} = 200,000 - 100,000 = 100,000 \text{ paise (₹1,000)}$$
> 6. We generate an invoice with two line items: a positive `PRORATION_CHARGE` (+200,000 paise) and a negative `PRORATION_CREDIT` (-100,000 paise)."

---

### Q22: "Why does accessing an ORM relationship in async SQLAlchemy raise `MissingGreenlet: greenlet_spawn has not been called`?"
> **Answer:**
> "In synchronous SQLAlchemy, reading an un-loaded relationship (like `invoice.line_items`) triggers a 'lazy load'—SQLAlchemy silently executes a hidden blocking SQL query to load the related rows.
> In async SQLAlchemy, all database I/O must be explicit and awaited. Python cannot pause execution inside a plain synchronous attribute lookup to perform an asynchronous network query.
> To prevent hidden blocking I/O, SQLAlchemy raises `MissingGreenlet`. The solution is **Eager Loading**: we use `selectinload(Invoice.line_items)` in our repository query so that parent and children are loaded together in the initial coroutine."

---

### Q23: "What caused `RuntimeError: Event loop is closed` when running async tests with PostgreSQL, and how did you resolve it?"
> **Answer:**
> "By default, SQLAlchemy's `create_async_engine` uses an internal connection pool (`QueuePool`) that keeps asyncpg TCP sockets open in memory to reuse them across requests.
> In test environments, test runners like `pytest-anyio` spin up and close a brand-new asyncio event loop for every single test function.
> When Test 1 finished, its event loop was closed. When Test 2 began in a new event loop, SQLAlchemy tried to reuse the cached connection from the pool, which was attached to the dead event loop from Test 1, triggering `RuntimeError: Event loop is closed`.
> We resolved this by configuring `poolclass=NullPool`. `NullPool` ensures connections are opened when needed and closed immediately when the session exits, preventing sockets from outliving their parent event loop."

---

### Q24: "How does the automated subscription renewal job work, and how does it prevent double renewals?"
> **Answer:**
> "Our background renewal engine (`process_due_renewals`) scans PostgreSQL for active subscriptions whose `current_period_end <= now`:
> 1. For each due subscription, it checks whether `cancel_at_period_end` is true. If so, it marks the subscription `CANCELLED` and stops renewal.
> 2. If continuing, it rolls the period forward in an atomic transaction:
>    $$\text{current\_period\_start} = \text{current\_period\_end}, \quad \text{current\_period\_end} = \text{new\_end}$$
> 3. It generates an `OPEN` renewal invoice with a `LineItemKind.BASE_FEE` line item for the plan's base price.
> 4. Because the update advances `current_period_end` to the future inside the database commit, subsequent runs of the background scanner will not pick up the same subscription again, making the renewal scan safe and idempotent."

---

# 📅 DAY 4 — MODULE 4: PAYMENT GATEWAY & WEBHOOKS

### Q25: "Why should a billing system never trust payment success notifications sent directly from the frontend (browser or mobile app)?"
> **Answer:**
> "Frontend clients execute code in an untrusted environment controlled by the end user or potential attacker. If the backend relied on a frontend redirect or client API call saying `POST /api/payments/confirm { status: 'success' }`:
> 1. An attacker could open Postman, inspect network traffic, and send a forged 'success' payload without ever paying a single rupee.
> 2. Conversely, a legitimate customer might complete their payment at the bank, but close their mobile browser before the return redirect executes, leaving their subscription wrongfully unpaid.
> 
> The gold standard in fintech is: **Frontend redirects are for UI feedback only. Payment confirmation and state mutation must strictly depend on cryptographically signed, server-to-server Webhooks sent directly from the payment gateway.**"

---

### Q26: "How does HMAC-SHA256 signature verification work for webhooks, and why must you use `hmac.compare_digest` instead of `==`?"
> **Answer:**
> "When Razorpay or Stripe sends an HTTP POST webhook:
> 1. The gateway hashes the raw binary request payload using a pre-shared secret:
>    $$\text{Signature} = \text{HMAC-SHA256}(\text{raw\_payload}, \text{webhook\_secret})$$
> 2. It attaches this signature in the `X-Razorpay-Signature` header.
> 3. Our server reads the raw binary body (`await request.body()`) before any JSON deserialization, recomputes the HMAC-SHA256 hash using the same secret, and checks if both signatures match.
> 
> **Why `hmac.compare_digest` instead of `==`?**
> Standard string comparison (`==`) short-circuits: it compares character-by-character and returns `False` the moment it finds the first mismatching byte. Attackers can exploit this via a **Timing Attack** by measuring microsecond response time differences to deduce the correct signature byte-by-byte. `hmac.compare_digest` runs in **constant time**, comparing all bytes regardless of mismatches, eliminating side-channel timing leaks."

---

### Q27: "What is Webhook Idempotency, and how does BillWise prevent double-processing payment events?"
> **Answer:**
> "Payment gateways adhere to an **'At-Least-Once Delivery'** guarantee. If our server takes slightly too long to respond with `200 OK` or if a network blip occurs, the gateway automatically retries delivering the same webhook event multiple times.
> If we blindly processed every incoming webhook, a subscription might be extended twice or duplicate payments credited.
> In BillWise:
> 1. Every webhook carries a unique gateway identifier (`event_id`, e.g. `evt_fake_...`).
> 2. We maintain a `WebhookEvent` database table with a unique constraint on `(gateway, event_id)`.
> 3. When a webhook arrives, we query whether this `event_id` was already successfully processed.
> 4. If yes, we **immediately return `200 OK`** without executing any invoice or subscription updates.
> 5. If no, we process the transaction and persist the event atomically in the database."

---

### Q28: "What design pattern did you use to decouple the payment gateway integration, and why is it important?"
> **Answer:**
> "We implemented the **Gateway Pattern / Strategy Pattern** using Python's `typing.Protocol`:
> 1. We defined an abstract `PaymentGateway` protocol specifying methods like `create_order(amount_paise, currency, receipt)` and `verify_webhook_signature(payload, signature)`.
> 2. We created two concrete implementations:
>    * `RazorpayGateway`: Connects to real Razorpay REST APIs and verifies live HMAC signatures.
>    * `FakePaymentGateway`: An offline simulator that generates reproducible deterministic test orders and verifies HMAC signatures using our secret.
> 3. A factory dependency `get_payment_gateway()` injects the appropriate gateway based on configuration.
> 
> This enables 100% offline development and instant CI/CD test suite execution without depending on external network access or test API credentials, while keeping production code completely gateway-agnostic."

---

### Q29: "What is an Out-of-Order Webhook problem, and how do you handle it?"
> **Answer:**
> "Because webhooks travel over asynchronous networks, there is no guarantee that events arrive in chronological order. A `payment.failed` event could arrive *after* a customer re-attempted and triggered a `payment.authorized` event.
> In BillWise, we guard against out-of-order mutations using:
> 1. **Strict State Machine validation**: If an invoice is already in `PAID` status, an incoming `payment.failed` event is rejected or ignored because the state machine disallows `PAID -> OPEN` or `PAID -> VOID`.
> 2. **Event timestamp checks**: We record `received_at` / gateway timestamps and only allow transitions if the event represents newer state."

---

### Q30: "Why must you read `await request.body()` as raw bytes rather than `request.json()` when verifying webhook signatures?"
> **Answer:**
> "HMAC-SHA256 computes a cryptographic digest of the **exact byte sequence** sent over the wire.
> If you parse the body with `request.json()` and then serialize it back to bytes using `json.dumps()`, Python may change whitespace, strip trailing newlines, or reorder dictionary keys.
> Even a single rearranged whitespace character or different key order produces a completely different SHA-256 hash, causing legitimate webhooks to fail signature verification. Always verify the signature against the untouched raw byte stream directly."

---

# 📅 DAY 5 (PART 1) — MODULE 5: DUNNING ENGINE & FAILED PAYMENT RECOVERY

### Q31: "What is Dunning Management and why is it essential in recurring SaaS billing architectures?"
> **Answer:**
> "Dunning is the automated management of payment failures and customer communication before a recurring subscription is terminated.
> In recurring subscription models, credit/debit card charges frequently fail for transient reasons: bank server timeouts, temporary daily card limits, or card re-issuance.
> If a platform immediately cuts off service or cancels accounts upon the first failed charge, it introduces severe friction, frustrates customers, and bleeds recurring revenue.
> A robust dunning engine implements an automated grace period, schedules smart retries over multiple days (e.g. Days 1, 3, 5), logs audit trails, and only suspends access if recovery attempts are completely exhausted."

---

### Q32: "What is the difference between Voluntary Churn and Involuntary Churn?"
> **Answer:**
> "* **Voluntary Churn**: Occurs when a customer intentionally and consciously decides to leave your product (e.g. clicking 'Cancel Subscription' because they no longer need the software or switched to a competitor).
> * **Involuntary (Passive) Churn**: Occurs when a customer wants to remain subscribed, but their payment fails silently in the background due to technical or banking issues (e.g. expired card, insufficient funds, bank fraud filter false positive).
> 
> Studies show that **up to 40% of all SaaS customer churn is involuntary**. The Dunning Engine directly recovers this otherwise lost revenue without requiring customer support intervention."

---

### Q33: "Walk me through the Dunning state machine and lifecycle transitions in BillWise."
> **Answer:**
> "Our state machine strictly enforces this recovery lifecycle:
> 1. **Initial Failure**: A customer's renewal or proration charge fails (`payment.failed` webhook). The subscription transitions:
>    $$\text{ACTIVE} \longrightarrow \text{PAST\_DUE}$$
>    The invoice remains in `OPEN` status, and an initial `Payment` attempt record is marked `FAILED`.
> 2. **Grace Period Retries**: A background worker (`process_dunning_retries`) queries all `PAST_DUE` subscriptions with open invoices and invokes our retry policy (`MAX_DUNNING_ATTEMPTS = 3`).
> 3. **Recovery Path**: If any retry attempt succeeds:
>    * The invoice transitions `OPEN -> PAID`.
>    * The subscription transitions:
>      $$\text{PAST\_DUE} \longrightarrow \text{ACTIVE}$$
>    * An audit log `dunning.recovered` is emitted.
> 4. **Exhaustion Path**: If retry #3 fails:
>    * The retry counter reaches `MAX_DUNNING_ATTEMPTS`.
>    * The state machine triggers:
>      $$\text{PAST\_DUE} \longrightarrow \text{SUSPENDED}$$
>    * An audit log `dunning.exhausted_suspended` is recorded, locking feature access."

---

### Q34: "Why do invoices remain in `OPEN` status during the dunning grace period rather than `FAILED` or `VOID`?"
> **Answer:**
> "In GAAP/IFRS accounting and database normalization:
> * An invoice represents an **outstanding debt obligation** that the customer owes to the business. As long as the customer is within their grace period and we are actively trying to recover payment, the debt remains valid and unsettled (`OPEN`).
> * `Payment` represents individual **transaction attempts** against that invoice. An invoice can have multiple payment attempts (`Payment.attempt_number = 1, 2, 3`), where attempts 1 and 2 may have `status = FAILED`, but attempt 3 has `status = SUCCEEDED`.
> * Marking an invoice `VOID` would legally forgive the debt, and marking it `FAILED` would prevent subsequent retry attempts from settling the invoice."

---

### Q35: "Why did attempting `change_plan` on a `PAST_DUE` subscription throw an `InvalidSubscriptionStateError`?"
> **Answer:**
> "In BillWise, our domain service layer enforces financial integrity rules. A customer currently in `PAST_DUE` status has an unsettled balance and overdue payment.
> Allowing a customer to switch tiers, upgrade, or calculate new proration charges while their previous invoice is delinquent would create compounded debt, race conditions in period dates, and credit leakage.
> Subscriptions must be restored to `ACTIVE` before any mid-cycle plan modifications can be initiated."

---

# 📅 DAY 5 (PART 2) — MODULE 6: PDF INVOICING & SECURE DOWNLOADS

### Q36: "Why should a production backend avoid saving generated PDF files to the local filesystem?"
> **Answer:**
> "Saving static files to local server disk creates severe operational anti-patterns:
> 1. **Disk Exhaustion**: At scale, hundreds of thousands of customer invoices will rapidly consume storage capacity and trigger system outages.
> 2. **Multi-Server Container State Inconsistency**: Modern cloud backends (AWS ECS, Kubernetes, Render) run multiple container replicas behind a load balancer. If Container 1 generates and saves a PDF locally, an immediate download request routed to Container 2 will return `404 Not Found`.
> 3. **Stale Cache Invalidation**: If an invoice transitions from `OPEN` to `PAID`, a stale PDF file sitting on disk might inadvertently be served to users.
> 
> Generating the PDF **dynamically in RAM** using `io.BytesIO` ensures our servers remain completely **stateless**, instantly scalable, and always reflective of current database state."

---

### Q37: "How do you generate and stream a binary PDF in FastAPI without saving it to disk?"
> **Answer:**
> "We combine Python's `io.BytesIO` buffer with FastAPI's `Response` object:
> 1. We instantiate an in-memory byte buffer: `buffer = io.BytesIO()`.
> 2. ReportLab's `SimpleDocTemplate` compiles the document elements (flowables) directly into this buffer: `doc.build(elements)`.
> 3. We extract the compiled raw bytes: `pdf_bytes = buffer.getvalue()`.
> 4. We return a FastAPI `Response`:
>    ```python
>    return Response(
>        content=pdf_bytes,
>        media_type="application/pdf",
>        headers={"Content-Disposition": f'attachment; filename="{invoice.number}.pdf"'}
>    )
>    ```
> 5. The memory buffer is immediately closed and garbage-collected, preventing RAM leaks."

---

### Q38: "What is an Insecure Direct Object Reference (IDOR) vulnerability, and how did you prevent it in the invoice download endpoint?"
> **Answer:**
> "An IDOR vulnerability occurs when an API accepts a database identifier (such as `/api/invoices/{id}/pdf`) and returns the underlying resource without verifying whether the authenticated caller actually owns that resource.
> Without protection, an attacker logged in as User B could brute-force invoice UUIDs and download sensitive billing receipts and PII belonging to User A.
> 
> In BillWise, our route handler enforces **Tenant Isolation**:
> 1. We decode the caller's JWT to get `current_user.id`.
> 2. We resolve the user's `Customer` profile.
> 3. We compare `invoice.customer_id == customer.id`.
> 4. If they do not match (and the caller is not an Admin), the request is rejected immediately with **`403 Forbidden`**."

---

### Q39: "What is the purpose of the `Content-Disposition` header when serving PDF files?"
> **Answer:**
> "The `Content-Disposition` response header dictates how the user's browser should handle the incoming binary payload:
> * `inline`: Tells the browser to render the PDF directly inside the browser's built-in PDF viewer tab.
> * `attachment; filename="INV-2026-000001.pdf"`: Prompts the browser's native 'Save As' download dialog with a pre-populated, clean filename.
> 
> In BillWise, we specify `attachment` with the sequential invoice number so users can conveniently store branded records for expense filing."

---

### Q40: "How do you verify in automated tests that a generated binary response is a valid PDF?"
> **Answer:**
> "Under the ISO 32000 standard, every valid PDF document must begin with the 4-byte magic signature **`%PDF`** (typically `%PDF-1.4`).
> In our Pytest suite (`test_invoices_pdf.py`):
> 1. We assert that `isinstance(pdf_bytes, bytes)` and `len(pdf_bytes) > 1000`.
> 2. We assert that `pdf_bytes.startswith(b"%PDF")`.
> 3. We verify that the HTTP response returns `headers['content-type'] == 'application/pdf'`.
> This guarantees valid document compilation without needing a headless browser or heavy external PDF parsing tools."

---

# 📅 DAY 6 — MODULE 7: FRONTEND CUSTOMER & ADMIN DASHBOARD

### Q41: "Explain how you implemented the Axios Interceptor pattern for JWT authentication and token refresh rotation."
> **Answer:**
> "In BillWise, rather than manually attaching auth headers to every component API call:
> 1. **Request Interceptor**: Intercepts every outgoing request, retrieves the access token from `localStorage`, and injects `headers.Authorization = 'Bearer ' + token`.
> 2. **Response Interceptor (Transparent Token Rotation)**:
>    * Listens for `401 Unauthorized` responses.
>    * If a `401` occurs and hasn't been retried yet (`!originalRequest._retry`), it sets `_retry = true`.
>    * It calls `/api/auth/refresh` using the stored `refresh_token`.
>    * Upon receiving fresh access and refresh tokens, it updates `localStorage`, rewires the original request's auth header, and replays the original API call.
>    * The customer never sees an error and never gets logged out mid-action."

---

### Q42: "How do you handle binary file downloads (like streaming PDF invoices) in an authenticated React application?"
> **Answer:**
> "A traditional `<a href='/api/invoices/123/pdf'>` tag cannot attach custom HTTP `Authorization: Bearer <token>` headers.
> To download secured binary files:
> 1. We issue an authenticated Axios request specifying `responseType: 'blob'`.
> 2. When the binary bytes arrive, we create a temporary in-memory Object URL using `window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }))`.
> 3. We dynamically create an invisible anchor tag `<a download='INV-XXXXXX.pdf' href={url}>`, append it to the DOM, programmatically trigger `.click()`, and remove it.
> 4. Finally, we call `window.URL.revokeObjectURL(url)` to clean up browser RAM."

---

### Q43: "What is Cross-Origin Resource Sharing (CORS), and how did you resolve it during development and production?"
> **Answer:**
> "CORS is a browser security mechanism that restricts a web application running at one origin (e.g. `http://localhost:5173`) from making HTTP requests to a different origin (e.g. `http://localhost:8000`) without server permission.
> In BillWise, we resolved this using **Reverse Proxying**:
> * In development, we configured Vite's dev server proxy: requests matching `/api/*` are internally forwarded by Vite's Node server to `http://localhost:8000`. The browser thinks it's talking to the same origin, eliminating preflight `OPTIONS` overhead and CORS errors.
> * In production, Nginx or Docker container reverse proxies both the built React static bundle and FastAPI behind the exact same domain."

---

### Q44: "How does the frontend decode user roles without making extra network requests to the backend?"
> **Answer:**
> "A JSON Web Token (JWT) is composed of Header, Payload, and Signature separated by dots.
> The Payload is a Base64URL-encoded JSON string containing standard claims (`sub`, `role`, `exp`).
> On the frontend, we use client-side decoding (`atob()`) to parse the JSON claims immediately upon receiving the token.
> This allows our `AuthProvider` and `ProtectedRoute` components to instantaneously determine whether the user is an `admin` or `customer` and render the appropriate dashboard without waiting for an extra round-trip user profile API query."

---

### Q45: "How did you design Role-Based Route Guards in React Router?"
> **Answer:**
> "We created a reusable `<ProtectedRoute requiredRole={...}>` wrapper component:
> 1. It inspects the `useAuth()` context.
> 2. If the user is unauthenticated, it returns `<Navigate to='/login' replace />`.
> 3. If a specific role is required (e.g. `requiredRole='admin'`) and the user's role is `customer`, it redirects them to `/dashboard` to prevent privilege escalation.
> 4. If authorized, it renders the child route wrapped in the global `<Navbar />`."
---

# 📅 DAY 7 — MODULE 8: DOCKER, CONTAINERIZATION & PRODUCTION DEPLOYMENT

### Q46: "Why do you use Docker for deploying BillWise? What problem does it solve?"
> **Answer:**
> "The classic 'it works on my machine' problem is caused by **environment drift** — your laptop has Python 3.13, the server has Python 3.9; you have asyncpg 0.29 installed, the server has 0.27. These subtle differences cause crashes in production that are impossible to reproduce locally.
> Docker packages the exact Python interpreter version, all installed libraries, the OS base layer, and the application code into a single self-contained, portable **image**. Running `docker compose up --build` on any machine — your laptop, an AWS EC2, a GCP Cloud Run instance — produces a bit-for-bit identical runtime environment.
> This is called **deployment parity**, and it's a fundamental production engineering principle."

---

### Q47: "Explain multi-stage Docker builds. Why did you implement them in BillWise?"
> **Answer:**
> "Multi-stage builds use multiple `FROM` statements in a single Dockerfile. Each `FROM` creates a temporary **stage** that can copy artifacts from previous stages.
>
> In BillWise:
> - **Stage 1 (builder)**: Installs build tools like `gcc` and `libpq-dev` needed to compile native C extensions (`asyncpg` uses C-level PostgreSQL protocol bindings, `bcrypt` uses a C extension for hashing speed). This stage creates a large image with compilers.
> - **Stage 2 (runtime)**: Copies only the `/install` directory containing compiled packages from the builder. The final image contains **zero build tools**.
>
> Why this matters:
> 1. **Smaller image**: Build tools (gcc, make, etc.) add hundreds of MBs. The runtime image is significantly leaner (~180MB vs ~400MB).
> 2. **Security**: If a container is compromised, attackers cannot use `gcc` or other compilers to compile malicious binaries inside the container. Removing tools reduces the **attack surface**.
> This technique is a production engineering best practice and expected in senior engineering interviews."

---

### Q48: "What is a Docker health check, and why is it critical in BillWise's docker-compose.yml?"
> **Answer:**
> "A health check is a command Docker runs periodically to determine whether a container is truly ready to accept traffic, not just running.
>
> BillWise's `db` service has:
> ```yaml
> healthcheck:
>   test: [\"CMD-SHELL\", \"pg_isready -U billwise -d billwise\"]
>   interval: 5s
>   retries: 10
> ```
> `pg_isready` exits with code 0 only when PostgreSQL is accepting connections. Without this, Docker would mark the container as `Up` the moment the process starts — but PostgreSQL takes 2-5 seconds to initialize its data directory on a fresh volume.
>
> The `api` service uses `depends_on: db: condition: service_healthy` — it will not start (and therefore won't run `alembic upgrade head`) until PostgreSQL is ready. Without this, the Alembic migration command would fail with a connection refused error and the container would crash on every cold start."

---

### Q49: "What is a named Docker volume? How is `pgdata` different from a bind mount?"
> **Answer:**
> "Docker has two ways to persist data outside a container's lifecycle:
>
> 1. **Bind mount**: Maps a specific path on the host machine (e.g. `./postgres-data:/var/lib/postgresql`) to the container. The data is a folder on your local filesystem.
> 2. **Named volume** (`pgdata`): Docker manages the storage location internally. The volume persists across `docker compose down` restarts.
>
> In BillWise we use a **named volume** (`pgdata`):
> - `docker compose down` → containers stop, but the `pgdata` volume (all PostgreSQL rows) survive
> - `docker compose up` → new containers start, connect to the same volume, data is intact
> - `docker compose down -v` → explicitly deletes the volume (clean slate for development resets)
>
> Named volumes are preferred in production because they're portable, Docker-managed, and don't expose internal paths to the host filesystem."

---

### Q50: "Why is the startup command `alembic upgrade head && python -m scripts.seed && uvicorn` ordered this way?"
> **Answer:**
> "The three commands must run in strict order because each depends on the previous:
>
> 1. `alembic upgrade head` — Applies all pending SQL migrations to create or alter tables. If the schema hasn't been applied, any INSERT or SELECT by the seed script or the app will throw a `UndefinedTable` PostgreSQL error.
> 2. `python -m scripts.seed` — The seed script is **idempotent** (safe to run on every startup). It checks whether each plan code and user email already exists before creating them. It depends on the schema existing from step 1.
> 3. `uvicorn app.main:app` — The HTTP server starts serving API requests only after the database schema is correct and demo data is present. If uvicorn started first, a user hitting `/api/auth/login` before seed completion would receive a 500 error.
>
> This pattern — **migrate → seed → serve** — is the standard container startup sequence for stateful web applications."

---

### Q51: "How do you manage secrets like database passwords and API keys in production Docker deployments?"
> **Answer:**
> "Secrets must **never** be hardcoded in source code or committed to Git — including in `docker-compose.yml`. Our approach:
>
> 1. **`.env.example`** — Committed to Git. Documents every required environment variable (database URL, secret key, Razorpay credentials) with placeholder values. Acts as the contract between the development and operations teams.
> 2. **`.env`** — Created by each developer/ops engineer by copying `.env.example`. Added to `.gitignore`. Docker Compose automatically reads `.env` from the project root and interpolates variables like `${SECRET_KEY}`.
> 3. **Production secrets management** — In real deployments (AWS, GCP), secrets are injected at runtime via services like **AWS Secrets Manager**, **GCP Secret Manager**, or **Kubernetes Secrets** mounted as environment variables. The `.env` file is only for local development.
>
> This ensures zero secrets in the Git history. An attacker who clones the repository finds only placeholder values."

---

### Q52: "If a Docker container crashes in production, what mechanisms ensure BillWise recovers automatically?"
> **Answer:**
> "Several layers of automatic recovery:
>
> 1. **`restart: unless-stopped`** — Both `db` and `api` services in docker-compose.yml have this restart policy. Docker automatically restarts crashed containers unless they were explicitly stopped by an operator. On a server reboot, Docker daemon restarts and brings BillWise back up.
> 2. **Health check gating** — `api` waits for `db` to be healthy before starting. If the database is temporarily down, the api container won't start in a broken state.
> 3. **Alembic idempotency** — `alembic upgrade head` is idempotent. If the container crashes mid-startup and restarts, running migrations again is safe — Alembic checks `alembic_version` and skips already-applied migrations.
> 4. **Seed idempotency** — `python -m scripts.seed` uses `get-or-create` logic. Re-running after a restart does not create duplicate plans or users.
>
> In production with Kubernetes, `Deployment` replicas and liveness/readiness probes provide the same guarantees at scale."

---

# 📅 DAY 8 — MODULE 9: DECOUPLED SAAS ARCHITECTURE, FEATURE GATING & CELERY WORKERS

### Q53: "What is a Decoupled Billing Architecture, and how does BillWise demonstrate it?"
> **Answer:**
> "In high-scale software companies, billing logic should never be tightly coupled with the core product business logic. Doing so leads to monolithic codebases where changes to pricing plans risk breaking user-facing applications.
>
> In BillWise:
> 1. The billing engine runs as a **standalone microservice** with its own database tables (Plans, Subscriptions, Invoices, Payments, Dunning).
> 2. To demonstrate real-world consumption, we built a simulated **'Cloud Infrastructure Provider'** SaaS interface.
> 3. When a customer tries to deploy a virtual server or spin up compute resources, the cloud provider queries BillWise's feature gating API (`/api/cloud/resources`) to determine:
>    - What tier is this tenant on? (`starter`, `pro`, `enterprise`)
>    - Are they within their server and CPU/RAM quotas?
>    - Is the subscription in good standing (`ACTIVE`) or past due?
> 4. If the tenant upgrades or downgrades their plan in BillWise, the cloud provider dynamically unlocks or restricts resources in real time without any code changes."

---

### Q54: "How does Dynamic Feature Gating work in BillWise? What happens when a tenant upgrades or their payment fails?"
> **Answer:**
> "Feature gating in BillWise is enforced at the backend dependency and router layer, not just by hiding UI buttons:
>
> 1. **Tier Quota Enforcement**:
>    - `Free / Starter`: Maximum 2 servers, 2 vCPUs, 4GB RAM. Premium add-ons like **Cloud Load Balancers** are locked. If a tenant attempts to deploy a Load Balancer, the API rejects the request with `403 Forbidden` (`Feature Gated`).
>    - `Pro / Enterprise`: Up to 5+ servers, 8+ vCPUs, and Cloud Load Balancers are **UNLOCKED**.
> 2. **Mid-Cycle Upgrade**:
>    - When a customer upgrades from Starter to Pro, BillWise calculates second-level proration, charges the net difference, and updates the plan ID. Instantly, the cloud console allows them to provision Load Balancers and higher compute instances.
> 3. **Payment Failure & Dunning Throttling**:
>    - If a recurring payment fails, the webhook transitions the subscription to `PAST_DUE`.
>    - The cloud provider detects the status, locks new server launches with `403 Forbidden` (`Billing Gate`), and marks active instances as `THROTTLED`.
>    - As soon as the customer or the automated dunning retry recovers the invoice payment, status returns to `ACTIVE` and compute resources are automatically un-throttled."

---

### Q55: "Why did you implement asynchronous background processing using Celery and Redis?"
> **Answer:**
> "Billing systems perform many heavy, time-consuming operations:
> - Scanning thousands of customer subscriptions to check for period renewals (`process_due_renewals`).
> - Executing dunning retry schedules across credit card gateways (`process_dunning_retries`).
> - Dispatching transactional emails (GST invoices, payment receipts, past-due dunning warnings).
>
> If we ran these synchronously inside a FastAPI request thread, HTTP requests would take multiple seconds or time out.
> By integrating **Celery** with **Redis** as the message broker:
> 1. The web application immediately enqueues a background task into Redis and returns a fast HTTP response (`202 Accepted` or `200 OK`) in under 50ms.
> 2. Dedicated Celery worker containers running in Docker pull tasks from Redis and process them concurrently without competing with the web API for CPU or event-loop threads.
> 3. Celery provides retry backoff, task tracking, and worker concurrency out of the box."

---

### Q56: "How did you design the administrative analytics and the interactive billing calendar?"
> **Answer:**
> "The Admin Control Center provides real-time financial telemetry for executive decision-making:
>
> 1. **Real-time MRR & ARR**:
>    - Monthly Recurring Revenue (MRR) is calculated by summing `plan.price_minor` for all `SubscriptionStatus.ACTIVE` tenants. ARR is projected as `MRR * 12`.
> 2. **Chart.js Financial Visualizations**:
>    - We integrated `chart.js` and `react-chartjs-2` to render a 6-month historical MRR and tax-invoiced revenue growth line chart with smooth bezier curves and responsive hover tooltips.
>    - A Doughnut chart visually communicates subscriber distribution across product tiers (Starter, Pro, Business, Enterprise).
> 3. **Global Billing Calendar**:
>    - A dedicated analytics query fetches upcoming subscription renewal dates across all tenants for the next 30 days.
>    - It renders a chronological renewal calendar showing the scheduled date, customer email, plan name, renewal fee in ₹, and status badge (`ACTIVE` vs `PAST_DUE`), allowing administrators to forecast cashflow and track impending churn risks."

---

### Q57: "Walk me through how the simulated payment gateway and webhook pipeline work end-to-end."
> **Answer:**
> "To test real-world payment scenarios without requiring live banking credentials, BillWise provides an end-to-end payment gateway simulation:
>
> 1. **Order Creation**: The customer clicks 'Pay Now' or 'Simulate Pay', triggering `POST /api/invoices/{id}/pay`. The backend creates a payment order with an ID and integer minor amount.
> 2. **Real-time Webhook Pipeline**:
>    - In production, gateways like Razorpay send an asynchronous HTTP POST to `/api/webhooks/razorpay` with a signature header (`X-Razorpay-Signature`).
>    - Our webhook listener validates the signature using constant-time `hmac.compare_digest` to prevent timing attacks.
> 3. **Interactive Simulation Modal**:
>    - In the Customer Portal, we added a dedicated simulation modal with two instant triggers:
>      - **Simulate Succeeded (200 OK)**: Captures payment, updates invoice to `PAID`, subscription to `ACTIVE`, un-throttles cloud instances, and creates a payment transaction record.
>      - **Simulate Failed (Card Declined)**: Triggers `payment.failed`, transitions subscription to `PAST_DUE`, triggers the automated dunning recovery engine, and throttles cloud compute resources.
> 4. **Idempotency**: The webhook processor checks event IDs against an idempotency ledger, preventing duplicate charges if the gateway retries the webhook delivery."
