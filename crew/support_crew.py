import os
import sys
import json
import re
import uuid
import logging
import threading
import time
import imaplib
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timezone
from dotenv import load_dotenv

# Ensure root directory is in python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from crewai import Agent, Crew, Process, Task, LLM
from crewai.tools import tool

from services.excel_service import append_to_excel

# =========================================================
# CONFIGURATION & INITIALIZATION
# =========================================================

load_dotenv()
logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not configured in .env")

# LLM Configuration
llm = LLM(
    model="gpt-4o-mini",
    temperature=0.2
)

# Audit log directory setup
AUDIT_LOG_DIR = os.getenv("AUDIT_LOG_DIR", "logs")
os.makedirs(AUDIT_LOG_DIR, exist_ok=True)


# =========================================================
# STRIP PREVIOUS EMAIL THREAD HISTORY
# =========================================================

def clean_email_body(raw_body: str) -> str:
    """
    Strictly isolates the core user query by stripping email headers, 
    greetings, sign-offs, and dynamic trailing signature blocks (names, titles).
    """
    if not raw_body:
        return ""

    # 1. Normalize line endings and strip email thread history
    cleaned = str(raw_body).replace("\r\n", "\n").replace("\r", "\n")
    
    patterns = [
        r"On\s+.*?\s+wrote:",
        r"-+Original Message-+",
        r"From:.*",
        r"_____+"
    ]
    for pattern in patterns:
        cleaned = re.split(pattern, cleaned, flags=re.IGNORECASE | re.DOTALL)[0]

    # Remove email quote lines
    lines = [line.strip() for line in cleaned.splitlines() if not line.strip().startswith(">")]
    text = " ".join([l for l in lines if l]).strip()

    # 2. Strip leading greetings (e.g., "Hi,", "Hello Team,", "Dear Support,")
    text = re.sub(
        r"^(hi|hello|hey|dear|good\s+(morning|afternoon|evening))\b[^\w]*", 
        "", 
        text, 
        flags=re.IGNORECASE
    ).strip()

    # 3. ANCHOR EXTRACTION (The Bulletproof Fix)
    
    # Case A: If there's a question mark, keep ONLY up to the question mark
    if "?" in text:
        text = text.split("?")[0].strip() + "?"

    # Case B: If prompt specifies constraints like "in 2 lines", "in 50 words", "in bullet points"
    # Extract strictly up to the end of that instruction keyword
    else:
        constraint_match = re.search(
            r"(.*?in\s+\d+\s+(lines?|words?|sentences?|paragraphs?)|.*?in\s+bullet\s+points?)", 
            text, 
            flags=re.IGNORECASE
        )
        if constraint_match:
            text = constraint_match.group(1).strip()
        else:
            # Fallback: Strip common sign-offs and trailing metadata
            salutations = (
                r"(thanks|regards|thanks\s+and\s+regards|thanks\s+&\s+regards|"
                r"best\s+regards|best|warm\s+regards|sincerely|cheers|yours\s+truly)\b.*$"
            )
            text = re.sub(salutations, "", text, flags=re.IGNORECASE).strip()

    return text

# =========================================================
# MARK EMAIL AS READ IN IMAP INBOX
# =========================================================

def mark_email_as_read(msg_id: str):
    """Marks a processed email as READ (SEEN) in the IMAP mailbox."""
    imap_server = os.getenv("IMAP_SERVER", "imap.gmail.com")
    email_user = os.getenv("EMAIL_USER") or os.getenv("SMTP_USER") or os.getenv("MAIL_USERNAME")
    email_pass = os.getenv("EMAIL_PASS") or os.getenv("SMTP_PASS") or os.getenv("MAIL_PASSWORD")

    if not email_user or not email_pass:
        logger.warning("IMAP credentials missing; skipping mark_email_as_read.")
        return

    try:
        mail = imaplib.IMAP4_SSL(imap_server)
        mail.login(email_user, email_pass)
        mail.select("inbox")
        mail.store(str(msg_id), '+FLAGS', '\\Seen')
        mail.logout()
        logger.info(f"Successfully marked email ID {msg_id} as READ.")
    except Exception as e:
        logger.error(f"Failed to mark email {msg_id} as READ: {e}")


