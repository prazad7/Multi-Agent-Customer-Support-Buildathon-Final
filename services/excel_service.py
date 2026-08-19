import os
import time
import logging
from openpyxl import load_workbook, Workbook

logger = logging.getLogger(__name__)

DEFAULT_EXCEL_PATH = os.getenv("EXCEL_LOG_PATH", "support_logs.xlsx")
FALLBACK_EXCEL_PATH = os.getenv("EXCEL_FALLBACK_PATH", "support_logs_pending.xlsx")

HEADERS = ["S.No", "User email", "Query", "Final response", "DateTime of query received"]


def _ensure_workbook_exists(file_path: str):
    """Creates a new workbook with headers if the target file does not exist."""
    if not os.path.exists(file_path):
        wb = Workbook()
        ws = wb.active
        ws.title = "Support Logs"
        ws.append(HEADERS)
        wb.save(file_path)
        logger.info(f"[EXCEL SERVICE] Created new Excel log file at '{file_path}'.")


def _write_row(file_path: str, user_email: str, query: str, final_response: str, received_datetime: str):
    """Appends a single row with auto-incremented S.No to an Excel file and saves it."""
    _ensure_workbook_exists(file_path)
    wb = load_workbook(file_path)
    ws = wb.active

    # Auto-increment S.No based on current row count (subtract header row)
    s_no = ws.max_row

    # Append 5-column structured row
    ws.append([s_no, user_email, query, final_response, received_datetime])
    wb.save(file_path)


def append_to_excel(
    user_email: str, 
    query: str, 
    final_response: str, 
    received_datetime: str, 
    excel_path: str = DEFAULT_EXCEL_PATH,
    max_retries: int = 3,
    retry_delay: float = 1.5
) -> bool:
    """
    Appends query execution log to an Excel workbook.
    Handles file locks (e.g., when Excel is left open) with retries and a pending fallback file.
    """
    # Step 1: Attempt to write to the primary Excel log file with retries
    for attempt in range(1, max_retries + 1):
        try:
            _write_row(excel_path, user_email, query, final_response, received_datetime)
            logger.info(f"[EXCEL SERVICE] Successfully updated main file: '{excel_path}'")
            return True
        except (PermissionError, IOError) as e:
            logger.warning(
                f"[EXCEL SERVICE] Lock detected on '{excel_path}' (Attempt {attempt}/{max_retries}). "
                f"File might be open in Excel. Retrying in {retry_delay}s... Error: {e}"
            )
            if attempt < max_retries:
                time.sleep(retry_delay * attempt)  # Backoff delay
        except Exception as e:
            logger.error(f"[EXCEL SERVICE] Unexpected error while writing to '{excel_path}': {e}")
            break

    # Step 2: Fallback to pending log file if main file remains locked
    logger.warning(
        f"[EXCEL SERVICE] Main log file '{excel_path}' remains locked. "
        f"Appending entry to fallback file '{FALLBACK_EXCEL_PATH}' instead."
    )
    
    try:
        _write_row(FALLBACK_EXCEL_PATH, user_email, query, final_response, received_datetime)
        logger.info(f"[EXCEL SERVICE] Successfully saved entry to fallback: '{FALLBACK_EXCEL_PATH}'")
        return True
    except Exception as e:
        logger.critical(f"[EXCEL SERVICE] Critical failure writing to fallback file '{FALLBACK_EXCEL_PATH}': {e}")
        return False