# 🚀 BillWise Master Project Handoff & Architecture Blueprint

> **NOTE FOR ANY AI ASSISTANT OR ENGINEER READING THIS:**  
> This document is the single source of truth for **BillWise: A Decoupled SaaS Automated Billing and Subscription Management Platform**. It details the full system architecture, backend APIs, mathematical engines, database models, frontend interfaces, credentials, testing suites, and instructions for how to run and extend the codebase.

---

## 📌 1. Project Overview & Metadata

- **Project Title**: BillWise: A Decoupled SaaS Automated Billing and Subscription Management Platform
- **Origin / Context**: Enterprise-grade SaaS subscription billing platform built according to modern production standards and Infosys Springboard Virtual Internship 7.0 requirements.
- **Repository**: Git on branch `build` (pushed to `origin/build` at `https://github.com/madhumitasaha975-svg/BillWise.git`).
- **Core Technology Stack**:
  - **Backend**: Python 3.12/3.13, FastAPI (async), SQLAlchemy 2.0 (AsyncSession), PostgreSQL 16/17 (asyncpg), Alembic, Pydantic v2, PyJWT, Passlib (bcrypt), ReportLab, Celery 5.3, Redis 7.
  - **Frontend**: React 19, Vite 8, Tailwind CSS v4, Lucide React, Chart.js (`react-chartjs-2`), Axios (with JWT interceptors), React Router DOM v7.
  - **DevOps & Containers**: Docker Multi-Stage Build (`python:3.12-slim`), Docker Compose (db on 5433:5432, redis on 6379, api on 8000, worker).
  - **Testing**: Pytest 9, AnyIO, HTTPX AsyncClient — **33 Automated Tests (100% Passing)**.

---

## 🏛️ 2. Architectural Pillars & Core Engineering Decisions

### 1. Decoupled Billing Microservice Architecture
Billing logic is **never coupled** with core product business logic. BillWise runs as an independent financial control plane. To demonstrate this in action, we built a simulated **"Cloud Infrastructure Provider"** SaaS console where customers deploy compute servers. The cloud provider queries BillWise's feature gating APIs (`/api/cloud/resources`) to check quotas and lock/unlock features based on active subscription status.

### 2. Zero Floating-Point Precision Drift (Integer Paise)
All currency values are stored as **integers in minor units** (paise for INR, cents for USD). Example: `₹1,499.00` is stored as `149900`. Floating-point math (`0.1 + 0.2 = 0.30000000000000004`) causes balance drift across thousands of cycles. Integer math guarantees exact tax calculations and balance consistency.

### 3. Strict Finite State Machine
Subscription lifecycles follow legal transitions:
$$\text{TRIALING} \longrightarrow \text{ACTIVE} \longleftrightarrow \text{PAST\_DUE} \longrightarrow \text{SUSPENDED} \longrightarrow \text{CANCELLED}$$
Illegal transitions (e.g., jumping from `CANCELLED` back to `ACTIVE` or `TRIALING` straight to `SUSPENDED`) raise `IllegalTransitionError`.

### 4. Second-Level Proration Engine
When a customer changes plans mid-cycle, BillWise calculates the exact unused seconds on the old plan and credits the customer:
$$\text{Unused Credit} = \text{Old Price} \times \frac{\text{Remaining Seconds}}{\text{Total Cycle Seconds}}$$
It then calculates the remaining seconds on the new plan and charges the customer:
$$\text{Remaining Charge} = \text{New Price} \times \frac{\text{Remaining Seconds}}{\text{Total Cycle Seconds}}$$
$$\text{Net Immediate Due} = \max(0, \text{Remaining Charge} - \text{Unused Credit})$$
Itemized as separate `PRORATION_CHARGE` and `PRORATION_CREDIT` line items on the invoice.

### 5. Automated Dunning Engine (Involuntary Churn Recovery)
When recurring payment charges fail:
- Status transitions `ACTIVE -> PAST_DUE` with an active grace period.
- Background worker schedules automated retries on **Day 1, Day 3, and Day 5**.
- If retry succeeds: transitions back `PAST_DUE -> ACTIVE`, invoice marked `PAID`.
- If 3 retries fail (`MAX_DUNNING_ATTEMPTS = 3`): transitions `PAST_DUE -> SUSPENDED`, cloud compute throttled.
- Every state change is recorded in an immutable `AuditLog` table.

