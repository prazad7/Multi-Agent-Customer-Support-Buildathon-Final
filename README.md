Markdown
# AI Support Agent & Workflow Automation

An automated email-driven customer support system built with CrewAI, Python, and OpenPyXL. The pipeline monitors incoming support emails, processes and cleans user queries using agentic AI workflows, generates concise answers, logs transaction data into Excel, and dispatches automated replies.

---

## Key Features

* **Automated Inbox Processing**: Polls incoming emails and extracts user inquiries while stripping out greetings, signatures, and email thread history.
* **Multi-Agent Orchestration**: Powered by CrewAI agents to evaluate, research, and formulate exact, constrained responses.
* **Excel Audit Logging**: Writes query records, timestamps, and responses directly to `support_logs.xlsx` with automatic retry logic and lock fallback support.
* **Automated Email Replies**: Formats responses cleanly and sends professional updates directly to the sender.

---

## Project Structure
```text
Multi-Agent-Customer-Support-Buildathon-Final/
├── crew/                     # CrewAI agent definitions, tasks, and tools
├── guardrails_config/        # Safety and prompt guardrails configuration
├── knowledge_base/           # Raw documents and domain knowledge sources
├── logs/                     # Folder for runtime application execution logs
├── rag/                      # Retrieval-Augmented Generation pipeline & vector index
├── services/                 # Email (IMAP/SMTP) & Excel logging services
├── .env                      # Active environment variables (API keys, credentials)
├── .env.example              # Template for environment configuration
├── .gitignore                # Ignored files (e.g., support_logs.xlsx, venv)
├── app.log                   # Active system log file
├── main.py                   # Primary application entry point & execution loop
├── README.md                 # Project documentation
├── requirements.lock         # Locked dependency versions
├── requirements.txt          # Primary Python dependencies
└── support_logs.xlsx         # Dynamic Excel audit trail for processed queries

Setup & Installation
--------------------
1. Prerequisites
   Python 3.10+ installed.
   A Gmail account with 2-Step Verification enabled and an App Password generated.

2. Install Dependencies
Bash
git clone <repository-url>
cd Multi-Agent-Customer-Support-Buildathon-Final
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
Configuration (.env)
Copy .env.example to .env and fill in your credentials:

Bash
cp .env.example .env
Set the following variables inside .env:

Code snippet
# OpenAI / LLM Credentials
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL_NAME=gpt-4o-mini

# Email Credentials
EMAIL_USER=your_support_email@gmail.com
EMAIL_PASSWORD=your_gmail_app_password_here
IMAP_SERVER=imap.gmail.com
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

# Excel Log Configuration
EXCEL_LOG_PATH=support_logs.xlsx
EXCEL_FALLBACK_PATH=support_logs_pending.xlsx
How to Run
Run the primary script to start monitoring incoming emails and trigger the multi-agent pipeline:

Bash
python main.py