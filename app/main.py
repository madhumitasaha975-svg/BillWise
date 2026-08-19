from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import database engine and Base declarative mapping
from app.database.connection import engine, Base

# Import models so SQLAlchemy knows they exist before creating tables
import app.models.core

# Import routers
from app.routers import auth
from app.api import plans
from app.api import users  
from app.api import subscriptions
from app.api import invoices

# NEW: Import the Mock Gateway and Webhooks
from app.api import mock_gateway
from app.api import webhooks

# Create all tables in the database
Base.metadata.create_all(bind=engine)

# Initialize FastAPI application
app = FastAPI(
    title="BillWise API",
    description="Backend API for the Automated Billing Platform",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all route handlers
app.include_router(auth.router)
app.include_router(plans.router)
app.include_router(users.router)  
app.include_router(subscriptions.router)
app.include_router(invoices.router)  

# NEW: Register the Mock Bank and Webhook routers
app.include_router(mock_gateway.router)
app.include_router(webhooks.router)

# Root endpoint for health check
@app.get("/")
def root():
    return {
        "status": "success", 
        "message": "BillWise API is running and database is connected!"
    }