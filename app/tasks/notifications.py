from app.core.celery_app import celery_app

from app.services.notification_service import (
    send_subscription_created_email,
    send_payment_success_email,
    send_payment_failed_email,
    send_renewal_email,
)


@celery_app.task(name="notifications.subscription_created")
def subscription_created_notification(
    email: str,
    plan_name: str,
    end_date: str,
):
    send_subscription_created_email(
        email=email,
        plan_name=plan_name,
        end_date=end_date,
    )


@celery_app.task(name="notifications.payment_success")
def payment_success_notification(
    email: str,
    invoice_number: str,
    amount: float,
    currency: str,
):
    send_payment_success_email(
        email=email,
        invoice_number=invoice_number,
        amount=amount,
        currency=currency,
    )


@celery_app.task(name="notifications.payment_failed")
def payment_failed_notification(
    email: str,
    invoice_number: str,
    amount: float,
    currency: str,
):
    send_payment_failed_email(
        email=email,
        invoice_number=invoice_number,
        amount=amount,
        currency=currency,
    )


@celery_app.task(name="notifications.renewal")
def renewal_notification(
    email: str,
    invoice_number: str,
    plan_name: str,
    amount: float,
    currency: str,
):
    send_renewal_email(
        email=email,
        invoice_number=invoice_number,
        plan_name=plan_name,
        amount=amount,
        currency=currency,
    )