### 6. Stateless In-Memory PDF Invoicing
ReportLab tax invoices are generated directly inside an in-memory byte buffer (`io.BytesIO`) and streamed over HTTP with `application/pdf`. Zero temporary files are written to disk, eliminating server disk exhaustion risks. Protected by Insecure Direct Object Reference (IDOR) checks.

### 7. Asynchronous Task Processing with Celery & Redis
Heavy recurring operations (batch renewal scanning, payment retries, transactional notifications) run asynchronously via Celery workers pulling tasks from Redis, ensuring web API responses always return in $< 50\text{ms}$.

---

## 🗄️ 3. Database Architecture & Alembic Migrations

The database consists of **11 tables** managed via async Alembic migrations in `backend/alembic/versions/`:

### Migration 1: `76a2986cfdf6_create_initial_billing_tables.py`
1. **`users`**: `id` (UUID), `email` (unique index), `hashed_password` (bcrypt), `role` (`admin` | `customer`), `is_active`, `created_at`, `updated_at`.
2. **`customers`**: `id` (UUID), `user_id` (FK `users.id`), `name`, `phone`, `razorpay_customer_id`, timestamps.
3. **`plans`**: `id` (UUID), `code` (unique: `free`, `starter`, `pro`, `business`, `enterprise`), `name`, `price_minor` (paise), `currency` (`INR`), `billing_interval` (`monthly`, `yearly`), `trial_days`, `is_active`.
4. **`subscriptions`**: `id` (UUID), `customer_id` (FK `customers.id`), `plan_id` (FK `plans.id`), `status` (`trialing`, `active`, `past_due`, `suspended`, `cancelled`), `trial_ends_at`, `current_period_start`, `current_period_end`, `cancel_at_period_end`, `cancelled_at`.
5. **`billing_cycles`**: `id` (UUID), `subscription_id` (FK), `plan_id`, `cycle_number`, `period_start`, `period_end`, `status` (`open`, `closed`).
6. **`invoices`**: `id` (UUID), `customer_id` (FK), `subscription_id` (FK), `number` (e.g. `INV-2026-000001`), `status` (`draft`, `open`, `paid`, `void`), `currency`, `subtotal_minor`, `tax_minor` (18% GST), `total_minor`, `due_date`, `paid_at`.
7. **`invoice_line_items`**: `id` (UUID), `invoice_id` (FK), `description`, `kind` (`base_fee`, `proration_credit`, `proration_charge`), `amount_minor`.
8. **`payments`**: `id` (UUID), `invoice_id` (FK), `amount_minor`, `currency`, `status` (`pending`, `succeeded`, `failed`), `gateway` (`razorpay`, `fake`), `gateway_order_id`, `gateway_payment_id`.
9. **`idempotency_keys`**: `id` (UUID), `key` (unique), `user_id`, `request_path`, `request_hash` (SHA-256), `response_status`, `response_body`.
10. **`audit_logs`**: `id` (UUID), `actor_user_id` (FK `users.id`), `action`, `entity_type`, `entity_id`, `details` (JSON), `created_at`.

### Migration 2: `c4d8e2f1a903_create_cloud_servers_table.py`
11. **`cloud_servers`**: `id` (UUID), `customer_id` (FK `customers.id`), `name`, `region` (`ap-south-1`, etc.), `vcpus` (int), `ram_gb` (int), `has_load_balancer` (bool), `status` (`RUNNING`, `THROTTLED`, `STOPPED`), `created_at`.

---

## 🔌 4. Backend Endpoints Breakdown

All endpoints registered in `backend/app/main.py`:

### Authentication & Token Rotation (`/api/auth`)
- `POST /api/auth/register` — Creates user + customer profile (bcrypt salt).
- `POST /api/auth/login` — Verifies password, returns `access_token` (30m) & `refresh_token` (7d).
- `POST /api/auth/refresh` — Rotates tokens transparently on 401 without user logout.

