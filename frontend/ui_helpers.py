import logging

import streamlit as st
from sqlalchemy.orm import Session

from backend.database.db import SESSION_FINALIZED_KEY
from backend.services.analysis_service import get_analyzable_csv_files
from backend.utils.file_utils import format_file_size

logger = logging.getLogger(__name__)


def normalize_exclusive_all_selection(
    selected_options: list[str],
    previous_options: list[str],
    all_option: str = "All",
) -> list[str]:
    if not selected_options:
        return [all_option]
    if all_option not in selected_options:
        return selected_options
    if all_option not in previous_options:
        return [all_option]

    specific_options = [
        option
        for option in selected_options
        if option != all_option
    ]
    return specific_options or [all_option]


def enforce_exclusive_all_selection(
    widget_key: str,
    all_option: str = "All",
) -> None:
    previous_key = f"_{widget_key}_previous"
    selected_options = list(st.session_state.get(widget_key, []))
    previous_options = list(
        st.session_state.get(previous_key, [all_option])
    )
    normalized_options = normalize_exclusive_all_selection(
        selected_options,
        previous_options,
        all_option,
    )
    st.session_state[widget_key] = normalized_options
    st.session_state[previous_key] = normalized_options


def commit_session_changes(
    session: Session,
    page_logger: logging.Logger,
    error_message: str,
) -> bool:
    try:
        session.commit()
        session.info[SESSION_FINALIZED_KEY] = True
        return True
    except Exception:
        session.rollback()
        session.info[SESSION_FINALIZED_KEY] = True
        page_logger.exception("Database commit failed.")
        st.error(error_message)
        return False


def select_analyzable_csv(
    session: Session,
    *,
    empty_message: str,
    index: int | None = 0,
    key: str | None = None,
    placeholder: str | None = None,
) -> int | None:
    try:
        csv_files = get_analyzable_csv_files(session)
    except Exception:
        logger.exception("Could not load the available CSV files.")
        st.error("Available CSV files could not be loaded. Please try again.")
        st.stop()
    if not csv_files:
        st.info(empty_message)
        st.stop()

    file_lookup = {file_record.id: file_record for file_record in csv_files}
    selected_file_id = st.selectbox(
        "Select CSV file",
        options=list(file_lookup),
        index=index,
        format_func=lambda file_id: (
            f"{file_lookup[file_id].original_name} - "
            f"{format_file_size(file_lookup[file_id].size_bytes)}"
        ),
        key=key,
        placeholder=placeholder,
    )
    return selected_file_id
