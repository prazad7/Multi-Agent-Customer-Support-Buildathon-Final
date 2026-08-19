import os
import json
import logging
import time
import re
import threading
import queue

from datetime import datetime

from dotenv import load_dotenv


from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import SerperDevTool

from pydantic import BaseModel, Field, ValidationError

from services.email_service import send_email
from rag.rag_search import search_knowledge_base

load_dotenv()

# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


# =========================================================
# ENVIRONMENT
# =========================================================

if not os.getenv("OPENAI_API_KEY"):
    raise ValueError(
        "OPENAI_API_KEY is not set in the .env file"
    )

if not os.getenv("SERPER_API_KEY"):
    raise ValueError(
        "SERPER_API_KEY is not set in the .env file"
    )


# =========================================================
# CONFIGURATION
# =========================================================

CONFIDENCE_THRESHOLD = 80
MAX_WEB_SEARCH_ATTEMPTS = 3
MAX_CONVERSATION_TURNS = 10
MAX_HISTORY_RECORDS = 1000


# =========================================================
# CREW CONFIGURATION
# =========================================================

CREW_VERBOSE = (
    os.getenv(
        "CREW_VERBOSE",
        "false"
    ).lower()
    in ("true", "1", "yes")
)

CREW_TRACING = (
    os.getenv(
        "CREW_TRACING",
        "false"
    ).lower()
    in ("true", "1", "yes")
)


# =========================================================
# FILE LOCATIONS
# =========================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

MEMORY_FILE = os.path.join(
    BASE_DIR,
    "conversation_memory.json"
)

REQUEST_COUNTER_FILE = os.path.join(
    BASE_DIR,
    "request_counter.json"
)

AUDIT_HISTORY_FILE = os.path.join(
    BASE_DIR,
    "request_history.json"
)


# =========================================================
# PERFORMANCE METRICS
# =========================================================

def print_performance_metrics(metrics: dict):

    print()
    print("=" * 80)
    print("PERFORMANCE METRICS")
    print("=" * 80)

    for name, value in metrics.items():

        if name == "total":
            continue

        print(
            f"{name:<35}: "
            f"{value:.2f} sec"
        )

    print("-" * 80)

    if "total" in metrics:

        print(
            f"{'Total':<35}: "
            f"{metrics['total']:.2f} sec"
        )

    print("=" * 80)


# =========================================================
# 3.21.1 - SESSION-SAFE CONVERSATION MEMORY
# =========================================================

MAX_CONVERSATION_TURNS = 10

MEMORY_FILE = os.path.join(
    BASE_DIR,
    "conversation_memory.json"
)


def normalize_email(user_email: str) -> str:
    """
    Normalize email address for persistent customer memory.
    """

    return user_email.strip().lower()