### Subscriptions & Proration (`/api/subscriptions`)
- `GET /api/subscriptions/me` — Fetches active customer subscription and plan details.
- `GET /api/subscriptions/{id}` — Fetches subscription by ID (tenant checked).
- `POST /api/subscriptions/{id}/change-plan` — Mid-cycle plan upgrade/downgrade with atomic second-level proration calculation and invoice line items.

### Invoices, Payments & Simulator (`/api/invoices`)
- `GET /api/invoices/me` — Lists customer invoices with status, line items, and GST breakdown.
- `POST /api/invoices/{id}/pay` — Initiates payment order on gateway (Razorpay or fake gateway).
- `POST /api/invoices/{id}/simulate-payment` — **Interactive Demo Endpoint**: accepts `{"outcome": "succeeded" | "failed"}` to immediately simulate real-time gateway webhook responses, transitions, and cloud resource state.
- `GET /api/invoices/{id}/pdf` — Streams ReportLab PDF tax invoice with GSTIN and IDOR protection.

### Webhook Listener (`/api/webhooks`)
- `POST /api/webhooks/razorpay` — HMAC-SHA256 signature verification (`hmac.compare_digest`), idempotent processing, transitions invoices to `PAID` and subscriptions to `ACTIVE` on `payment.captured`, or `PAST_DUE` on `payment.failed`.

### Decoupled Cloud Infrastructure & Feature Gating (`/api/cloud`)
- `GET /api/cloud/resources` — Returns current plan tier, quota limits, compute usage, server list, and lock status.
- `POST /api/cloud/servers` — Provisions a simulated server. Rejects with `403 Forbidden` if:
  - User exceeds server quota for tier (Starter: 2, Pro: 5).
  - User exceeds vCPU/RAM limits.
  - User requests Load Balancer on Free/Starter (`Feature Gated`).
  - Subscription status is `PAST_DUE` or `SUSPENDED` (`Billing Gate`).
- `DELETE /api/cloud/servers/{id}` — Terminates instance and frees quota.

### Admin Control Plane & Analytics (`/api/admin`, Protected: `require_admin`)
- `GET /api/admin/metrics` — Overall totals: Revenue Collected, Active Subscribers, Past-due Count, Invoice count.
- `GET /api/admin/analytics` — **Chart.js & Calendar Data**: MRR, ARR, 6-Month MRR Growth Trend, Plan Tier Distribution, and Upcoming 30-Day Billing Renewal Calendar.
- `GET /api/admin/subscriptions` — Lists all tenant subscription contracts.
- `GET /api/admin/audit-logs` — Immutable audit log feed.
- `POST /api/admin/trigger-renewals` — Manually triggers background subscription renewal scanner.
- `POST /api/admin/trigger-dunning` — Manually triggers automated dunning retry engine.

---

## 🎨 5. Frontend Structure & Key Components

Located in `D:/BILLWISE/BillWise/frontend/src`:

```
src/
├── api/
│   └── client.js             # Central Axios instance with JWT injection & 401 token refresh
├── context/
│   └── AuthContext.jsx       # Global Auth state, atob claim decoding, login/logout
├── components/
│   ├── Navbar.jsx            # Dynamic navbar with role badge, links, logout
│   ├── ChangePlanModal.jsx   # Mid-cycle upgrade modal with proration math feedback
│   └── SimulatePaymentModal.jsx # 1-Click Payment Gateway simulator (succeeded / failed)
├── pages/
│   ├── LandingPage.jsx       # 3D tilted mockup, floating depth cards, live proration visualizer
│   ├── Login.jsx             # Sign In with 1-Click Demo Buttons (Customer & Admin)
│   ├── Register.jsx          # Tenant Registration form with 1-Click Demo Fill
│   ├── CustomerDashboard.jsx # Dual-tab portal: Billing & Invoices + Cloud Console
│   └── AdminDashboard.jsx    # Chart.js MRR trend, Doughnut plan split, Billing Calendar
├── App.jsx                   # React Router with ProtectedRoute role guards
└── main.jsx
```

