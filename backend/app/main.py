from fastapi import FastAPI

from app.api import health

app = FastAPI(
    title="BillWise API",
    version="0.1.0",
    description="Subscription billing platform",
)

app.include_router(health.router)
