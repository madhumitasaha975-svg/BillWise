import uuid
from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.enums import InvoiceStatus, SubscriptionStatus
from app.models.invoice import Invoice
from app.models.subscription import Subscription
from app.services.dunning_service import DunningService


async def process_dunning_retries(simulate_success: bool = False) -> int:
    """
    Scans for open invoices belonging to PAST_DUE subscriptions
    and executes a dunning retry attempt on each.
    
    Returns the count of invoices processed.
    """
    processed_count = 0

    async with SessionLocal() as session:
        # Find all open invoices whose subscription is in PAST_DUE status
        stmt = (
            select(Invoice.id)
            .join(Subscription, Invoice.subscription_id == Subscription.id)
            .where(
                Subscription.status == SubscriptionStatus.PAST_DUE,
                Invoice.status == InvoiceStatus.OPEN,
            )
        )
        result = await session.execute(stmt)
        due_invoice_ids = result.scalars().all()

        dunning_service = DunningService(session)
        for inv_id in due_invoice_ids:
            res = await dunning_service.execute_dunning_retry(
                inv_id, simulate_success=simulate_success
            )
            processed_count += 1
            print(
                f"🛡️ Dunning attempt: Invoice {res.get('invoice_number')} -> "
                f"Outcome: {res.get('status')}, "
                f"Sub Status: {res.get('subscription_status')}, "
                f"Attempt: {res.get('attempt') or res.get('attempts')}"
            )

    return processed_count
