from fastapi import FastAPI
from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
from app.api.cloud import router as cloud_router
from app.api.health import router as health_router
from app.api.payments import router as payments_router
from app.api.subscriptions import router as subscriptions_router
from app.api.webhooks import router as webhooks_router

app = FastAPI(
    title="BillWise API",
    version="0.1.0",
    description="Subscription billing platform",
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(subscriptions_router)
app.include_router(payments_router)
app.include_router(webhooks_router)
app.include_router(admin_router)
app.include_router(cloud_router)