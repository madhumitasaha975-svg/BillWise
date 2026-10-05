from fastapi import FastAPI
from app.api.auth import router as auth_router
from app.api.health import router as health_router

app = FastAPI(
    title="BillWise API",
    version="0.1.0",
    description="Subscription billing platform",
)

app.include_router(health_router)
app.include_router(auth_router)