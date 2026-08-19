import os
import smtplib
from email.message import EmailMessage

from dotenv import load_dotenv

load_dotenv()


SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
EMAIL_FROM = os.getenv("EMAIL_FROM", SMTP_USERNAME)


def send_email(to_email: str, subject: str, body: str):
    """Send an email through the configured SMTP server."""

    if not SMTP_USERNAME or not SMTP_PASSWORD:
        raise RuntimeError(
            "SMTP_USERNAME and SMTP_PASSWORD must be configured."
        )

    message = EmailMessage()
    message["From"] = EMAIL_FROM
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
        smtp.starttls()
        smtp.login(SMTP_USERNAME, SMTP_PASSWORD)
        smtp.send_message(message)


def send_subscription_created_email(
    email: str,
    plan_name: str,
    end_date: str,
):
    send_email(
        email,
        "Subscription Activated - BillWise",
        f"""Hello,

Your BillWise subscription has been successfully activated.

Plan: {plan_name}
Valid until: {end_date}

Thank you for using BillWise.

Regards,
BillWise Team
""",
    )


def send_payment_success_email(
    email: str,
    invoice_number: str,
    amount: float,
    currency: str,
):
    send_email(
        email,
        "Payment Successful - BillWise",
        f"""Hello,

Your payment was successfully processed.

Invoice: {invoice_number}
Amount: {amount:.2f} {currency}

Thank you for your payment.

Regards,
BillWise Team
""",
    )


def send_payment_failed_email(
    email: str,
    invoice_number: str,
    amount: float,
    currency: str,
):
    send_email(
        email,
        "Payment Failed - Action Required",
        f"""Hello,

Your recent payment could not be completed.

Invoice: {invoice_number}
Amount: {amount:.2f} {currency}

Please update your payment method and try again.

Regards,
BillWise Team
""",
    )


def send_renewal_email(
    email: str,
    invoice_number: str,
    plan_name: str,
    amount: float,
    currency: str,
):
    send_email(
        email,
        "Subscription Renewed - BillWise",
        f"""Hello,

Your BillWise subscription has been renewed successfully.

Plan: {plan_name}
Invoice: {invoice_number}
Amount: {amount:.2f} {currency}

Thank you for continuing to use BillWise.

Regards,
BillWise Team
""",
    )