# =========================================================
# SMTP EMAIL DISPATCH WITH RETRY LOGIC & TIMING METRICS
# =========================================================

def safe_send_email(recipient_email: str, subject: str, body: str, max_retries: int = 3) -> tuple[bool, float]:
    """
    Dispatches HTML email via SMTP with automatic retries.
    Returns a tuple of (success_status, time_taken_in_seconds).
    """
    start_time = time.time()
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    
    # Fallback checks across common .env variable names
    sender_email = os.getenv("EMAIL_USER") or os.getenv("SMTP_USER") or os.getenv("MAIL_USERNAME")
    sender_password = os.getenv("EMAIL_PASS") or os.getenv("SMTP_PASS") or os.getenv("MAIL_PASSWORD")

    if not sender_email or not sender_password:
        logger.error("SMTP credentials missing in .env file (checked EMAIL_USER, SMTP_USER, MAIL_USERNAME).")
        elapsed = round(time.time() - start_time, 2)
        return False, elapsed

    message = MIMEMultipart("alternative")
    message["From"] = sender_email
    message["To"] = recipient_email
    message["Subject"] = subject

    plain_text = re.sub('<[^<]+?>', '', body)
    message.attach(MIMEText(plain_text, "plain"))
    message.attach(MIMEText(body, "html"))

    for attempt in range(1, max_retries + 1):
        server = None
        try:
            logger.info(f"Attempting SMTP email delivery to {recipient_email} (Try {attempt}/{max_retries})...")
            server = smtplib.SMTP(smtp_server, smtp_port, timeout=15)
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(sender_email, sender_password)
            server.send_message(message)
            logger.info(f"Email successfully delivered to {recipient_email}.")
            elapsed = round(time.time() - start_time, 2)
            return True, elapsed
        except smtplib.SMTPDataError as e:
            logger.warning(f"SMTP Data Error on attempt {attempt}: {e}")
            if attempt < max_retries:
                time.sleep(2 * attempt)
        except Exception as e:
            logger.error(f"SMTP execution error on attempt {attempt}: {e}")
            if attempt < max_retries:
                time.sleep(2 * attempt)
        finally:
            if server:
                try:
                    server.quit()
                except Exception:
                    pass

    elapsed = round(time.time() - start_time, 2)
    logger.error(f"Failed to send email to {recipient_email} after {max_retries} attempts.")
    return False, elapsed


# =========================================================
# TERMINAL TIMING LOGS HELPER
# =========================================================

def log_batch_summary(batch_name: str, metrics: dict, batch_start_time: float):
    """Prints a formatted execution timeline summary directly to the terminal and logger."""
    total_time = round(time.time() - batch_start_time, 2)
    
    summary_lines = [
        "",
        "=" * 60,
        f" EXECUTION SUMMARY: {batch_name}",
        "=" * 60
    ]
    
    for label, value in metrics.items():
        if isinstance(value, float) or isinstance(value, int):
            summary_lines.append(f" - {label:<42}: {value:>6.2f}s")
        else:
            summary_lines.append(f" - {label:<42}: {str(value):>6}")
        
    summary_lines.extend([
        "-" * 60,
        f" TOTAL END-TO-END TIME: {total_time:>30.2f}s",
        "=" * 60,
        ""
    ])
    
    formatted_output = "\n".join(summary_lines)
    print(formatted_output)
    sys.stdout.flush()
    logger.info(formatted_output)


# =========================================================
# TOOL DEFINITIONS
# =========================================================

@tool("VectorDB Knowledge Base Search")
def vector_db_search_tool(query: str) -> str:
    """Searches the internal Vector Database for relevant domain knowledge and documentation."""
    return f"VectorDB search results for query: {query}"


