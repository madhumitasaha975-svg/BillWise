# BillWise

A subscription billing platform: plans, subscription lifecycle, invoices with proration,
payment gateway + webhooks, dunning, PDF invoices, and a React frontend.

> Status: Module 1 (Foundations) - see [PROGRESS.md](PROGRESS.md).

## Quick start (backend)

```bash
cp .env.example .env
docker compose up -d db              # Postgres only
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head                 # create tables
python -m scripts.seed               # plans + admin + customer
uvicorn app.main:app --reload        # http://localhost:8000/docs
pytest                               # run tests
```

## Architecture rules
- Layers: `api` (HTTP only) -> `services` (business logic) -> `repositories` (DB access)
- Money = integer paise, never floats. All datetimes are UTC, timezone-aware.
- Subscription status changes go through an explicit state machine.
- Secrets live in `.env` only.