### Key UI Features
1. **Interactive 3D Product Mockup (`LandingPage.jsx`)**: Tracks mouse movement (`rotateX`, `rotateY`, `perspective-1200`) showing the live Pro Plan control plane, cycle progress, and integer paise math.
2. **Customer Portal (`CustomerDashboard.jsx`)**:
   - **Tab 1: Billing & Invoices**: Current plan card, cycle dates, plan change modal, itemized invoice table with streaming PDF downloads and 1-click **"Simulate Pay"** button.
   - **Tab 2: Cloud Infrastructure Console**: Demonstrates decoupled feature gating. Quota meters, server cards with green running pulses, and Load Balancer locked/unlocked indicators. Throttling banner shown when in `PAST_DUE`.
3. **Admin Control Center (`AdminDashboard.jsx`)**:
   - **Chart.js Line Chart**: 6-Month historical MRR & tax-invoiced trend with bezier smoothing.
   - **Chart.js Doughnut Chart**: Active subscription distribution across tiers.
   - **Global Billing Calendar**: 30-day renewal schedule showing upcoming renewal dates, customer email, plan name, fee in ₹, and status badges.
   - **Background Job Triggers**: 1-click execution of the renewal scanner and dunning engine.
   - **Live Audit Trail**: Chronological feed of all dunning transitions and administrative actions.

---

## 👥 6. How to Use & Demonstrate the Platform

### Pre-Seeded Credentials
| Role | Email | Password | Permissions |
| :--- | :--- | :--- | :--- |
| **Administrator** | `admin@billwise.com` | `admin123` | Full access to Admin Control Center, Chart.js telemetry, job triggers, and all invoices. |
| **Customer** | `customer@billwise.com` | `customer123` | Access to Customer Portal, proration changes, cloud console, and PDF downloads. |

### Walkthrough User Flows

#### Flow 1: Customer Mid-Cycle Plan Change & Proration
1. Go to `http://localhost:5173/login` $\to$ Click **"Demo Customer"** $\to$ Sign In.
2. You are on the **Customer Portal** (`/dashboard`).
3. Under Current Plan, click **"Change / Upgrade Plan"**.
4. Select **Pro Plan (₹1,499/mo)** or **Business Plan (₹4,999/mo)**.
5. Notice the instant proration math: Unused credit from Starter is subtracted from remaining charge on Pro.
6. Confirm upgrade $\to$ A new itemized invoice appears in your table with `PRORATION_CHARGE` and `PRORATION_CREDIT` line items!
7. Click **"PDF"** to instantly stream the GST-itemized invoice compiled in RAM.

#### Flow 2: Testing Feature Gating on Cloud Console
1. In the Customer Portal, click the top tab: **"Cloud Infrastructure (Decoupled SaaS)"**.
2. Notice the quota badges: On Starter, maximum 2 servers, Load Balancer is **LOCKED**.
3. Click **"Deploy Server"** $\to$ Check "Attach Cloud Load Balancer" $\to$ It is disabled with a gold lock badge.
4. Go back to Billing $\to$ Upgrade to **Pro Plan**.
5. Return to Cloud Console $\to$ Load Balancer is now **UNLOCKED (PRO FEATURE)**! Deploy a cluster with Load Balancer attached!

#### Flow 3: Testing Payment Gateway Failure, Dunning & Throttling
1. In Customer Portal, go to **"Billing & Invoices"**.
2. Find an invoice with status `Due` or click **"Simulate Pay"** on any invoice.
3. In the modal, click **"Simulate Payment Failure (Trigger Dunning)"**.
4. Instantly:
   - Subscription shifts from `ACTIVE` to `PAST_DUE (Dunning Active)`.
   - Switch to **"Cloud Infrastructure"** tab: A high-impact warning appears: *"Cloud compute resources throttled due to Past Due billing status."* Active servers display status **THROTTLED**.
5. Return to invoices $\to$ Click **"Simulate Pay"** $\to$ Click **"Simulate Payment Success (200 OK)"**.
6. Status immediately recovers to `ACTIVE`, invoice marks `PAID`, and cloud instances return to `RUNNING`!