def load_customer_conversation(
    user_email: str
) -> list:
    """
    Load persistent conversation history for one customer.

    IMPORTANT:
    This function does NOT modify global state.

    It returns a new list that the caller owns.
    """

    normalized_email = normalize_email(
        user_email
    )

    if not os.path.exists(MEMORY_FILE):

        logger.info(
            "No persistent conversation memory found "
            "for %s.",
            normalized_email
        )

        return []

    try:

        with open(
            MEMORY_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        customers = data.get(
            "customers",
            {}
        )

        if not isinstance(
            customers,
            dict
        ):

            return []

        customer_data = customers.get(
            normalized_email,
            {}
        )

        if not isinstance(
            customer_data,
            dict
        ):

            return []

        stored_history = customer_data.get(
            "conversation_history",
            []
        )

        if not isinstance(
            stored_history,
            list
        ):

            return []

        max_messages = (
            MAX_CONVERSATION_TURNS * 2
        )

        history = list(
            stored_history[-max_messages:]
        )

        logger.info(
            "Loaded %s conversation messages "
            "for %s.",
            len(history),
            normalized_email
        )

        return history

    except (
        json.JSONDecodeError,
        OSError,
        TypeError
    ) as exc:

        logger.warning(
            "Could not load persistent conversation "
            "memory for %s: %s",
            normalized_email,
            exc
        )

        return []


def save_customer_conversation(
    user_email: str,
    conversation_history: list
):
    """
    Save only the specified customer's conversation.

    No global conversation state is used.
    """

    normalized_email = normalize_email(
        user_email
    )

    if not isinstance(
        conversation_history,
        list
    ):

        conversation_history = []

    max_messages = (
        MAX_CONVERSATION_TURNS * 2
    )

    history_to_save = list(
        conversation_history[-max_messages:]
    )

    data = {
        "updated_at":
            datetime.now().isoformat(),
        "customers": {}
    }

    # -----------------------------------------------------
    # Preserve existing customers
    # -----------------------------------------------------

    if os.path.exists(MEMORY_FILE):

        try:

            with open(
                MEMORY_FILE,
                "r",
                encoding="utf-8"
            ) as file:

                existing_data = json.load(file)

            existing_customers = (
                existing_data.get(
                    "customers",
                    {}
                )
            )

            if isinstance(
                existing_customers,
                dict
            ):

                data["customers"] = dict(
                    existing_customers
                )

            # -------------------------------------------------
            # Backward compatibility with old format
            # -------------------------------------------------

            elif isinstance(
                existing_data.get(
                    "conversation_history"
                ),
                list
            ):

                data["customers"][
                    normalized_email
                ] = {
                    "conversation_history":
                        existing_data[
                            "conversation_history"
                        ]
                }

        except (
            json.JSONDecodeError,
            OSError,
            TypeError
        ):

            logger.warning(
                "Existing conversation memory could not be "
                "read. Creating a new structure."
            )

    # -----------------------------------------------------
    # Save current customer
    # -----------------------------------------------------

    data["customers"][
        normalized_email
    ] = {
        "updated_at":
            datetime.now().isoformat(),
        "conversation_history":
            history_to_save
    }

    try:

        with open(
            MEMORY_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                data,
                file,
                indent=4,
                ensure_ascii=False
            )

        logger.info(
            "Conversation memory saved for %s.",
            normalized_email
        )

    except OSError as exc:

        logger.exception(
            "Failed to save conversation memory: %s",
            exc
        )


def clear_customer_conversation(
    user_email: str
):
    """
    Clear persistent conversation for one customer only.

    Does not affect any other customer.
    """

    normalized_email = normalize_email(
        user_email
    )

    if not os.path.exists(
        MEMORY_FILE
    ):

        return

    try:

        with open(
            MEMORY_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        customers = data.get(
            "customers",
            {}
        )

        if not isinstance(
            customers,
            dict
        ):

            return

        customers.pop(
            normalized_email,
            None
        )

        data["customers"] = customers

        data["updated_at"] = (
            datetime.now().isoformat()
        )

        with open(
            MEMORY_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                data,
                file,
                indent=4,
                ensure_ascii=False
            )

        logger.info(
            "Conversation memory cleared for %s.",
            normalized_email
        )

    except (
        json.JSONDecodeError,
        OSError,
        TypeError
    ) as exc:

        logger.exception(
            "Failed to clear conversation memory for %s: %s",
            normalized_email,
            exc
        )


def add_customer_conversation_turn(
    user_email: str,
    conversation_history: list,
    user_query: str,
    final_answer: str
) -> list:
    """
    Add one conversation turn.

    Returns the updated conversation history.

    IMPORTANT:
    No global variables are modified.
    """

    updated_history = list(
        conversation_history or []
    )

    updated_history.append(
        {
            "role": "user",
            "content": user_query
        }
    )

    updated_history.append(
        {
            "role": "assistant",
            "content": final_answer
        }
    )

    max_messages = (
        MAX_CONVERSATION_TURNS * 2
    )

    if len(updated_history) > max_messages:

        updated_history = (
            updated_history[
                -max_messages:
            ]
        )

    save_customer_conversation(
        user_email=user_email,
        conversation_history=updated_history
    )

    return updated_history


def format_conversation_history(
    conversation_history: list
) -> str:
    """
    Convert session-specific conversation history
    into the prompt format expected by CrewAI.
    """

    if not conversation_history:

        return (
            "NO PREVIOUS CONVERSATION."
        )

    lines = []

    for message in conversation_history:

        if not isinstance(message, dict):
            continue

        role = message.get(
            "role",
            "unknown"
        ).upper()

        content = message.get(
            "content",
            ""
        )

        lines.append(
            f"{role}: {content}"
        )

    if not lines:

        return (
            "NO PREVIOUS CONVERSATION."
        )

    return "\n\n".join(
        lines
    )


# =========================================================
# REQUEST ID
# =========================================================

def load_request_counter() -> int:

    if not os.path.exists(
        REQUEST_COUNTER_FILE
    ):

        return 0

    try:

        with open(
            REQUEST_COUNTER_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        return int(
            data.get(
                "request_counter",
                0
            )
        )

    except (
        json.JSONDecodeError,
        OSError,
        ValueError,
        TypeError
    ):

        logger.warning(
            "Could not load request counter."
        )

        return 0


def save_request_counter(
    request_number: int
):

    try:

        with open(
            REQUEST_COUNTER_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                {
                    "request_counter":
                        request_number,

                    "updated_at":
                        datetime.now().isoformat()
                },
                file,
                indent=4
            )

    except OSError as exc:

        logger.exception(
            "Failed to save request counter: %s",
            exc
        )


request_counter = load_request_counter()


def generate_request_id() -> str:

    global request_counter

    request_counter += 1

    save_request_counter(
        request_counter
    )

    date_part = datetime.now().strftime(
        "%Y%m%d"
    )

    return (
        f"QE-{date_part}-"
        f"{request_counter:03d}"
    )


# =========================================================
# AUDIT HISTORY
# =========================================================

def load_audit_history() -> dict:

    if not os.path.exists(
        AUDIT_HISTORY_FILE
    ):

        return {
            "customers": {}
        }

    try:

        with open(
            AUDIT_HISTORY_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        if not isinstance(data, dict):

            return {
                "customers": {}
            }

        if not isinstance(
            data.get("customers"),
            dict
        ):

            data["customers"] = {}

        return data

    except (
        json.JSONDecodeError,
        OSError,
        TypeError
    ) as exc:

        logger.warning(
            "Could not load audit history: %s",
            exc
        )

        return {
            "customers": {}
        }


def save_audit_history(data: dict):

    try:

        with open(
            AUDIT_HISTORY_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                data,
                file,
                indent=4,
                ensure_ascii=False
            )

        logger.info(
            "Audit history saved successfully."
        )

    except OSError as exc:

        logger.exception(
            "Failed to save audit history: %s",
            exc
        )


def create_audit_record(
    request_id: str,
    user_email: str,
    user_query: str
) -> dict:

    return {

        "request_id":
            request_id,

        "user_email":
            normalize_email(user_email),

        "user_query":
            user_query,

        "final_answer":
            None,

        "confidence":
            0,

        "status":
            "IN_PROGRESS",

        "web_search_attempts":
            0,

        "email_sent":
            False,

        "created_at":
            datetime.now().isoformat(),

        "completed_at":
            None
    }


def start_audit_record(
    request_id: str,
    user_email: str,
    user_query: str
):

    normalized_email = normalize_email(
        user_email
    )

    data = load_audit_history()

    customers = data.setdefault(
        "customers",
        {}
    )

    customer_data = customers.setdefault(
        normalized_email,
        {
            "requests": []
        }
    )

    request_record = create_audit_record(
        request_id,
        normalized_email,
        user_query
    )

    customer_data.setdefault(
        "requests",
        []
    )

    customer_data["requests"].append(
        request_record
    )

    customer_data["requests"] = (
        customer_data["requests"]
        [-MAX_HISTORY_RECORDS:]
    )

    data["updated_at"] = (
        datetime.now().isoformat()
    )

    save_audit_history(data)


def update_audit_record(
    request_id: str,
    user_email: str,
    **updates
):

    normalized_email = normalize_email(
        user_email
    )

    data = load_audit_history()

    customers = data.get(
        "customers",
        {}
    )

    customer_data = customers.get(
        normalized_email
    )

    if not customer_data:
        return

    requests = customer_data.get(
        "requests",
        []
    )

    target_record = None

    for record in requests:

        if record.get(
            "request_id"
        ) == request_id:

            target_record = record
            break

    if target_record is None:
        return

    for key, value in updates.items():

        target_record[key] = value

    target_record[
        "updated_at"
    ] = datetime.now().isoformat()

    data["updated_at"] = (
        datetime.now().isoformat()
    )

    save_audit_history(data)


def complete_audit_record(
    request_id: str,
    user_email: str,
    result: dict
):

    agent3_output = result.get(
        "agent3_output"
    )

    final_answer = None
    confidence = 0

    if isinstance(
        agent3_output,
        dict
    ):

        final_answer = (
            agent3_output.get(
                "final_answer"
            )
        )

        confidence = (
            agent3_output.get(
                "confidence",
                0
            )
        )

    update_audit_record(

        request_id=request_id,

        user_email=user_email,

        final_answer=final_answer,

        confidence=confidence,

        status=result.get(
            "status",
            "UNKNOWN"
        ),

        web_search_attempts=result.get(
            "web_search_attempts",
            0
        ),

        email_sent=result.get(
            "email_sent",
            False
        ),

        completed_at=datetime.now().isoformat()
    )


def get_customer_request_history(
    user_email: str,
    limit: int = 10
) -> list:

    normalized_email = normalize_email(
        user_email
    )

    data = load_audit_history()

    customers = data.get(
        "customers",
        {}
    )

    customer_data = customers.get(
        normalized_email,
        {}
    )

    requests = customer_data.get(
        "requests",
        []
    )

    if not isinstance(
        requests,
        list
    ):

        return []

    return requests[
        -limit:
    ][::-1]


def display_request_history(
    user_email: str,
    limit: int = 10
):

    history = get_customer_request_history(
        user_email,
        limit
    )

    print()
    print("=" * 80)
    print(
        f"REQUEST HISTORY - "
        f"{normalize_email(user_email)}"
    )
    print("=" * 80)

    if not history:

        print(
            "No request history found."
        )

        return

    for index, record in enumerate(
        history,
        start=1
    ):

        print()
        print(
            f"[{index}] "
            f"{record.get('request_id', 'N/A')}"
        )

        print(
            f"    Date       : "
            f"{record.get('created_at', 'N/A')}"
        )

        print(
            f"    Query      : "
            f"{record.get('user_query', 'N/A')}"
        )

        print(
            f"    Status     : "
            f"{record.get('status', 'N/A')}"
        )

        print(
            f"    Confidence : "
            f"{record.get('confidence', 0)}%"
        )

        print(
            f"    Web Search : "
            f"{record.get('web_search_attempts', 0)} attempt(s)"
        )

        print(
            f"    Email Sent : "
            f"{record.get('email_sent', False)}"
        )

        final_answer = record.get(
            "final_answer"
        )

        if final_answer:

            print(
                f"    Answer     : "
                f"{final_answer}"
            )

        print("-" * 80)

    print()


# =========================================================
# LLM
# =========================================================

llm = LLM(
    model="gpt-4o-mini"
)


# =========================================================
# TOOLS
# =========================================================

serper_tool = SerperDevTool()


# =========================================================
# AGENT 1
# =========================================================

agent1 = Agent(

    role="QE Knowledge Assistant",

    goal=(
        "Answer the user's question strictly from the "
        "supplied FAISS knowledge base."
    ),

    backstory=(
        "You are an experienced Quality Engineering "
        "knowledge assistant. Your primary responsibility "
        "is grounded question answering using the project's "
        "FAISS knowledge base. Never use unsupported "
        "general knowledge."
    ),

    llm=llm,

    verbose=CREW_VERBOSE,

    allow_delegation=False
)


# =========================================================
# AGENT 2
# =========================================================

agent2 = Agent(

    role="QE Evidence Verification Specialist",

    goal=(
        "Verify answers using available evidence and "
        "determine whether the answer meets the confidence "
        "threshold."
    ),

    backstory=(
        "You are a senior QE validation specialist. "
        "You critically evaluate evidence relevance, "
        "source quality, agreement and completeness. "
        "Never blindly trust another agent."
    ),

    llm=llm,

    verbose=CREW_VERBOSE,

    allow_delegation=False
)


# =========================================================
# WEB SEARCH AGENT
# =========================================================

web_search_agent = Agent(

    role="QE Web Research Specialist",

    goal=(
        "Search the web for reliable evidence when "
        "internal knowledge is insufficient."
    ),

    backstory=(
        "You are a senior QE research specialist. "
        "Search for reliable, relevant and authoritative "
        "sources."
    ),

    tools=[
        serper_tool
    ],

    llm=llm,

    verbose=CREW_VERBOSE,

    allow_delegation=False,

    # ---------------------------------------------------
    # PERFORMANCE OPTIMIZATION:
    #
    # This is the only agent with a tool, so it's the only
    # one that can loop (think -> search -> think -> search
    # -> ...). CrewAI's default max_iter is 20, which lets a
    # single task silently run many extra search rounds
    # before answering. Task 3 already instructs the agent
    # to "search efficiently" and "not perform unnecessary
    # searches" - these caps just enforce that instruction
    # instead of only asking for it, without changing what a
    # normal (efficient) run produces.
    # ---------------------------------------------------

    max_iter=5,

    max_execution_time=45
)


# =========================================================
# AGENT 3
# =========================================================

agent3 = Agent(

    role="QE Support Response Specialist",

    goal=(
        "Convert already verified information into a "
        "clear final customer response without changing "
        "the verification result."
    ),

    backstory=(
        "You are a senior QE customer support response "
        "specialist. You must only format and summarize "
        "the verified evidence supplied by Agent 2. "
        "You never calculate, modify or reinterpret "
        "confidence."
    ),

    llm=llm,

    verbose=CREW_VERBOSE,

    allow_delegation=False
)


# =========================================================
# STRUCTURED OUTPUT
# =========================================================

class FinalSupportResponse(BaseModel):

    user_query: str = Field(
        description="Original user query"
    )

    final_answer: str = Field(
        description="Final consolidated answer"
    )

    confidence: int = Field(
        ge=0,
        le=100
    )

    status: str

    sources: list[str] = Field(
        default_factory=list
    )


# =========================================================
# TASK 1
# =========================================================

task1 = Task(

    description="""
CONVERSATION HISTORY:

{conversation_history}


USER QUERY:

{user_query}


RETRIEVED FAISS KNOWLEDGE:

{rag_context}


You are Agent 1.

Use conversation history only to understand follow-up
questions and references.

Conversation history is NOT factual evidence.

Your ONLY factual source is the supplied FAISS knowledge.

If the FAISS knowledge does not contain sufficient
information, return:

ANSWER:
INSUFFICIENT_KNOWLEDGE

STATUS:
NEEDS_WEB_SEARCH

SOURCES:
None

KNOWLEDGE_SUPPORT:
The FAISS knowledge base does not contain sufficient
relevant information.

Otherwise return:

ANSWER:
<answer>

STATUS:
SUPPORTED_BY_RAG

SOURCES:
<source names>

KNOWLEDGE_SUPPORT:
<brief explanation>
""",

    expected_output="""
A strictly RAG-grounded answer.

STATUS must be either:

SUPPORTED_BY_RAG

or:

NEEDS_WEB_SEARCH
""",

    agent=agent1
)


# =========================================================
# TASK 2
# INITIAL RAG VERIFICATION
# =========================================================

task2 = Task(

    description="""
USER QUERY:

{user_query}


The previous task is Agent 1.

Read Agent 1's output from the task context.

You are Agent 2, the Evidence Verification Specialist.

Determine whether Agent 1's answer is supported by
the available FAISS evidence.

If Agent 1 reports:

STATUS:
NEEDS_WEB_SEARCH

or:

ANSWER:
INSUFFICIENT_KNOWLEDGE

then:

STATUS:
NEEDS_WEB_SEARCH

and:

VERIFICATION_CONFIDENCE:
0

Do NOT use general LLM knowledge.

Evaluate:

1. Evidence relevance
2. Evidence quality
3. Source agreement
4. Answer completeness
5. Evidence-to-answer alignment
6. Unsupported claims

Calculate:

VERIFICATION_CONFIDENCE: integer 0-100
EVIDENCE_QUALITY: integer 0-100
SOURCE_AGREEMENT: integer 0-100
ANSWER_COMPLETENESS: integer 0-100

Confidence threshold:

{confidence_threshold}

If confidence >= threshold AND evidence directly
supports the answer:

STATUS:
VERIFIED

Otherwise:

STATUS:
NEEDS_WEB_SEARCH

Return exactly:

VERIFICATION_CONFIDENCE:
<number>

EVIDENCE_QUALITY:
<number>

SOURCE_AGREEMENT:
<number>

ANSWER_COMPLETENESS:
<number>

STATUS:
VERIFIED or NEEDS_WEB_SEARCH

VERIFIED_ANSWER:
<answer if verified>

SOURCES:
<sources>

REASON:
<short explanation>
""",

    expected_output="""
Evidence verification report containing:

VERIFICATION_CONFIDENCE
EVIDENCE_QUALITY
SOURCE_AGREEMENT
ANSWER_COMPLETENESS
STATUS
VERIFIED_ANSWER
SOURCES
REASON
""",

    agent=agent2,

    context=[
        task1
    ]
)


# =========================================================
# TASK 3
# OPTIMIZED WEB SEARCH
# =========================================================

task3 = Task(

    description="""
CONVERSATION HISTORY:

{conversation_history}


USER QUERY:

{user_query}


CURRENT ANSWER:

{current_answer}


CURRENT EVIDENCE:

{current_evidence}


You are the Web Research Specialist.

Search the web using the available Serper tool.

Find reliable evidence directly relevant to the user's
actual question.

Search efficiently. Do not perform unnecessary searches.

Prefer:

1. Official documentation
2. Official project websites
3. Authoritative technical sources
4. Reliable technical references

The search must:

1. Support the answer.
2. Correct incorrect information.
3. Fill missing information.
4. Resolve contradictions.

Do not blindly confirm the existing answer.

If you cannot find any relevant, reliable web results,
say so explicitly rather than leaving the search inconclusive.

Return:

WEB_SEARCH_FINDINGS:
<findings, or "No relevant web results were found.">

SOURCES:
<source names and URLs actually found, or "None">

EVIDENCE_SUMMARY:
<why this evidence answers the user's question>
""",

    expected_output="""
Web search findings, relevant sources and evidence summary.
""",

    agent=web_search_agent
)


# =========================================================
# TASK 4
# OPTIMIZED WEB VERIFICATION
# =========================================================

task4 = Task(

    description="""
USER QUERY:

{user_query}


CURRENT ANSWER:

{current_answer}


CURRENT EVIDENCE:

{current_evidence}


The previous task is the Web Research task.

Read the Web Research output from the task context.

You are Agent 2, the Evidence Verification Specialist.

Independently verify the answer using:

1. Original FAISS evidence
2. Web research evidence

SOURCE CITATION RULES (STRICT):

The original FAISS evidence was already judged insufficient
by Agent 1. You may use it only as background context for
understanding the question.

You must NOT list the original FAISS source (for example,
a path like knowledge_base\\some_file.md) in SOURCES unless
the Web Research findings above independently confirm the
same information.

Your SOURCES list must be built ONLY from the sources
actually returned by the Web Research task above (site
names, document titles, or URLs the web agent found).

If the Web Research task found no usable sources, return:

SOURCES:
None

Do not invent, assume, or carry forward a source that was
not explicitly provided by the Web Research task output.

Evaluate:

1. Does the evidence directly answer the question?
2. Is the evidence reliable?
3. Do sources agree?
4. Does evidence support or contradict the answer?
5. Is the answer complete?
6. Are there unsupported claims?

Calculate:

VERIFICATION_CONFIDENCE: integer 0-100
EVIDENCE_QUALITY: integer 0-100
SOURCE_AGREEMENT: integer 0-100
ANSWER_COMPLETENESS: integer 0-100

Confidence threshold:

{confidence_threshold}

If confidence >= threshold:

STATUS:
VERIFIED

Otherwise:

STATUS:
NEEDS_MORE_WEB_SEARCH

IMPORTANT:

VERIFICATION_CONFIDENCE MUST ALWAYS BE AN INTEGER.

Examples:

85
90
100

Never return:

0.85
0.90
0.95

Return:

VERIFICATION_CONFIDENCE:
<number>

EVIDENCE_QUALITY:
<number>

SOURCE_AGREEMENT:
<number>

ANSWER_COMPLETENESS:
<number>

STATUS:
VERIFIED or NEEDS_MORE_WEB_SEARCH

VERIFIED_ANSWER:
<answer>

SOURCES:
<sources>

REASON:
<short explanation>
""",

    expected_output="""
Verification report containing integer confidence,
status, verified answer, sources and reason.
""",

    agent=agent2,

    context=[
        task3
    ]
)


# =========================================================
# TASK 5
# AGENT 3 FINAL RESPONSE
#
# IMPORTANT:
# Agent 2 output is passed explicitly through:
#
# {agent2_output}
#
# This prevents Agent 3 from depending on cross-Crew
# task context.
# =========================================================

task5 = Task(

    description="""
USER QUERY:

{user_query}


AGENT 2 VERIFIED OUTPUT:

{agent2_output}


You are Agent 3.

Your ONLY job is to create the final customer response.

Agent 2's output above is the authoritative verification
result.

STRICT RULES:

1. Use ONLY information contained in Agent 2 output.
2. Do NOT perform web search.
3. Do NOT introduce new facts.
4. Do NOT invent sources.
5. Do NOT calculate confidence.
6. Do NOT estimate confidence.
7. Do NOT convert confidence.
8. Do NOT change confidence.
9. Do NOT use decimal confidence.
10. Keep the original user query exactly.
11. The final answer should directly answer the user.
12. Respect the requested answer length when possible.
13. If the user asks for one line, give one line.
14. If the user asks for two lines, give two concise lines.
15. Use Agent 2's verified answer as the factual basis.

VERY IMPORTANT:

Agent 2 confidence is authoritative.

Agent 3 must copy the Agent 2 confidence exactly as an
integer.

For example, if Agent 2 says:

VERIFICATION_CONFIDENCE: 85

then return:

"confidence": 85

NOT:

"confidence": 0.85

NOT:

"confidence": 0.95

NOT:

"confidence": 90

Do not modify the number.

Agent 3 must return ONLY valid JSON.

Use exactly this structure:

{
    "user_query": "<original user query>",
    "final_answer": "<clear final answer>",
    "confidence": <Agent 2 VERIFICATION_CONFIDENCE>,
    "status": "VERIFIED",
    "sources": [
        "<source 1>",
        "<source 2>"
    ]
}

If Agent 2 says VERIFIED, status must be VERIFIED.

Do not change the verification status.

Do not add markdown fences.
Do not add explanations outside JSON.
""",

    expected_output="""
Valid JSON containing:

user_query
final_answer
confidence
status
sources
""",

    agent=agent3
)


# =========================================================
# INITIAL CREW
# =========================================================

initial_support_crew = Crew(

    agents=[
        agent1,
        agent2
    ],

    tasks=[
        task1,
        task2
    ],

    process=Process.sequential,

    verbose=CREW_VERBOSE,

    tracing=CREW_TRACING
)


# =========================================================
# OPTIMIZED WEB SEARCH + VERIFICATION CREW
# =========================================================

web_verification_crew = Crew(

    agents=[
        web_search_agent,
        agent2
    ],

    tasks=[
        task3,
        task4
    ],

    process=Process.sequential,

    verbose=CREW_VERBOSE,

    tracing=CREW_TRACING
)


# =========================================================
# AGENT 3 CREW
# =========================================================

final_response_crew = Crew(

    agents=[
        agent3
    ],

    tasks=[
        task5
    ],

    process=Process.sequential,

    verbose=CREW_VERBOSE,

    tracing=CREW_TRACING
)


# =========================================================
# CONFIDENCE NORMALIZATION
# =========================================================

def normalize_confidence_value(
    value
) -> int:
    """
    Convert confidence returned by an LLM into a safe
    integer percentage.

    Supported examples:

    90       -> 90
    "90"     -> 90
    0.90     -> 90
    "0.90"   -> 90
    0.95     -> 95
    "0.95"   -> 95
    """

    if value is None:

        return 0

    if isinstance(
        value,
        bool
    ):

        return 0

    try:

        numeric_value = float(
            str(value).strip()
        )

    except (
        ValueError,
        TypeError
    ):

        return 0

    # -----------------------------------------------------
    # Decimal confidence
    # -----------------------------------------------------

    if (
        0 <= numeric_value <= 1
        and numeric_value != 0
    ):

        numeric_value *= 100

    # -----------------------------------------------------
    # Percentage confidence
    # -----------------------------------------------------

    numeric_value = round(
        numeric_value
    )

    numeric_value = max(
        0,
        min(
            100,
            numeric_value
        )
    )

    return int(
        numeric_value
    )


# =========================================================
# EXTRACT CONFIDENCE
# =========================================================

def extract_confidence(
    output
) -> int:

    text = str(output)

    patterns = [
        r"VERIFICATION_CONFIDENCE\s*:\s*([0-9]+(?:\.[0-9]+)?)",
        r'"confidence"\s*:\s*([0-9]+(?:\.[0-9]+)?)',
        r"confidence\s*:\s*([0-9]+(?:\.[0-9]+)?)"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE
        )

        if match:

            return normalize_confidence_value(
                match.group(1)
            )

    logger.warning(
        "Could not extract confidence. "
        "Treating confidence as 0."
    )

    return 0


# =========================================================
# EXTRACT STATUS
# =========================================================

def extract_status(
    output
) -> str:

    text = str(output)

    match = re.search(
        r"STATUS\s*:\s*([A-Z_]+)",
        text,
        flags=re.IGNORECASE
    )

    if match:

        return match.group(1).strip().upper()

    return ""


# =========================================================
# KNOWN REPORT FIELD LABELS
#
# Used by _extract_field_block() below to know where one
# field's value ends and the next field begins.
# =========================================================

_REPORT_FIELD_LABELS = [
    "VERIFICATION_CONFIDENCE",
    "EVIDENCE_QUALITY",
    "SOURCE_AGREEMENT",
    "ANSWER_COMPLETENESS",
    "STATUS",
    "VERIFIED_ANSWER",
    "SOURCES",
    "REASON",
]

_REPORT_FIELD_LINE_PATTERN = re.compile(
    r"^\s*(" + "|".join(_REPORT_FIELD_LABELS) + r")\s*:\s*(.*)$",
    re.IGNORECASE
)


def _extract_field_block(
    text: str,
    field_name: str
) -> str:
    """
    Extract the block of text following "<field_name>:" up to
    (but not including) the next known report field label, or
    the end of the text.

    PERFORMANCE FIX:

    This replaces a previous regex-based implementation that
    looked like:

        r"FIELD\\s*:\\s*(.*?)"
        r"(?=\\n\\s*\\n\\s*(?:OTHER_LABEL|...)\\s*:|\\Z)"

    Because \\s already matches \\n, chaining \\s* around a
    literal \\n like that lets the regex engine distribute the
    same whitespace across multiple quantifiers in exponentially
    many ways. On real LLM output that didn't line up exactly
    with the expected blank-line-before-next-label shape, this
    caused catastrophic backtracking - multi-second (sometimes
    20+ second) delays on a function that does no I/O and no LLM
    call at all. That is what was showing up as "Agent 3" time
    in the performance metrics even though Agent 3 does not make
    an LLM call in this codebase.

    This version scans line-by-line, which is linear in the
    length of the text and produces the same result for
    well-formed output.
    """

    lines = text.splitlines()

    start_index = None
    inline_value = ""

    for index, line in enumerate(lines):

        match = _REPORT_FIELD_LINE_PATTERN.match(line)

        if (
            match
            and match.group(1).upper() == field_name.upper()
        ):

            start_index = index
            inline_value = match.group(2).strip()
            break

    if start_index is None:

        return ""

    collected = (
        [inline_value] if inline_value else []
    )

    for line in lines[start_index + 1:]:

        if _REPORT_FIELD_LINE_PATTERN.match(line):

            break

        collected.append(line)

    return "\n".join(collected).strip()


# =========================================================
# EXTRACT VERIFIED ANSWER
#
# PERFORMANCE OPTIMIZATION (Step 3):
#
# Previously, Agent 3 made a separate LLM call purely to
# copy VERIFIED_ANSWER out of Agent 2's output into JSON.
# Agent 3 never actually decided anything: confidence and
# status were always forcibly overwritten with Agent 2's
# values in validate_agent3_output().
#
# This function performs the same extraction directly in
# Python, using the same regex-based approach already used
# for extract_confidence() and extract_status() above.
# =========================================================

def extract_verified_answer(
    output
) -> str:

    text = str(output)

    answer = _extract_field_block(
        text,
        "VERIFIED_ANSWER"
    )

    if (
        answer
        and answer.upper() not in ("NONE", "N/A")
    ):

        return answer

    logger.warning(
        "Could not extract VERIFIED_ANSWER. "
        "Falling back to full verification output."
    )

    return text.strip()


# =========================================================
# EXTRACT SOURCES
# =========================================================

def extract_sources(
    output
) -> list:

    text = str(output)

    raw_sources = _extract_field_block(
        text,
        "SOURCES"
    )

    if (
        not raw_sources
        or raw_sources.upper() in ("NONE", "N/A")
    ):

        return []

    sources = []

    for line in raw_sources.splitlines():

        cleaned = line.strip()

        cleaned = re.sub(
            r"^[-*\d\.\)]+\s*",
            "",
            cleaned
        )

        if (
            cleaned
            and cleaned.upper() not in ("NONE", "N/A")
        ):

            sources.append(cleaned)

    return sources


# =========================================================
# CLEAN JSON
# =========================================================

def clean_json_output(
    raw_output: str
) -> str:

    cleaned = raw_output.strip()

    # -----------------------------------------------------
    # Remove markdown JSON fence
    # -----------------------------------------------------

    if cleaned.startswith(
        "```json"
    ):

        cleaned = cleaned[
            len("```json"):
        ].strip()

    elif cleaned.startswith(
        "```"
    ):

        cleaned = cleaned[
            len("```"):
        ].strip()

    if cleaned.endswith(
        "```"
    ):

        cleaned = cleaned[
            :-len("```")
        ].strip()

    # -----------------------------------------------------
    # Extract JSON object if surrounding text exists
    # -----------------------------------------------------

    start_index = cleaned.find(
        "{"
    )

    end_index = cleaned.rfind(
        "}"
    )

    if (
        start_index >= 0
        and end_index > start_index
    ):

        cleaned = cleaned[
            start_index:
            end_index + 1
        ]

    return cleaned.strip()


# =========================================================
# VALIDATE AGENT 3 OUTPUT
#
# IMPORTANT 3.18.10 FIX
#
# Agent 3 is NOT trusted for confidence.
#
# The expected Agent 2 confidence is authoritative.
#
# Even if Agent 3 returns 0.95 or 85 or 90,
# the final confidence is forcibly set to Agent 2's
# confidence.
# =========================================================

def validate_agent3_output(
    raw_output: str,
    expected_confidence: int,
    expected_query: str
) -> FinalSupportResponse:

    cleaned_output = clean_json_output(
        raw_output
    )

    try:

        parsed_output = json.loads(
            cleaned_output
        )

    except json.JSONDecodeError as exc:

        logger.error(
            "Agent 3 returned invalid JSON: %s",
            exc
        )

        raise ValueError(
            f"Agent 3 returned invalid JSON: {exc}"
        ) from exc

    if not isinstance(
        parsed_output,
        dict
    ):

        raise ValueError(
            "Agent 3 output must be a JSON object."
        )

    # =====================================================
    # ORIGINAL QUERY
    # =====================================================

    agent3_query = str(
        parsed_output.get(
            "user_query",
            ""
        )
    ).strip()

    if agent3_query != expected_query.strip():

        logger.warning(
            "Agent 3 changed the original user query. "
            "Restoring original query."
        )

        parsed_output[
            "user_query"
        ] = expected_query

    # =====================================================
    # CONFIDENCE
    #
    # THIS IS THE KEY FIX.
    #
    # Never trust Agent 3 confidence.
    # =====================================================

    agent3_raw_confidence = (
        parsed_output.get(
            "confidence",
            None
        )
    )

    logger.info(
        "Agent 3 raw confidence: %s",
        agent3_raw_confidence
    )

    logger.info(
        "Authoritative Agent 2 confidence: %s",
        expected_confidence
    )

    # -----------------------------------------------------
    # FORCE Agent 2 confidence
    # -----------------------------------------------------

    parsed_output[
        "confidence"
    ] = int(
        expected_confidence
    )

    # =====================================================
    # STATUS
    # =====================================================

    parsed_output[
        "status"
    ] = "VERIFIED"

    # =====================================================
    # SOURCES
    # =====================================================

    sources = parsed_output.get(
        "sources",
        []
    )

    if sources is None:

        sources = []

    if isinstance(
        sources,
        str
    ):

        sources = [
            sources
        ]

    if not isinstance(
        sources,
        list
    ):

        sources = []

    parsed_output[
        "sources"
    ] = [
        str(source)
        for source in sources
    ]

    # =====================================================
    # FINAL ANSWER
    # =====================================================

    final_answer = parsed_output.get(
        "final_answer",
        ""
    )

    if not isinstance(
        final_answer,
        str
    ):

        final_answer = str(
            final_answer
        )

    parsed_output[
        "final_answer"
    ] = final_answer.strip()

    # =====================================================
    # FINAL PYDANTIC VALIDATION
    # =====================================================

    try:

        validated_output = (
            FinalSupportResponse.model_validate(
                parsed_output
            )
        )

    except ValidationError as exc:

        logger.error(
            "Agent 3 output validation failed: %s",
            exc
        )

        raise ValueError(
            f"Agent 3 output validation failed: {exc}"
        ) from exc

    # =====================================================
    # SAFETY CHECK
    # =====================================================

    if (
        validated_output.confidence
        != int(expected_confidence)
    ):

        raise ValueError(
            "Internal error: final confidence does not "
            "match Agent 2 confidence."
        )

    if (
        validated_output.user_query.strip()
        != expected_query.strip()
    ):

        raise ValueError(
            "Internal error: final query does not "
            "match original query."
        )

    if validated_output.status != "VERIFIED":

        raise ValueError(
            "Internal error: final status is not VERIFIED."
        )

    logger.info(
        "Agent 3 validation successful. "
        "Final confidence locked to Agent 2 confidence: %s",
        expected_confidence
    )

    return validated_output


# =========================================================
# RAG RETRIEVAL
# =========================================================

def retrieve_rag_context(
    user_query: str
):

    retrieved_results = search_knowledge_base(
        user_query,
        top_k=5
    )

    if not retrieved_results:

        return (
            "NO RELEVANT KNOWLEDGE WAS FOUND "
            "IN THE FAISS KNOWLEDGE BASE."
        )

    return "\n\n".join(
        [
            (
                f"SOURCE: {result['source']}\n"
                f"CONTENT:\n{result['content']}"
            )
            for result in retrieved_results
        ]
    )


# =========================================================
# RUN INITIAL CREW
# =========================================================

def run_initial_crew(
    user_query: str,
    rag_context: str,
    conversation_history_text: str
):

    logger.info(
        "Starting application-level CrewAI workflow."
    )

    result = initial_support_crew.kickoff(

        inputs={

            "user_query":
                user_query,

            "rag_context":
                rag_context,

            "conversation_history":
                conversation_history_text,

            "confidence_threshold":
                CONFIDENCE_THRESHOLD,

            "current_answer":
                "",

            "current_evidence":
                rag_context
        }
    )

    return str(result)


# =========================================================
# RUN OPTIMIZED WEB SEARCH + VERIFICATION
# =========================================================

def run_web_search_and_verification(
    user_query: str,
    current_answer: str,
    current_evidence: str,
    conversation_history_text: str
):

    logger.info(
        "Starting optimized Web Search + Verification Crew."
    )

    result = web_verification_crew.kickoff(

        inputs={

            "user_query":
                user_query,

            "current_answer":
                current_answer,

            "current_evidence":
                current_evidence,

            "conversation_history":
                conversation_history_text,

            "confidence_threshold":
                CONFIDENCE_THRESHOLD
        }
    )

    # -----------------------------------------------------
    # VISIBILITY FIX:
    #
    # web_verification_crew runs task3 (web search) then
    # task4 (verification). By default only task4's output
    # (the final task) is easily visible via str(result).
    #
    # This pulls out task3's raw findings as well, so it's
    # possible to see what the web search actually found,
    # separately from Agent 2's verification report.
    # -----------------------------------------------------

    web_search_findings_raw = ""

    try:

        tasks_output = getattr(
            result,
            "tasks_output",
            None
        )

        if tasks_output:

            web_search_findings_raw = str(
                tasks_output[0].raw
            )

    except (
        AttributeError,
        IndexError,
        TypeError
    ) as exc:

        logger.warning(
            "Could not extract raw web search "
            "findings: %s",
            exc
        )

    logger.info(
        "Web search findings (raw): %s",
        web_search_findings_raw
        or "No web search findings captured."
    )

    return str(result), web_search_findings_raw


# =========================================================
# RUN AGENT 3
#
# Agent 3 - No web search, no LLM search. It takes Agent 1's
# retrieval and Agent 2's verified output and returns ONLY
# the final, correctly formatted customer response (task5's
# strict rules forbid new facts, new sources, or changing the
# confidence/status set by Agent 2).
#
# This is the active path called from both success branches
# of run_support_crew() below. An earlier draft of a
# performance optimization introduced a pure-Python
# `build_final_response()` helper that skipped this Crew
# kickoff entirely (and produced the "Agent 3: 0.00 sec"
# timings) - that helper is intentionally removed. It never
# actually decided anything (its confidence/status were
# hardcoded), and skipping it meant Agent 3 wasn't running at
# all, only a mechanical copy of Agent 2's text. Agent 1 and
# Agent 2's own logic (task1-task4, initial_support_crew,
# web_verification_crew) and the email step are unchanged.
# =========================================================

def run_agent3(
    user_query: str,
    agent2_output: str,
    final_confidence: int
):

    logger.info(
        "Starting Agent 3 final response Crew."
    )

    # -----------------------------------------------------
    # IMPORTANT:
    #
    # Explicitly pass Agent 2 output into Task 5.
    #
    # This is more reliable than expecting a separate
    # Crew to access another Crew's task context.
    # -----------------------------------------------------

    result = final_response_crew.kickoff(

        inputs={

            "user_query":
                user_query,

            "agent2_output":
                agent2_output,

            "final_confidence":
                int(final_confidence)
        }
    )

    return validate_agent3_output(

        raw_output=str(result),

        expected_confidence=
            int(final_confidence),

        expected_query=
            user_query
    )


# =========================================================
# LINKIFY URLS
# =========================================================

URL_PATTERN = re.compile(
    r'(https?://[^\s<>"\']+)'
)


def linkify_urls(text: str) -> str:
    """
    Convert any raw http(s) URL found in the given text into
    a clickable HTML anchor tag. Handles cases where a source
    entry contains a single clean URL, multiple URLs, or a
    URL embedded alongside other text.
    """

    if not text:
        return text

    return URL_PATTERN.sub(
        lambda match: (
            f'<a href="{match.group(1)}">'
            f'{match.group(1)}</a>'
        ),
        text
    )


# =========================================================
# CREATE EMAIL BODY
# =========================================================

def create_email_body(
    agent3_output: FinalSupportResponse,
    request_id: str
) -> str:

    if agent3_output.sources:

        formatted_sources = "<br>".join(

            f'{index}. {linkify_urls(str(source).strip())}'

            for index, source
            in enumerate(
                agent3_output.sources,
                start=1
            )
        )

    else:

        formatted_sources = (
            "No sources available."
        )

    email_body = f"""\
<div style="font-family: Arial, sans-serif; font-size: 14px; line-height: 1.6; color: #222;">

<p>This response was generated by the QE Multi-Agent Customer Support System
(<a href="https://qecustomersupport.tech">qecustomersupport.tech</a>)</p>

<p><b>Request ID:</b> {request_id}</p>

<p><b>User Query:</b><br>
{agent3_output.user_query}</p>

<p><b>Output:</b><br>
{linkify_urls(agent3_output.final_answer)}</p>

<p><b>Accuracy level:</b> {agent3_output.confidence}%</p>

<p><b>Sources Verified:</b><br>
{formatted_sources}</p>

</div>
"""

    return email_body.strip()


# =========================================================
# SEND EMAIL
# =========================================================

def send_final_response_email(
    user_email: str,
    agent3_output: FinalSupportResponse,
    request_id: str
) -> bool:

    try:

        email_body = create_email_body(
            agent3_output,
            request_id
        )

        subject = (
            "QE Customer Support - "
            f"Verified Response [{request_id}]"
        )

        send_email(

            recipient_email=
                user_email,

            subject=
                subject,

            body=
                email_body
        )

        return True

    except Exception as exc:

        logger.exception(
            "Failed to send email: %s",
            exc
        )

        return False


# =========================================================
# BACKGROUND EMAIL WORKER (PERSISTENT QUEUE)
#
# PERFORMANCE OPTIMIZATION (Step 4, revised):
#
# The previous implementation spawned a brand-new
# threading.Thread for every single request just to send one
# email. Creating an OS-level thread is not free (interpreter
# + OS bookkeeping), and that overhead is paid on every request
# even though the thread is only used once.
#
# This replaces per-request thread creation with a single
# long-lived daemon worker thread that consumes jobs from a
# queue. send_final_response_email_async() now just enqueues a
# job (a fast, in-memory operation) instead of spinning up a
# new OS thread each time.
#
# CORRECTNESS GUARANTEE (unchanged):
#
# agent3_output is still a fully-built, immutable
# FinalSupportResponse at the moment it is enqueued, and
# nothing modifies it afterwards. The worker thread sends the
# exact same object that was enqueued, in the exact same order
# jobs were submitted (a queue.Queue is FIFO), so emailed
# content is still guaranteed to be byte-for-byte identical to
# what the user was shown on screen, and delivery order matches
# request order.
# =========================================================

_email_job_queue = queue.Queue()


def _email_worker_loop():

    while True:

        job = _email_job_queue.get()

        if job is None:

            _email_job_queue.task_done()

            break

        user_email, agent3_output, request_id = job

        try:

            success = send_final_response_email(

                user_email=
                    user_email,

                agent3_output=
                    agent3_output,

                request_id=
                    request_id
            )

            logger.info(
                "Background email send %s "
                "(Request ID: %s).",
                "succeeded" if success else "failed",
                request_id
            )

        except Exception as exc:

            logger.exception(
                "Background email send raised an "
                "unexpected exception "
                "(Request ID: %s): %s",
                request_id,
                exc
            )

        finally:

            _email_job_queue.task_done()


_email_worker_thread = threading.Thread(

    target=
        _email_worker_loop,

    name=
        "email-worker",

    daemon=
        True
)

_email_worker_thread.start()


def send_final_response_email_async(
    user_email: str,
    agent3_output: FinalSupportResponse,
    request_id: str
):

    # Enqueue only. The persistent worker thread above sends
    # the email; this call returns as soon as the job is
    # placed on the queue.

    _email_job_queue.put(
        (
            user_email,
            agent3_output,
            request_id
        )
    )


# =========================================================
# MAIN SUPPORT SERVICE
# =========================================================

def run_support_crew(
    user_query: str,
    user_email: str,
    request_id: str,
    conversation_history: list
):

    total_start = time.perf_counter()

    performance = {}

    logger.info(
        "Support request started "
        "(Request ID: %s)",
        request_id
    )

    # =====================================================
    # 1. CONVERSATION HISTORY
    # =====================================================

    conversation_history_text = (
        format_conversation_history(
            conversation_history
        )
    )

    # =====================================================
    # 2. FAISS
    # =====================================================

    start = time.perf_counter()

    rag_context = retrieve_rag_context(
        user_query
    )

    performance[
        "FAISS retrieval"
    ] = (
        time.perf_counter() - start
    )

    # =====================================================
    # 3. INITIAL CREW
    #
    # Agent 1 -> Agent 2
    # =====================================================

    start = time.perf_counter()

    initial_output = run_initial_crew(

        user_query=
            user_query,

        rag_context=
            rag_context,

        conversation_history_text=
            conversation_history_text
    )

    performance[
        "Initial Crew workflow"
    ] = (
        time.perf_counter() - start
    )

    confidence = extract_confidence(
        initial_output
    )

    agent1_output = initial_output
    agent2_output = initial_output

    # =====================================================
    # FORCE WEB SEARCH WHEN RAG IS INSUFFICIENT
    # =====================================================

    if (
        "NEEDS_WEB_SEARCH"
        in initial_output
    ):

        confidence = 0

    # =====================================================
    # 4. VERIFIED WITHOUT WEB
    # =====================================================

    if confidence >= CONFIDENCE_THRESHOLD:

        logger.info(
            "RAG answer verified without web search."
        )

        start = time.perf_counter()

        agent3_output = run_agent3(

            user_query=
                user_query,

            agent2_output=
                initial_output,

            final_confidence=
                confidence
        )

        performance[
            "Agent 3"
        ] = (
            time.perf_counter() - start
        )

        # -------------------------------------------------
        # MEMORY
        # -------------------------------------------------

        conversation_history = (
            add_customer_conversation_turn(
                user_email=user_email,
                conversation_history=conversation_history,
                user_query=user_query,
                final_answer=agent3_output.final_answer
            )
        )

        # -------------------------------------------------
        # EMAIL
        # -------------------------------------------------

        start = time.perf_counter()

        # Email is handed off to the persistent background
        # worker using the exact, already-finalized
        # agent3_output object, so it never blocks the
        # response and always reflects precisely what was
        # shown to the user.
        send_final_response_email_async(

            user_email=
                user_email,

            agent3_output=
                agent3_output,

            request_id=
                request_id
        )

        email_sent = True

        performance[
            "Email"
        ] = (
            time.perf_counter() - start
        )

        performance[
            "total"
        ] = (
            time.perf_counter()
            - total_start
        )

        print_performance_metrics(
            performance
        )

        return {

            "request_id":
                request_id,

            "conversation_history":
                conversation_history,

            "status":
                "VERIFIED",

            "agent1_output":
                agent1_output,

            "agent2_output":
                agent2_output,

            "agent3_output":
                agent3_output.model_dump(),

            "email_sent":
                email_sent,

            "web_search_attempts":
                0,

            "web_search_findings":
                [],

            "performance":
                performance
        }

    # =====================================================
    # 5. OPTIMIZED WEB SEARCH LOOP
    # =====================================================

    current_answer = initial_output
    current_evidence = rag_context

    web_search_attempts = 0

    verification_output = initial_output

    web_search_findings_log = []

    while (

        confidence < CONFIDENCE_THRESHOLD

        and

        web_search_attempts
        < MAX_WEB_SEARCH_ATTEMPTS
    ):

        web_search_attempts += 1

        logger.info(
            "Starting web search attempt %s/%s.",
            web_search_attempts,
            MAX_WEB_SEARCH_ATTEMPTS
        )

        # -------------------------------------------------
        # ONE CREW KICKOFF:
        #
        # Web Search Agent
        #       ↓
        # Agent 2 Verification
        #
        # -------------------------------------------------

        start = time.perf_counter()

        verification_output, web_search_findings_raw = (
            run_web_search_and_verification(

                user_query=
                    user_query,

                current_answer=
                    current_answer,

                current_evidence=
                    current_evidence,

                conversation_history_text=
                    conversation_history_text
            )
        )

        web_search_findings_log.append(
            {
                "attempt": web_search_attempts,
                "findings": web_search_findings_raw,
            }
        )

        combined_time = (
            time.perf_counter() - start
        )

        performance[
            f"Web search + verification "
            f"{web_search_attempts}"
        ] = combined_time

        # -------------------------------------------------
        # CONFIDENCE
        # -------------------------------------------------

        confidence = extract_confidence(
            verification_output
        )

        logger.info(
            "Verification confidence after "
            "attempt %s: %s",
            web_search_attempts,
            confidence
        )

        current_answer = verification_output

        current_evidence = (
            f"{current_evidence}\n\n"
            f"WEB SEARCH ATTEMPT "
            f"{web_search_attempts}:\n"
            f"{verification_output}"
        )

        # -------------------------------------------------
        # EARLY EXIT
        # -------------------------------------------------

        if confidence >= CONFIDENCE_THRESHOLD:

            logger.info(
                "Verification succeeded after "
                "%s web search attempt(s).",
                web_search_attempts
            )

            break

    # =====================================================
    # 6. SUCCESS
    # =====================================================

    if confidence >= CONFIDENCE_THRESHOLD:

        # -------------------------------------------------
        # AGENT 3
        # -------------------------------------------------

        start = time.perf_counter()

        agent3_output = run_agent3(

            user_query=
                user_query,

            agent2_output=
                verification_output,

            final_confidence=
                confidence
        )

        performance[
            "Agent 3"
        ] = (
            time.perf_counter() - start
        )

        # -------------------------------------------------
        # MEMORY
        # -------------------------------------------------

        conversation_history = (
            add_customer_conversation_turn(
                user_email=user_email,
                conversation_history=conversation_history,
                user_query=user_query,
                final_answer=agent3_output.final_answer
            )
        )

        # -------------------------------------------------
        # EMAIL
        # -------------------------------------------------

        start = time.perf_counter()

        # Email is handed off to the persistent background
        # worker using the exact, already-finalized
        # agent3_output object, so it never blocks the
        # response and always reflects precisely what was
        # shown to the user.
        send_final_response_email_async(

            user_email=
                user_email,

            agent3_output=
                agent3_output,

            request_id=
                request_id
        )

        email_sent = True

        performance[
            "Email"
        ] = (
            time.perf_counter() - start
        )

        performance[
            "total"
        ] = (
            time.perf_counter()
            - total_start
        )

        print_performance_metrics(
            performance
        )

        return {

            "request_id":
                request_id,

            "conversation_history":
                conversation_history,

            "status":
                "VERIFIED",

            "agent1_output":
                agent1_output,

            "agent2_output":
                verification_output,

            "agent3_output":
                agent3_output.model_dump(),

            "email_sent":
                email_sent,

            "web_search_attempts":
                web_search_attempts,

            "web_search_findings":
                web_search_findings_log,

            "performance":
                performance
        }

    # =====================================================
    # 7. SAFE FAILURE
    # =====================================================

    performance[
        "total"
    ] = (
        time.perf_counter()
        - total_start
    )

    print_performance_metrics(
        performance
    )

    logger.error(
        "Unable to verify answer after %s "
        "web search attempt(s).",
        web_search_attempts
    )

    return {

        "request_id":
            request_id,

        "status":
            "UNABLE_TO_VERIFY",

        "agent1_output":
            agent1_output,

        "agent2_output":
            verification_output,

        "agent3_output":
            None,

        "email_sent":
            False,

        "web_search_attempts":
            web_search_attempts,

        "web_search_findings":
            web_search_findings_log,

        "performance":
            performance
    }


# =========================================================
# MAIN APPLICATION
# =========================================================

if __name__ == "__main__":

    print()
    print("=" * 80)
    print(
        "QE SUPPORT AGENT - STEP 3.21.1"
    )
    print(
        "Optimized Web Search + Verification"
    )
    print("=" * 80)

    print()
    print(
        f"Confidence threshold : "
        f"{CONFIDENCE_THRESHOLD}%"
    )

    print(
        f"Maximum web attempts : "
        f"{MAX_WEB_SEARCH_ATTEMPTS}"
    )

    print(
        f"Crew verbose         : "
        f"{CREW_VERBOSE}"
    )

    print(
        f"Crew tracing         : "
        f"{CREW_TRACING}"
    )

    # =====================================================
    # EMAIL
    # =====================================================

    user_email = input(
        "\nEnter your email address: "
    ).strip()

    if not user_email:

        print(
            "Email address cannot be empty."
        )

        raise SystemExit

    user_email = normalize_email(
        user_email
    )

    # =====================================================
    # LOAD MEMORY
    # =====================================================

    conversation_history = load_customer_conversation(
        user_email
    )

    print()
    print(
        "Conversational mode enabled."
    )

    print(
        "Ask multiple questions in the same session."
    )

    print(
        "Type 'exit' to end the conversation."
    )

    print(
        "Type 'reset' to clear this customer's "
        "conversation memory."
    )

    print(
        "Type 'history' to view the latest 10 requests."
    )

    print(
        "Type 'history 5' to view the latest 5 requests."
    )

    print(
        "Request audit history is stored separately "
        "from conversation memory."
    )

    # =====================================================
    # CONVERSATION LOOP
    # =====================================================

    while True:

        user_query = input(
            "\nEnter your question: "
        ).strip()

        # =================================================
        # EXIT
        # =================================================

        if user_query.lower() == "exit":

            print()
            print(
                "Conversation ended."
            )

            print(
                f"Conversation messages stored: "
                f"{len(conversation_history)}"
            )

            print(
                f"Persistent memory file: "
                f"{MEMORY_FILE}"
            )

            print(
                f"Audit history file: "
                f"{AUDIT_HISTORY_FILE}"
            )

            break

        # =================================================
        # RESET
        # =================================================

        if user_query.lower() == "reset":

            clear_customer_conversation(
                user_email
            )

            conversation_history = []

            print()
            print(
                "Conversation memory for this email "
                "has been cleared."
            )

            print(
                "Request audit history has NOT been deleted."
            )

            continue

        # =================================================
        # HISTORY
        # =================================================

        if user_query.lower() == "history":

            display_request_history(
                user_email=user_email,
                limit=10
            )

            continue

        # =================================================
        # HISTORY N
        # =================================================

        if user_query.lower().startswith(
            "history "
        ):

            parts = user_query.split(
                maxsplit=1
            )

            try:

                history_limit = int(
                    parts[1].strip()
                )

                if history_limit <= 0:

                    print(
                        "\nHistory count must be "
                        "greater than 0."
                    )

                    continue

                if history_limit > 100:

                    history_limit = 100

                display_request_history(
                    user_email=user_email,
                    limit=history_limit
                )

            except (
                ValueError,
                IndexError
            ):

                print(
                    "\nInvalid history command."
                )

                print(
                    "Use: history"
                )

                print(
                    "or: history 5"
                )

            continue

        # =================================================
        # EMPTY QUESTION
        # =================================================

        if not user_query:

            print(
                "Question cannot be empty."
            )

            continue

        # =================================================
        # REQUEST ID
        # =================================================

        request_id = generate_request_id()

        # =================================================
        # CREATE AUDIT RECORD
        # =================================================

        start_audit_record(

            request_id=
                request_id,

            user_email=
                user_email,

            user_query=
                user_query
        )

        # =================================================
        # RUN SUPPORT SYSTEM
        # =================================================

        try:

            result = run_support_crew(

                user_query=
                    user_query,

                user_email=
                    user_email,

                request_id=
                    request_id,

                conversation_history=
                    conversation_history
            )

            conversation_history = result.get(
                "conversation_history",
                conversation_history
            )

            # -------------------------------------------------
            # COMPLETE AUDIT
            # -------------------------------------------------

            complete_audit_record(

                request_id=
                    request_id,

                user_email=
                    user_email,

                result=
                    result
            )

        except Exception as exc:

            logger.exception(
                "Support request failed "
                "(Request ID: %s): %s",
                request_id,
                exc
            )

            update_audit_record(

                request_id=
                    request_id,

                user_email=
                    user_email,

                status=
                    "FAILED",

                confidence=
                    0,

                email_sent=
                    False,

                completed_at=
                    datetime.now().isoformat(),

                error=
                    str(exc)
            )

            print()
            print("=" * 80)
            print(
                "REQUEST FAILED"
            )
            print("=" * 80)

            print(
                f"Request ID: {request_id}"
            )

            print(
                f"Error: {exc}"
            )

            print(
                "The failed request has been "
                "stored in audit history."
            )

            continue

        # =================================================
        # FINAL RESULT
        # =================================================

        print()
        print("=" * 80)
        print(
            "FINAL RESULT"
        )
        print("=" * 80)

        print(
            f"REQUEST ID: "
            f"{result.get('request_id', 'N/A')}"
        )

        print(
            f"STATUS: "
            f"{result.get('status', 'N/A')}"
        )

        print(
            f"WEB SEARCH ATTEMPTS: "
            f"{result.get('web_search_attempts', 0)}"
        )

        print(
            f"EMAIL SENT: "
            f"{result.get('email_sent', False)}"
        )

        print()

        # =================================================
        # PERFORMANCE
        # =================================================

        performance = result.get(
            "performance",
            {}
        )

        if performance:

            print(
                "=" * 80
            )

            print(
                "PERFORMANCE"
            )

            print(
                "=" * 80
            )

            for name, value in performance.items():

                if name == "total":
                    continue

                print(
                    f"{name:<35}: "
                    f"{value:.2f} sec"
                )

            print(
                "-" * 80
            )

            print(
                f"{'Total':<35}: "
                f"{performance.get('total', 0):.2f} sec"
            )

            print(
                "=" * 80
            )

        # =================================================
        # AGENT 1
        # =================================================

        print()
        print(
            "=" * 80
        )

        print(
            "AGENT 1 OUTPUT"
        )

        print(
            "=" * 80
        )

        print(
            result.get(
                "agent1_output",
                "N/A"
            )
        )

        # =================================================
        # AGENT 2
        # =================================================

        print()
        print(
            "=" * 80
        )

        print(
            "AGENT 2 OUTPUT"
        )

        print(
            "=" * 80
        )

        print(
            result.get(
                "agent2_output",
                "N/A"
            )
        )

        # =================================================
        # AGENT 3
        # =================================================

        print()
        print(
            "=" * 80
        )

        print(
            "AGENT 3 FINAL OUTPUT"
        )

        print(
            "=" * 80
        )

        print(
            json.dumps(
                result.get(
                    "agent3_output",
                    {
                        "error":
                            "Agent 3 was not executed."
                    }
                ),
                indent=4,
                ensure_ascii=False
            )
        )

        print()
        print(
            "Request audit record saved successfully."
        )