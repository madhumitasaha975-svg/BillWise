from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
import random
import httpx
import asyncio
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/mock-bank",
    tags=["Mock Payment Gateway"]
)

# --- SCHEMAS ---
class ChargeRequest(BaseModel):
    invoice_id: str
    customer_id: str
    amount: float
    currency: str = "USD"

class RefundRequest(BaseModel):
    invoice_id: str
    customer_id: str
    amount: float
    currency: str = "USD"

# --- WEBHOOK DISPATCHER (Background Task) ---
async def process_and_send_webhook(charge_data: ChargeRequest):
    """
    Simulates talking to the bank, calculating success/failure, 
    and dispatching the webhook back to our core system.
    """
    # 1. Simulate bank processing time (2 seconds)
    await asyncio.sleep(2)
    
    # 2. The 80/20 Probabilistic Engine
    # 80% chance of 'succeeded', 20% chance of 'failed'
    outcome = random.choices(["succeeded", "failed"], weights=[0.8, 0.2])[0]
    
    # 3. Construct the Stripe-like Event Payload
    event_type = f"payment_intent.{outcome}"
    
    webhook_payload = {
        "event_id": f"evt_{random.randint(100000, 999999)}",
        "type": event_type,
        "data": {
            "invoice_id": charge_data.invoice_id,
            "customer_id": charge_data.customer_id,
            "amount_attempted": charge_data.amount,
            "currency": charge_data.currency,
            "status": outcome,
            "failure_reason": "insufficient_funds" if outcome == "failed" else None
        }
    }
    
    # 4. Dispatch the Webhook back to our own server
    # We are posting to localhost because both the mock bank and our app live on the same server right now
    target_webhook_url = "http://127.0.0.1:8000/webhooks/payments"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(target_webhook_url, json=webhook_payload)
            logger.info(f"Dispatched webhook {event_type} to {target_webhook_url} | Response: {response.status_code}")
    except Exception as e:
        logger.error(f"Failed to send mock webhook: {e}")

# --- REFUND WEBHOOK DISPATCHER ---
async def process_and_send_refund_webhook(refund_data: RefundRequest):
    """Simulates processing a refund and dispatching the refunded webhook."""
    await asyncio.sleep(2) # Simulate bank processing time
    
    event_type = "payment_intent.refunded"
    
    webhook_payload = {
        "event_id": f"evt_{random.randint(100000, 999999)}",
        "type": event_type,
        "data": {
            "invoice_id": refund_data.invoice_id,
            "customer_id": refund_data.customer_id,
            "amount_attempted": refund_data.amount,
            "currency": refund_data.currency,
            "status": "refunded",
            "failure_reason": None
        }
    }
    
    target_webhook_url = "http://127.0.0.1:8000/webhooks/payments"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(target_webhook_url, json=webhook_payload)
            logger.info(f"Dispatched webhook {event_type} to {target_webhook_url} | Response: {response.status_code}")
    except Exception as e:
        logger.error(f"Failed to send mock refund webhook: {e}")


# --- THE MAIN PAYMENT ENDPOINT ---
@router.post("/charge")
async def create_charge(request: ChargeRequest, background_tasks: BackgroundTasks):
    """
    Endpoint called by the frontend/backend to initiate a payment.
    Instantly returns 'processing' and hands the heavy lifting to the background.
    """
    # Pass the heavy processing and webhook dispatching to a background thread
    background_tasks.add_task(process_and_send_webhook, request)
    
    # Return immediately to the user (Fast UX)
    return {
        "status": "processing",
        "message": "Payment is being processed by the bank. A webhook will be fired upon completion."
    }

# --- THE REFUND ENDPOINT ---
@router.post("/refund")
async def create_refund(request: RefundRequest, background_tasks: BackgroundTasks):
    """Initiates a refund back to the customer's card."""
    background_tasks.add_task(process_and_send_refund_webhook, request)
    
    return {
        "status": "processing",
        "message": "Refund initiated. A webhook will be fired upon completion."
    }