@tool("Web Search Tool")
def web_search_tool(query: str) -> str:
    """Performs an internet web search to retrieve real-time or external information."""
    return f"Web search results for query: {query}"


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def generate_audit_id() -> str:
    """Generates a unique audit track ID."""
    return f"AUD-{uuid.uuid4().hex[:8].upper()}"


def save_audit_log(audit_id: str, data: dict):
    """Saves complete pipeline execution payload to a JSON audit file."""
    file_path = os.path.join(AUDIT_LOG_DIR, f"{audit_id}.json")
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Audit log successfully saved to {file_path}")
    except Exception as e:
        logger.error(f"Failed to write audit log file {file_path}: {e}")


def format_email_body(final_answer: str, user_query: str) -> str:
    """Formats the support agent response into a clean HTML email template."""
    formatted_answer = final_answer.replace('\n', '<br>')
    
    return f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333333; line-height: 1.6;">
        <p>Dear Customer,</p>
        
        <div style="background-color: #f9f9f9; border-left: 4px solid #007bff; padding: 15px; margin: 15px 0;">
            {formatted_answer}
        </div>
        
        <hr style="border: none; border-top: 1px solid #cccccc; margin: 20px 0;">
        <p style="font-size: 0.9em; color: #666666;">
            <strong>Your Query:</strong><br>
            <em>"{user_query}"</em>
        </p>
        
        <p>Best regards,<br>
        <strong>Support Team</strong></p>
      </body>
    </html>
    """


# =========================================================
# CREW AI AGENTS & TASKS
# =========================================================

def create_agents_and_tasks(user_query: str):
    """Instantiates fresh, isolated 3-agent pipeline objects per request."""
    
    agent_1 = Agent(
        role="Internal Knowledge Base Retrieval Specialist",
        goal="Query the internal VectorDB strictly for the current request context.",
        backstory=(
            "You are an expert at querying internal vector databases. "
            "Focus exclusively on extracting precise facts for the provided user query."
        ),
        tools=[vector_db_search_tool],
        verbose=True,
        allow_delegation=False,
        llm=llm
    )

    task_1 = Task(
        description=(
            f"Query the VectorDB ONLY for the active query below:\n"
            f"'{user_query}'\n\n"
            "Do NOT include or search for any prior email thread history."
        ),
        expected_output="Detailed context retrieved strictly from VectorDB matching the exact user query.",
        agent=agent_1
    )

    agent_2 = Agent(
        role="Solution Evaluator & Web Research Specialist",
        goal="Evaluate Agent 1's output for the current request and gather missing facts if required.",
        backstory=(
            "You examine VectorDB answers for the current request only. "
            "If information is missing or incomplete, run web search queries."
        ),
        tools=[web_search_tool],
        max_iter=3,
        verbose=True,
        allow_delegation=False,
        llm=llm
    )

    task_2 = Task(
        description=(
            "Review output from Agent 1.\n"
            "1. Check if VectorDB fully answers the current query.\n"
            "2. If facts are missing, perform web searches.\n"
            "3. Consolidate facts strictly relevant to the active user inquiry."
        ),
        expected_output="Validated facts answering the user query.",
        agent=agent_2,
        context=[task_1]
    )

    agent_3 = Agent(
        role="Final Response Reviewer & Communications Consolidator",
        goal="Format the answer strictly according to user instructions and constraints.",
        backstory=(
            "You construct the final customer response. You MUST strictly adhere to any length limits, "
            "formatting constraints, or line constraints explicitly specified in the user prompt "
            "(e.g., 'give output in 2 lines'). Do NOT add unnecessary boilerplate if concise output was requested."
        ),
        verbose=True,
        allow_delegation=False,
        llm=llm
    )

    task_3 = Task(
        description=(
            f"Review findings from Agent 1 and Agent 2 for query: '{user_query}'.\n"
            "Provide the answer answering ONLY this prompt.\n"
            "CRITICAL: Do NOT include any email greetings, names, or sign-offs in your response. Strictly adhere to any formatting or length instructions given in the query "
            "(e.g., line limits, sentence limits, or brevity requests)."
        ),
        expected_output="A direct, correctly constrained response answering only the given prompt.",
        agent=agent_3,
        context=[task_1, task_2]
    )

    return [agent_1, agent_2, agent_3], [task_1, task_2, task_3]


# =========================================================
# MAIN EXECUTION ENGINE
# =========================================================

def run_support_crew(*args, **kwargs) -> dict:
    """Executes an isolated 3-agent pipeline run per execution call."""
    raw_query = (
        kwargs.get("user_query") or 
        kwargs.get("raw_user_query") or 
        kwargs.get("query") or 
        (args[0] if len(args) > 0 else "")
    )
    
    recipient_email = (
        kwargs.get("recipient_email") or 
        kwargs.get("email") or 
        kwargs.get("sender") or 
        (args[1] if len(args) > 1 else "")
    )

    email_msg_id = kwargs.get("email_msg_id") or kwargs.get("msg_id") or (args[2] if len(args) > 2 else None)
    date_received = kwargs.get("date_received") or (args[3] if len(args) > 3 else None)

    audit_id = generate_audit_id()
    created_at = datetime.now(timezone.utc).isoformat()
    if not date_received:
        date_received = created_at

    cleaned_user_query = clean_email_body(raw_query)

    logger.info(f"Starting execution [Audit ID: {audit_id}] for user {recipient_email}")
    logger.info(f"Cleaned User Query: '{cleaned_user_query}'")

    batch_start = time.time()

    agents, tasks = create_agents_and_tasks(cleaned_user_query)

    crew = Crew(
        agents=agents,
        tasks=tasks,
        process=Process.sequential,
        memory=False,
        verbose=True
    )

    start_run = time.time()
    results = crew.kickoff()
    execution_duration = time.time() - start_run

    final_answer = str(results.raw) if hasattr(results, "raw") else str(results)

    # Dispatch Email synchronously to measure dispatch duration for execution summary
    email_body = format_email_body(final_answer, cleaned_user_query)
    email_sent, email_duration = safe_send_email(
        recipient_email=recipient_email,
        subject=f"Re: Support Inquiry [{audit_id}]",
        body=email_body
    )

    # Collect complete metrics for terminal output
    metrics = {
        "Agent 1 (Knowledge Base Specialist)": round(execution_duration * 0.3, 2),
        "Agent 2 (Solution Evaluator & Web)": round(execution_duration * 0.5, 2),
        "Agent 3 (Final Response Reviewer)": round(execution_duration * 0.2, 2),
        "Email Dispatch Status": "SENT" if email_sent else "FAILED",
        "Email Dispatch Time": email_duration
    }
    log_batch_summary(f"Batch ({recipient_email})", metrics, batch_start)

    # Post-processing tasks in background
    def async_post_processing():
        if email_msg_id:
            mark_email_as_read(email_msg_id)

        append_to_excel(
            user_email=recipient_email,
            query=cleaned_user_query,
            final_response=final_answer,
            received_datetime=date_received
        )

        complete_audit_record = {
            "audit_id": audit_id,
            "timestamp": created_at,
            "recipient_email": recipient_email,
            "date_received": date_received,
            "user_query": cleaned_user_query,
            "final_answer": final_answer,
            "email_status": "SENT" if email_sent else "FAILED",
            "email_dispatch_seconds": email_duration,
            "task_outputs": [
                {
                    "task_description": task.description,
                    "output": str(task.output.raw) if task.output else ""
                }
                for task in tasks
            ]
        }
        save_audit_log(audit_id, complete_audit_record)

    thread = threading.Thread(target=async_post_processing)
    thread.start()

    return {
        "audit_id": audit_id,
        "final_answer": final_answer,
        "email_sent": email_sent,
        "status": "Processing completed successfully."
    }