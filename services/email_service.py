import os
import smtplib
import imaplib
import email
from email.header import decode_header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from typing import List, Dict

from dotenv import load_dotenv

# =========================================================
# ENVIRONMENT & LOGGING
# =========================================================

load_dotenv()
logger = logging.getLogger(__name__)

# =========================================================
# EMAIL CONFIGURATION
# =========================================================

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))

IMAP_SERVER = os.getenv("IMAP_SERVER", "imap.gmail.com")
IMAP_PORT = int(os.getenv("IMAP_PORT", "993"))

EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")

# =========================================================
# VALIDATE CONFIGURATION
# =========================================================

if not EMAIL_SENDER:
    raise ValueError("EMAIL_SENDER is not configured in .env")

if not EMAIL_APP_PASSWORD:
    raise ValueError("EMAIL_APP_PASSWORD is not configured in .env")


# =========================================================
# SEND EMAIL
# =========================================================

def send_email(
    recipient_email: str,
    subject: str,
    body: str
) -> bool:
    try:
        logger.info("Preparing email for %s", recipient_email)

        message = MIMEMultipart()
        message["From"] = EMAIL_SENDER
        message["To"] = recipient_email
        message["Subject"] = subject

        message.attach(MIMEText(body, "html"))

        logger.info("Connecting to Gmail SMTP")
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            logger.info("Authenticating with Gmail")
            server.login(EMAIL_SENDER, EMAIL_APP_PASSWORD)
            server.send_message(message)

        logger.info("Email sent successfully to %s", recipient_email)
        return True

    except Exception as e:
        logger.exception("Failed to send email")
        return False


# =========================================================
# FETCH UNREAD EMAILS (IMAP)
# =========================================================

def _decode_header_str(header_value: str) -> str:
    if not header_value:
        return ""
    decoded_fragments = decode_header(header_value)
    text_parts = []
    for fragment, encoding in decoded_fragments:
        if isinstance(fragment, bytes):
            text_parts.append(fragment.decode(encoding or "utf-8", errors="ignore"))
        else:
            text_parts.append(str(fragment))
    return "".join(text_parts)


def fetch_unread_emails() -> List[Dict[str, str]]:
    """
    Polls IMAP server for UNSEEN emails, parses sender email, body text,
    subject, and received timestamp, then marks emails as Seen.
    """
    fetched_emails = []

    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        mail.login(EMAIL_SENDER, EMAIL_APP_PASSWORD)
        mail.select("inbox")

        status, response = mail.search(None, "UNSEEN")
        if status != "OK":
            mail.logout()
            return fetched_emails

        email_ids = response[0].split()

        for e_id in email_ids:
            status, data = mail.fetch(e_id, "(RFC822)")
            if status != "OK":
                continue

            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)

            subject = _decode_header_str(msg.get("Subject", ""))
            from_header = _decode_header_str(msg.get("From", ""))
            date_received = msg.get("Date", "")

            sender_email = email.utils.parseaddr(from_header)[1]

            # Extract body text
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition"))

                    if content_type == "text/plain" and "attachment" not in content_disposition:
                        payload = part.get_payload(decode=True)
                        if payload:
                            body = payload.decode("utf-8", errors="ignore")
                            break
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    body = payload.decode("utf-8", errors="ignore")

            if sender_email and body.strip():
                fetched_emails.append(
                    {
                        "sender_email": sender_email,
                        "subject": subject,
                        "query": body.strip(),
                        "date_received": date_received,
                    }
                )

        mail.logout()

    except Exception as exc:
        logger.exception("Error fetching unread emails via IMAP: %s", exc)

    return fetched_emails