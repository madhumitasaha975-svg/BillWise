import asyncio
import logging
from app.core.celery_app import celery_app
from app.jobs.dunning import process_dunning_retries
from app.jobs.renewals import process_due_renewals

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.process_billing_renewals")
def process_billing_renewals_task():
    """Celery background worker task for scanning and renewing due subscriptions."""
    logger.info("Executing Celery task: process_billing_renewals_task")
    count = asyncio.run(process_due_renewals())
    logger.info("Celery task completed: %d subscriptions renewed", count)
    return {"renewed_count": count}


@celery_app.task(name="tasks.process_dunning_retries")
def process_dunning_retries_task(simulate_success: bool = True):
    """Celery background worker task for dunning retry execution."""
    logger.info("Executing Celery task: process_dunning_retries_task")
    count = asyncio.run(process_dunning_retries(simulate_success=simulate_success))
    logger.info("Celery task completed: %d invoices retried", count)
    return {"retried_count": count}


@celery_app.task(name="tasks.send_billing_notification")
def send_billing_notification_task(recipient_email: str, subject: str, event_type: str, details: dict):
    """Simulated async email notification dispatcher (Invoice generated, Dunning warning, Payment receipt).
    
    Demonstrates asynchronous decoupling: Webhooks and billing jobs enqueue
    notification tasks to Redis without blocking the main FastAPI thread.
    """
    logger.info(
        "📧 [MOCK EMAIL DISPATCHED] To: %s | Subject: %s | Event: %s | Payload: %s",
        recipient_email,
        subject,
        event_type,
        details,
    )
    return {
        "status": "SENT",
        "recipient": recipient_email,
        "subject": subject,
        "event_type": event_type,
    }