#### Flow 4: Administrator Telemetry & Job Triggers
1. Log out $\to$ Click **"Demo Admin"** $\to$ Sign In.
2. You are redirected to `/admin`.
3. View the top KPI cards: Total Revenue Collected in ₹, MRR, Active Tenants, and Dunning Count.
4. Inspect the **Chart.js MRR Growth Line Chart** and **Plan Tier Doughnut Chart**.
5. Scroll to the **Global Billing Calendar** to see upcoming scheduled renewals for the next 30 days.
6. Click **"Trigger Due Renewals Scanner"** or **"Trigger Dunning Retry Engine"** to see background jobs execute and log into the live audit trail!

---

## 🏃 7. How to Run the Project

### Option A: Running via Docker Compose (Recommended)

1. Make sure Docker Desktop is running.
2. From the root repository directory:
   ```powershell
   docker compose up --build
   ```
3. Docker starts:
   - `billwise-db-1` (PostgreSQL 16 on port 5433)
   - `billwise-redis-1` (Redis 7 on port 6379)
   - `billwise-api-1` (FastAPI backend on port 8000, auto-runs migrations + seed)
   - `billwise-worker-1` (Celery background worker)
4. Start the frontend:
   ```powershell
   cd frontend
   npm run dev
   ```
5. Open your browser:
   - Frontend: `http://localhost:5173`
   - Backend API Docs (Swagger): `http://localhost:8000/docs`

### Option B: Running Locally (Windows PowerShell)

#### Backend:
```powershell
cd D:\BILLWISE\BillWise\backend
# Activate virtual environment
..\venv\Scripts\Activate.ps1

# Run migrations
alembic upgrade head

# Seed initial plans & users
python -m scripts.seed

# Start FastAPI server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Frontend:
```powershell
cd D:\BILLWISE\BillWise\frontend
npm run dev
```

---

## 🧪 8. Automated Testing Verification

All 33 backend tests can be executed at any time using:

```powershell
cd D:\BILLWISE\BillWise\backend
..\venv\Scripts\pytest.exe -q
```

### Test Coverage Breakdown:
1. `tests/test_auth.py` — Registration, duplicate prevention, password validation, JWT claim decode, token rotation, RBAC.
2. `tests/test_subscription_state_machine.py` — State machine transition legality and illegal jump rejections.
3. `tests/test_proration.py` — Mathematical precision of proration credits and charges down to the exact paisa.
4. `tests/test_renewals.py` — Automated period advancement and renewal invoice generation.
5. `tests/test_payments.py` — Order creation, fake gateway simulation, HMAC-SHA256 webhook verification, idempotency replay prevention.
6. `tests/test_dunning.py` — Day 1-3-5 retry schedule, grace period, auto-suspension, audit logs.
7. `tests/test_invoices_pdf.py` — ReportLab in-memory byte rendering, GST layout, and IDOR download security.
8. `tests/test_cloud_feature_gating.py` — Decoupled SaaS cloud quotas, Load Balancer locking on Starter, unlock on Pro, and past-due compute throttling.

---

## 🗺️ 9. Suggested Future Roadmap for Any Continuing AI

If an AI assistant is asked to extend BillWise further, here are the natural next enhancements:

1. **Production Cloud Hosting**:
   - Deploy backend + PostgreSQL to **Render**, **Railway**, or **Fly.io**.
   - Deploy frontend to **Vercel** or **Cloudflare Pages**.
2. **Real Razorpay Checkout Integration**:
   - Add Razorpay standard checkout popup script (`Razorpay.open()`) in `CustomerDashboard.jsx` using the `gateway_order_id` returned by `/api/invoices/{id}/pay`.
3. **Usage-Based (Metered) Billing**:
   - Add a meter event ingestion endpoint (`POST /api/meters/event`) to bill customers dynamically based on actual CPU/RAM hours consumed on their cloud instances.
4. **Email Dispatcher Adapter**:
   - Connect Celery's `send_billing_notification_task` to SendGrid or Resend to deliver actual PDF attachments to customer email inboxes.
