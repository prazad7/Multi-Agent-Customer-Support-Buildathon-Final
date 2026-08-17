import os
import smtplib
import logging

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from dotenv import load_dotenv


# =========================================================
# ENVIRONMENT
# =========================================================

load_dotenv()


# =========================================================
# LOGGING
# =========================================================

logger = logging.getLogger(__name__)


# =========================================================
# EMAIL CONFIGURATION
# =========================================================

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))

EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")


# =========================================================
# VALIDATE CONFIGURATION
# =========================================================

if not EMAIL_SENDER:
    raise ValueError(
        "EMAIL_SENDER is not configured in .env"
    )

if not EMAIL_APP_PASSWORD:
    raise ValueError(
        "EMAIL_APP_PASSWORD is not configured in .env"
    )


# =========================================================
# SEND EMAIL
# =========================================================

def send_email(
    recipient_email: str,
    subject: str,
    body: str
) -> bool:

    try:

        logger.info(
            "Preparing email for %s",
            recipient_email
        )

        # -------------------------------------------------
        # CREATE EMAIL
        # -------------------------------------------------

        message = MIMEMultipart()

        message["From"] = EMAIL_SENDER
        message["To"] = recipient_email
        message["Subject"] = subject

        message.attach(
            MIMEText(
                body,
                "plain"
            )
        )

        # -------------------------------------------------
        # CONNECT TO GMAIL SMTP
        # -------------------------------------------------

        logger.info(
            "Connecting to Gmail SMTP"
        )

        with smtplib.SMTP(
            SMTP_SERVER,
            SMTP_PORT
        ) as server:

            # -------------------------------------------------
            # START TLS
            # -------------------------------------------------

            server.starttls()

            # -------------------------------------------------
            # LOGIN
            # -------------------------------------------------

            logger.info(
                "Authenticating with Gmail"
            )

            server.login(
                EMAIL_SENDER,
                EMAIL_APP_PASSWORD
            )

            # -------------------------------------------------
            # SEND
            # -------------------------------------------------

            server.send_message(
                message
            )

        logger.info(
            "Email sent successfully to %s",
            recipient_email
        )

        return True

    except Exception as e:

        logger.exception(
            "Failed to send email"
        )

        return False