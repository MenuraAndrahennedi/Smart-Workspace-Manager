import logging

import streamlit as st

from backend.database.db import get_db_session
from backend.services.file_service import (
    delete_actual_file,
    get_download_path,
    get_library_files,
    read_managed_file_bytes,
)
from backend.utils.constants import ORGANIZER_CATEGORY_RULES
from backend.utils.file_utils import format_file_size
from frontend.ui_helpers import enforce_exclusive_all_selection

logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="File Library", 
    page_icon=":material/folder_open:", 
    layout="wide"
)

st.title("File Library")
st.caption(
    "Search, filter, download, and manage uploaded files."
)

# Search bar
search_term_input = st.text_input(label = "Search Files", placeholder = "Search files here")

#Filters
category_options = [
    "All",
    *[
        category.capitalize()
        for category in ORGANIZER_CATEGORY_RULES.keys()
    ],
    "Others",
]
category_widget_key = "file_library_categories"
st.session_state.setdefault(category_widget_key, ["All"])
st.session_state.setdefault(f"_{category_widget_key}_previous", ["All"])
select_category = st.segmented_control(
    label="Filter category",
    options=category_options,
    selection_mode="multi",
    key=category_widget_key,
    on_change=enforce_exclusive_all_selection,
    args=(category_widget_key,),
)

category_filter = None
if select_category and "All" not in select_category:
    category_filter = [
        category.lower()
        for category in select_category
    ]

status_options = ["All", "Uploaded", "Organized", "Failed"]
status_widget_key = "file_library_statuses"
st.session_state.setdefault(status_widget_key, ["All"])
st.session_state.setdefault(f"_{status_widget_key}_previous", ["All"])
select_status = st.segmented_control(
    label="Filter status",
    options=status_options,
    selection_mode="multi",
    key=status_widget_key,
    on_change=enforce_exclusive_all_selection,
    args=(status_widget_key,),
)

status_filter = None
if select_status and "All" not in select_status:
    status_filter = [
        status.lower()
        for status in select_status
    ]


# Delete Confirmation
@st.dialog("Confirm deletion", dismissible=False)
def confirm_delete(
    file_id: int,
    original_name: str,
) -> None:
    st.warning(
        f'Are you sure you want to permanently delete "{original_name}"?'
    )

    cancel_column, delete_column = st.columns(2)

    with cancel_column:
        if st.button(
            "Cancel",
            key=f"cancel_delete_{file_id}",
            width="stretch",
        ):
            st.rerun()

    with delete_column:
        if st.button(
            "Yes, delete",
            key=f"confirm_delete_{file_id}",
            type="primary",
            width="stretch",
        ):
            try:
                with get_db_session() as delete_session:
                    delete_actual_file(
                        session=delete_session,
                        file_id=file_id,
                    )

                st.session_state["delete_success"] = (
                    f'"{original_name}" was permanently deleted successfully.'
                )

                st.rerun()

            except FileNotFoundError:
                logger.warning(
                    "Delete requested for missing file ID %s.",
                    file_id,
                )
                st.error("The selected file no longer exists.")

            except Exception:
                logger.exception("Could not delete file ID %s.", file_id)
                st.error("The file could not be deleted.")


# Delete success message display 
delete_success = st.session_state.pop(
    "delete_success",
    None,
)

if delete_success:
    st.success(delete_success)

# Search and get files (Can delete)
with get_db_session() as session:
    try:
        files = get_library_files(
            session=session,
            search_term=search_term_input,
            category=category_filter,
            status=status_filter,
        )
    except Exception:
        logger.exception("Could not load the file library.")
        st.error("The file library could not be loaded. Please try again.")
        st.stop()
    if not files:
        st.info("No files matched your search and filters.")
        st.stop()

    st.write(f"Found {len(files)} files")

    for file_record in files:
        with st.container(border=True):
            st.subheader(file_record.original_name)

            st.write(f"Stored name: {file_record.stored_name}")
            st.write(f"Type: {file_record.category} / .{file_record.extension}")
            st.write(f"Size: {format_file_size(file_record.size_bytes)}")
            st.write(f"Status: {file_record.status}")
            st.write(f"Location: {file_record.storage_path}")

            try:
                file_path = get_download_path(file_record.storage_path)
                st.download_button(
                    label="Download",
                    data=read_managed_file_bytes(file_path),
                    file_name=file_record.original_name,
                    mime="application/octet-stream", # Unknown binary file (stream of 8-bit bytes)
                    key=f"download_{file_record.id}",
                    icon=":material/download:",
                    on_click="ignore",
                )
            except (FileNotFoundError, ValueError):
                logger.warning(
                    "Stored file is unavailable for file ID %s.",
                    file_record.id,
                )
                st.warning("The database record exists, but the stored file is missing.")

            if st.button(
                "Delete",
                key=f"delete_{file_record.id}",
            ):
                confirm_delete(
                    file_id=file_record.id,
                    original_name=file_record.original_name,
                )
