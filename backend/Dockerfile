# ─────────────────────────────────────────────────────────────────────────────
# Stage 1: builder — Install all packages including compile-time tools
#          This layer is DISCARDED from the final image.
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

# Install build tools needed to compile native Python extensions
# (asyncpg uses a C extension, reportlab needs libjpeg, bcrypt needs gcc)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install directly to a custom prefix so we can COPY just the site-packages
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ─────────────────────────────────────────────────────────────────────────────
# Stage 2: runtime — Lean production image, no build tools, no compilers
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

LABEL maintainer="BillWise <admin@billwise.com>" \
      description="BillWise SaaS Subscription Billing Platform — FastAPI Backend"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Tell Python where our custom prefix packages are installed
    PYTHONPATH="/app"

# Only copy runtime libraries (no gcc, no libjpeg-dev, no build artifacts)
COPY --from=builder /install /usr/local

WORKDIR /app

# Copy application code
COPY . .

EXPOSE 8000

# Default command is overridden by docker-compose.yml
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
