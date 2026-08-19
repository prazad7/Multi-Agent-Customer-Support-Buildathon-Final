import time
import logging
from datetime import datetime, timezone

from services.email_service import fetch_unread_emails
from crew.support_crew import run_support_crew

# =========================================================
# LOGGING CONFIGURATION
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app.log", encoding="utf-8")
    ]
)

logger = logging.getLogger(__name__)

# Polling Interval in seconds (default: 30 seconds)
POLL_INTERVAL_SECONDS = 30


# =========================================================
# MAIN DAEMON LOOP
# =========================================================

def process_incoming_emails():
    """
    Checks inbox for UNSEEN emails, routes each email through the 3-agent pipeline,
    sends out email replies, and appends records to support_logs.xlsx.
    """
    logger.info("Polling inbox for unread emails...")
    
    unread_emails = fetch_unread_emails()
    
    if not unread_emails:
        logger.info("No new emails found.")
        return

    logger.info("Found %d unread email(s) to process.", len(unread_emails))

    for item in unread_emails:
        sender_email = item.get("sender_email")
        query_text = item.get("query")
        date_received = item.get("date_received") or datetime.now(timezone.utc).isoformat()

        logger.info("Processing query from sender: %s", sender_email)

        try:
            # Trigger the 3-Agent Support Crew Pipeline
            result = run_support_crew(
                user_query=query_text,
                recipient_email=sender_email,
                date_received=date_received
            )
            logger.info("Execution finished for %s. Audit ID: %s", sender_email, result.get("audit_id"))

        except Exception as exc:
            logger.exception("Failed to process email from %s: %s", sender_email, exc)


def main():
    logger.info("=== Support Crew Background Daemon Started ===")
    logger.info("Polling interval set to %d seconds.", POLL_INTERVAL_SECONDS)

    try:
        while True:
            process_incoming_emails()
            time.sleep(POLL_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        logger.info("=== Support Crew Background Daemon Terminated by User ===")
    except Exception as exc:
        logger.critical("Fatal error in main loop: %s", exc, exc_info=True)


if __name__ == "__main__":
    main()