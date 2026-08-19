from datetime import datetime, timezone, timedelta

from app.core.celery_app import celery_app
from app.database.connection import SessionLocal
import app.models.core as models
from app.core import billing_math

from app.tasks.notifications import renewal_notification


@celery_app.task(name="app.tasks.billing.process_renewals")
def process_renewals():
    """
    Processes subscription billing cycles.

    Handles:
    1. Expired trials
    2. Active subscriptions due for renewal
    3. Subscriptions scheduled for cancellation
    4. Invoice generation
    5. Billing period extension
    6. Billing cycle records
    7. Renewal notifications
    """

    db = SessionLocal()

    now = datetime.now(timezone.utc)

    renewals_processed = 0
    notifications_queued = 0
    trials_expired = 0
    cancellations_processed = 0

    try:

        # ==========================================================
        # 1. HANDLE EXPIRED TRIALS
        # ==========================================================

        expired_trials = (
            db.query(models.Subscription)
            .filter(
                models.Subscription.status == models.SubscriptionState.trial,
                models.Subscription.current_period_end <= now
            )
            .all()
        )

        print(f"Found {len(expired_trials)} expired trials.")

        for sub in expired_trials:

            # ------------------------------------------------------
            # If trial was configured to cancel at period end
            # ------------------------------------------------------

            if sub.cancel_at_period_end:

                old_status = sub.status

                sub.status = models.SubscriptionState.cancelled
                sub.canceled_at = now

                db.add(
                    models.AuditLog(
                        entity_type="Subscription",
                        entity_id=sub.id,
                        action="TRIAL_AUTO_CANCELLED_AT_PERIOD_END",
                        old_value=old_status.value,
                        new_value=sub.status.value,
                    )
                )

                cancellations_processed += 1

                print(
                    f"Trial {sub.id} cancelled at period end."
                )

                continue

            # ------------------------------------------------------
            # Trial ended without cancellation.
            #
            # In a real billing system this would normally trigger
            # the first payment / invoice and move the subscription
            # to active or past_due depending on payment result.
            #
            # For this project we generate the first invoice and
            # move the subscription to active.
            # ------------------------------------------------------

            plan = (
                db.query(models.Plan)
                .filter(models.Plan.id == sub.plan_id)
                .first()
            )

            if not plan:
                print(
                    f"Plan {sub.plan_id} not found for trial {sub.id}."
                )
                continue

            try:

                invoice = billing_math.generate_standard_invoice(
                    db,
                    sub,
                    plan
                )

                # Move expired trial to active.
                old_status = sub.status
                sub.status = models.SubscriptionState.active

                # Start the paid billing period now.
                sub.current_period_start = now

                if plan.billing_interval == "annual":
                    sub.current_period_end = (
                        now + timedelta(days=365)
                    )
                else:
                    sub.current_period_end = (
                        now + timedelta(days=30)
                    )

                # Invoice due date.
                invoice.due_date = now + timedelta(days=7)

                # --------------------------------------------------
                # Billing cycle record
                # --------------------------------------------------

                db.add(
                    models.BillingCycle(
                        subscription_id=sub.id,
                        start_date=sub.current_period_start,
                        end_date=sub.current_period_end,
                        billing_date=now,
                    )
                )

                # --------------------------------------------------
                # Audit
                # --------------------------------------------------

                db.add(
                    models.AuditLog(
                        entity_type="Subscription",
                        entity_id=sub.id,
                        action="TRIAL_CONVERTED_TO_ACTIVE",
                        old_value=old_status.value,
                        new_value=sub.status.value,
                    )
                )

                db.commit()

                trials_expired += 1

                print(
                    f"Trial {sub.id} converted to ACTIVE."
                )

            except Exception as e:

                db.rollback()

                print(
                    f"Error processing expired trial "
                    f"{sub.id}: {e}"
                )

        # ==========================================================
        # 2. FIND ACTIVE SUBSCRIPTIONS DUE FOR RENEWAL
        # ==========================================================

        due_subscriptions = (
            db.query(models.Subscription)
            .filter(
                models.Subscription.status
                == models.SubscriptionState.active,

                models.Subscription.current_period_end <= now
            )
            .all()
        )

        print(
            f"Found {len(due_subscriptions)} subscriptions "
            f"due for renewal."
        )

        # ==========================================================
        # 3. PROCESS EACH RENEWAL
        # ==========================================================

        for sub in due_subscriptions:

            # ------------------------------------------------------
            # Cancellation at end of billing period
            # ------------------------------------------------------

            if sub.cancel_at_period_end:

                old_status = sub.status

                sub.status = models.SubscriptionState.cancelled
                sub.canceled_at = now

                db.add(
                    models.AuditLog(
                        entity_type="Subscription",
                        entity_id=sub.id,
                        action="AUTO_CANCELLED_AT_PERIOD_END",
                        old_value=old_status.value,
                        new_value=sub.status.value,
                    )
                )

                db.commit()

                cancellations_processed += 1

                print(
                    f"Subscription {sub.id} cancelled "
                    f"at period end."
                )

                continue

            # ------------------------------------------------------
            # Find plan
            # ------------------------------------------------------

            plan = (
                db.query(models.Plan)
                .filter(models.Plan.id == sub.plan_id)
                .first()
            )

            if not plan:

                print(
                    f"Plan {sub.plan_id} not found "
                    f"for subscription {sub.id}."
                )

                continue

            try:

                # --------------------------------------------------
                # Generate renewal invoice
                # --------------------------------------------------

                invoice = billing_math.generate_standard_invoice(
                    db,
                    sub,
                    plan
                )

                if not invoice:
                    print(
                        f"No invoice generated for "
                        f"subscription {sub.id}."
                    )
                    continue

                # --------------------------------------------------
                # Invoice due date
                # --------------------------------------------------

                invoice.due_date = now + timedelta(days=7)

                # --------------------------------------------------
                # Calculate next billing period
                # --------------------------------------------------

                new_period_start = now

                if plan.billing_interval == "annual":
                    new_period_end = (
                        now + timedelta(days=365)
                    )
                else:
                    new_period_end = (
                        now + timedelta(days=30)
                    )

                sub.current_period_start = new_period_start
                sub.current_period_end = new_period_end

                # --------------------------------------------------
                # Create BillingCycle
                # --------------------------------------------------

                billing_cycle = models.BillingCycle(
                    subscription_id=sub.id,
                    start_date=new_period_start,
                    end_date=new_period_end,
                    billing_date=now,
                )

                db.add(billing_cycle)

                # --------------------------------------------------
                # Audit renewal
                # --------------------------------------------------

                db.add(
                    models.AuditLog(
                        entity_type="Subscription",
                        entity_id=sub.id,
                        action="SUBSCRIPTION_RENEWED",
                        old_value="period_expired",
                        new_value="renewed",
                    )
                )

                db.commit()

                renewals_processed += 1

                print(
                    f"Renewed subscription {sub.id}. "
                    f"Invoice: {invoice.invoice_number}"
                )

                # --------------------------------------------------
                # Renewal notification
                # --------------------------------------------------

                customer = (
                    db.query(models.Customer)
                    .filter(
                        models.Customer.id == sub.customer_id
                    )
                    .first()
                )

                if customer:

                    try:

                        renewal_notification.delay(
                            email=customer.email,
                            plan_name=plan.name,
                            amount=invoice.amount_due,
                            next_billing_date=new_period_end.isoformat(),
                        )

                        notifications_queued += 1

                        print(
                            f"Renewal notification queued for "
                            f"{customer.email}"
                        )

                    except Exception as notification_error:

                        print(
                            f"Failed to queue renewal notification "
                            f"for subscription {sub.id}: "
                            f"{notification_error}"
                        )

            except Exception as e:

                db.rollback()

                print(
                    f"Error processing renewal "
                    f"for subscription {sub.id}: {e}"
                )

        # ==========================================================
        # 4. FINAL RESULT
        # ==========================================================

        print(
            "Billing Cycle Complete: "
            f"Processed {renewals_processed} renewals. "
            f"Expired trials: {trials_expired}. "
            f"Cancelled: {cancellations_processed}. "
            f"Queued {notifications_queued} renewal notifications."
        )

        return (
            f"Processed {renewals_processed} renewals. "
            f"Expired trials: {trials_expired}. "
            f"Cancelled: {cancellations_processed}. "
            f"Queued {notifications_queued} renewal notifications."
        )

    except Exception as e:

        db.rollback()

        print(
            f"Fatal error during billing cycle: {e}"
        )

        raise

    finally:

        db.close()