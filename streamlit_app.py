import os
import json
import logging
import re
import textwrap

import streamlit as st
from dotenv import load_dotenv

from crew.support_crew import (
    run_support_crew,
    generate_request_id,
    load_customer_conversation,
    clear_customer_conversation,
    normalize_email,
    get_customer_request_history,
    CONFIDENCE_THRESHOLD,
    MAX_WEB_SEARCH_ATTEMPTS,
    MAX_CONVERSATION_TURNS,
)


# =========================================================
# ENVIRONMENT
# =========================================================

load_dotenv()


# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="QE Support Agent",
    page_icon="🤖",
    layout="wide",
)


# =========================================================
# CUSTOM UI STYLING
# =========================================================

st.markdown(
    """
    <style>

    /* =====================================================
       GLOBAL APPLICATION & TYPOGRAPHY
       ===================================================== */

    .stApp {
        background: radial-gradient(circle at 15% 5%, rgba(91, 78, 220, 0.15), transparent 35%),
                    radial-gradient(circle at 85% 10%, rgba(0, 198, 255, 0.10), transparent 30%),
                    linear-gradient(135deg, #070c17 0%, #091121 50%, #060c17 100%);
        color: #f5f7ff;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }

    /* Modern scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    ::-webkit-scrollbar-track {
        background: #070c17;
    }
    ::-webkit-scrollbar-thumb {
        background: #1f293d;
        border-radius: 4px;
    }

    /* =====================================================
       SIDEBAR
       ===================================================== */

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0e1326 0%, #0a0d1d 100%);
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }

    section[data-testid="stSidebar"] > div:first-child {
        padding-top: 2rem;
    }

    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: #ffffff;
        font-weight: 700;
        letter-spacing: -0.5px;
    }

    /* Inputs */
    section[data-testid="stSidebar"] input {
        background-color: #121829 !important;
        color: #f5f7ff !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        border-radius: 8px !important;
        padding: 10px 14px !important;
    }

    section[data-testid="stSidebar"] input:focus {
        border-color: #6374ff !important;
        box-shadow: 0 0 0 2px rgba(99, 116, 255, 0.25) !important;
    }

    /* Primary Buttons */
    section[data-testid="stSidebar"] button[kind="primary"] {
        border-radius: 8px !important;
        font-weight: 600 !important;
        background: linear-gradient(90deg, #4f5df5, #7b3ff2) !important;
        color: #ffffff !important;
        border: none !important;
        box-shadow: 0 4px 14px rgba(84, 70, 220, 0.3) !important;
        transition: all 0.2s ease !important;
    }

    section[data-testid="stSidebar"] button[kind="primary"]:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 18px rgba(84, 70, 220, 0.45) !important;
    }

    /* Secondary "New User" Button Styling */
    /* Secondary CTA Button (Matching Primary Palette) */
    section[data-testid="stSidebar"] button[kind="secondary"] {
        border-radius: 8px !important;
        font-weight: 600 !important;
        background: linear-gradient(90deg, #4f5df5, #7b3ff2) !important;
        color: #ffffff !important;
        border: none !important;
        box-shadow: 0 4px 14px rgba(84, 70, 220, 0.3) !important;
        transition: all 0.2s ease !important;
    }

    section[data-testid="stSidebar"] button[kind="secondary"]:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 18px rgba(84, 70, 220, 0.45) !important;
        color: #ffffff !important;
    }

    /* =====================================================
       MAIN CONTENT CONTAINER
       ===================================================== */

    .main .block-container {
        padding-top: 2.5rem;
        padding-bottom: 4rem;
        max-width: 1200px;
    }

    /* =====================================================
       HEADER COMPONENT
       ===================================================== */

    .qe-header-container {
        display: flex;
        align-items: center;
        gap: 16px;
        margin-bottom: 8px;
    }

    .qe-avatar {
        width: 52px;
        height: 52px;
        min-width: 52px;
        background: linear-gradient(135deg, #6374ff 0%, #a14fff 100%);
        border-radius: 14px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 26px;
        box-shadow: 0 8px 20px rgba(99, 116, 255, 0.3);
    }

    .qe-title-text {
        font-size: 32px;
        font-weight: 800;
        letter-spacing: -0.8px;
        background: linear-gradient(90deg, #ffffff 30%, #a5b4fc 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
        line-height: 1.2;
    }

    .qe-subtitle-text {
        font-size: 16px;
        color: #94a3b8;
        margin-top: 4px;
        margin-bottom: 24px;
    }

    /* =====================================================
       INFORMATION BANNER
       ===================================================== */

    .info-banner {
        display: flex;
        align-items: center;
        gap: 14px;
        padding: 16px 20px;
        margin: 16px 0 28px 0;
        border-radius: 12px;
        background: rgba(30, 41, 59, 0.5);
        border: 1px solid rgba(99, 116, 255, 0.2);
        color: #cbd5e1;
        font-size: 15px;
        backdrop-filter: blur(8px);
    }

    .info-icon {
        width: 28px;
        height: 28px;
        min-width: 28px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 50%;
        background: rgba(99, 116, 255, 0.2);
        color: #818cf8;
        font-weight: 700;
        font-size: 14px;
    }

    /* =====================================================
       CHAT & CARDS
       ===================================================== */

    div[data-testid="stChatMessage"] {
        background-color: rgba(15, 23, 42, 0.6) !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 12px !important;
        margin-bottom: 12px !important;
    }

    div[data-testid="stChatInput"] {
        border-radius: 12px !important;
    }

    div[data-testid="stChatInput"] textarea {
        background-color: #0f172a !important;
        color: #f8fafc !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        border-radius: 10px !important;
    }

    div[data-testid="stChatInput"] textarea:focus {
        border-color: #6374ff !important;
        box-shadow: 0 0 0 2px rgba(99, 116, 255, 0.2) !important;
    }

    /* Metrics & Expanders */
    div[data-testid="stMetric"] {
        background: rgba(15, 23, 42, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 10px;
        padding: 12px 16px;
    }

    div[data-testid="stExpander"] {
        border-radius: 10px !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        background: rgba(15, 23, 42, 0.4) !important;
    }

    hr {
        border-color: rgba(255, 255, 255, 0.08) !important;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# LOGGING
# =========================================================

logger = logging.getLogger("qe_streamlit")


# =========================================================
# SESSION STATE INITIALIZATION
# =========================================================

def initialize_session_state():

    if "user_email" not in st.session_state:
        st.session_state.user_email = ""

    if "conversation_history" not in st.session_state:
        st.session_state.conversation_history = []

    if "memory_loaded_for" not in st.session_state:
        st.session_state.memory_loaded_for = ""

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "last_result" not in st.session_state:
        st.session_state.last_result = None

    if "processing" not in st.session_state:
        st.session_state.processing = False


initialize_session_state()


# =========================================================
# EMAIL VALIDATION
# =========================================================

def is_valid_email(email: str) -> bool:

    pattern = (
        r"^[A-Za-z0-9._%+-]+"
        r"@[A-Za-z0-9.-]+\."
        r"[A-Za-z]{2,}$"
    )

    return bool(re.match(pattern, email))


# =========================================================
# LOAD CUSTOMER SESSION
# =========================================================

def load_customer_session(user_email: str):

    normalized_email = normalize_email(user_email)

    if (
        st.session_state.memory_loaded_for
        == normalized_email
    ):
        return

    history = load_customer_conversation(
        normalized_email
    )

    st.session_state.user_email = normalized_email

    st.session_state.conversation_history = history

    st.session_state.memory_loaded_for = normalized_email

    st.session_state.messages = []

    for message in history:

        role = message.get("role")

        content = message.get(
            "content",
            "",
        )

        if role in ("user", "assistant"):

            st.session_state.messages.append(
                {
                    "role": role,
                    "content": content,
                }
            )


# =========================================================
# RESET / NEW USER SESSION
# =========================================================

def new_user_session():

    st.session_state.user_email = ""

    st.session_state.conversation_history = []

    st.session_state.memory_loaded_for = ""

    st.session_state.messages = []

    st.session_state.last_result = None

    st.session_state.processing = False

    st.rerun()


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.header("Welcome Amigo! 👋")

    email_input = st.text_input(
        "Email address",
        value=st.session_state.user_email,
        placeholder="abc123@example.com",
    )

    if st.button(
        "Start a conversation  ➤",
        use_container_width=True,
        type="primary",
    ):

        email_input = email_input.strip()

        if not email_input:

            st.error(
                "Email address cannot be empty."
            )

        elif not is_valid_email(email_input):

            st.error(
                "Please enter a valid email address."
            )

        else:

            load_customer_session(
                email_input
            )

            st.success(
                "Customer memory loaded."
            )

            st.rerun()

    if st.button(
        " New User",
        use_container_width=True,
        type="secondary",
    ):
        new_user_session()


# =========================================================
# MAIN HEADER
# =========================================================

st.markdown(
    """
    <div class="qe-header-container">
        <div class="qe-avatar">🤖</div>
        <div>
            <div class="qe-title-text">QE Support Agent</div>
        </div>
    </div>
    <div class="qe-subtitle-text">
        Your AI companion for QE questions, test support, and verified answers.
    </div>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# REQUIRE CUSTOMER
# =========================================================

if not st.session_state.user_email:

    st.markdown(
        """
        <div class="info-banner">
            <div class="info-icon">i</div>
            <div>
                Enter your email address in the sidebar to start a conversation with the QE Support Agent.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.stop()


# =========================================================
# CHAT MESSAGES
# =========================================================

for message in st.session_state.messages:

    role = message.get("role")

    content = message.get(
        "content",
        "",
    )

    with st.chat_message(role):

        st.markdown(content)


# =========================================================
# QUESTION INPUT
# =========================================================

user_query = st.chat_input(
    "Ask your QE question..."
)


# =========================================================
# PROCESS QUESTION
# =========================================================

if user_query:

    user_query = user_query.strip()

    if not user_query:

        st.warning(
            "Question cannot be empty."
        )

        st.stop()


    # -----------------------------------------------------
    # Prevent Duplicate Execution
    # -----------------------------------------------------

    if st.session_state.processing:

        st.warning(
            "A request is already being processed."
        )

        st.stop()


    st.session_state.processing = True


    # -----------------------------------------------------
    # Add User Message
    # -----------------------------------------------------

    st.session_state.messages.append(
        {
            "role": "user",
            "content": user_query,
        }
    )

    with st.chat_message("user"):

        st.markdown(user_query)


    # -----------------------------------------------------
    # Generate Request ID
    # -----------------------------------------------------

    request_id = generate_request_id()


    # -----------------------------------------------------
    # Execute Support System
    # -----------------------------------------------------

    try:

        with st.chat_message("assistant"):

            with st.status(
                "Processing your request...",
                expanded=False,
            ):

                result = run_support_crew(

                    user_query=user_query,

                    user_email=(
                        st.session_state.user_email
                    ),

                    request_id=request_id,

                    conversation_history=(
                        st.session_state.conversation_history
                    ),
                )


        # -------------------------------------------------
        # Result
        # -------------------------------------------------

        status = result.get(
            "status",
            "UNKNOWN",
        )

        agent3_output = (
            result.get("agent3_output")
            or {}
        )


        # -------------------------------------------------
        # VERIFIED RESPONSE
        # -------------------------------------------------

        if status == "VERIFIED":

            final_answer = agent3_output.get(
                "final_answer",
                "No final answer was generated.",
            )

            confidence = agent3_output.get(
                "confidence",
                0,
            )

            sources = agent3_output.get(
                "sources",
                [],
            )


            # ---------------------------------------------
            # Display Answer
            # ---------------------------------------------

            with st.chat_message("assistant"):

                st.markdown(final_answer)

                st.caption(
                    f"Confidence: {confidence}%"
                )


                # -----------------------------------------
                # Sources
                # -----------------------------------------

                if sources:

                    with st.expander("Sources"):

                        for source in sources:

                            st.write(source)


            # ---------------------------------------------
            # Update Conversation
            # ---------------------------------------------

            st.session_state.conversation_history.append(
                {
                    "role": "user",
                    "content": user_query,
                }
            )

            st.session_state.conversation_history.append(
                {
                    "role": "assistant",
                    "content": final_answer,
                }
            )


            max_messages = (
                MAX_CONVERSATION_TURNS * 2
            )

            st.session_state.conversation_history = (
                st.session_state.conversation_history[
                    -max_messages:
                ]
            )


            # ---------------------------------------------
            # Save Assistant Message
            # ---------------------------------------------

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": final_answer,
                }
            )


        # -------------------------------------------------
        # UNABLE TO VERIFY
        # -------------------------------------------------

        else:

            error_message = (
                "I could not verify this answer "
                "with sufficient confidence."
            )

            with st.chat_message("assistant"):

                st.warning(error_message)

                st.caption(
                    f"Request ID: {request_id}"
                )

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": error_message,
                }
            )


        # -------------------------------------------------
        # Save Last Result
        # -------------------------------------------------

        st.session_state.last_result = result


    except Exception as exc:

        logger.exception(
            "Streamlit request failed: %s",
            exc,
        )

        with st.chat_message("assistant"):

            st.error(
                "An unexpected error occurred "
                "while processing your request."
            )

            st.caption(
                f"Request ID: {request_id}"
            )

        st.session_state.last_result = {
            "request_id": request_id,
            "status": "FAILED",
            "error": str(exc),
        }


    finally:

        st.session_state.processing = False


# =========================================================
# LAST REQUEST DETAILS
# =========================================================

if st.session_state.last_result:

    result = st.session_state.last_result

    st.divider()

    st.subheader("Latest Request")

    col1, col2, col3, col4 = st.columns(4)


    with col1:

        st.metric(
            "Request ID",
            result.get(
                "request_id",
                "N/A",
            ),
        )


    with col2:

        st.metric(
            "Status",
            result.get(
                "status",
                "N/A",
            ),
        )


    with col3:

        st.metric(
            "Web Attempts",
            result.get(
                "web_search_attempts",
                0,
            ),
        )


    with col4:

        email_sent = result.get(
            "email_sent",
            False,
        )

        st.metric(
            "Email Sent",
            "Yes" if email_sent else "No",
        )


    # -----------------------------------------------------
    # Performance
    # -----------------------------------------------------

    performance = result.get(
        "performance",
        {},
    )

    if performance:

        with st.expander(
            "Performance Metrics"
        ):

            performance_rows = []

            for name, value in performance.items():

                performance_rows.append(
                    {
                        "Stage": name,
                        "Time (seconds)": round(
                            value,
                            2,
                        ),
                    }
                )

            st.dataframe(
                performance_rows,
                use_container_width=True,
                hide_index=True,
            )


    # -----------------------------------------------------
    # Agent 1 Output
    # -----------------------------------------------------

    with st.expander("Agent 1 Output"):

        st.code(
            str(
                result.get(
                    "agent1_output",
                    "N/A",
                )
            )
        )


    # -----------------------------------------------------
    # Agent 2 Output
    # -----------------------------------------------------

    with st.expander("Agent 2 Output"):

        st.code(
            str(
                result.get(
                    "agent2_output",
                    "N/A",
                )
            )
        )


    # -----------------------------------------------------
    # Agent 3 Output
    # -----------------------------------------------------

    with st.expander(
        "Agent 3 Final Output"
    ):

        st.json(
            result.get(
                "agent3_output",
                {},
            )
        )