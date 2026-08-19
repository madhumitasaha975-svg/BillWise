from celery import Celery
from celery.schedules import crontab
import os

# Initialize Celery and connect it to your local Redis server
# NEW: We added the 'include' array so Celery knows where your task functions live!
celery_app = Celery(
    "billwise_worker",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    include=[
    "app.tasks.billing",     # <-- THIS FIXES THE ERROR
    "app.tasks.notifications",
]  
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# ---------------------------------------------------------
# CELERY BEAT SCHEDULE
# This tells Celery to wake up and run the billing task daily
# ---------------------------------------------------------
celery_app.conf.beat_schedule = {
    "daily-invoice-generation": {
        "task": "app.tasks.billing.process_renewals",
        "schedule": crontab(hour=0, minute=0), # Runs every night at midnight UTC
    }
}