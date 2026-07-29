from pathlib import Path
import sys
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from backend.database.db import get_db_session
from backend.database.repositories import query_files
from backend.services.file_service import delete_actual_file
from backend.utils.constants import ORGANIZER_CATEGORY_RULES
from backend.utils.file_utils import format_file_size

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
select_category = st.segmented_control(
    label="Filter category",
    options=category_options,
    selection_mode="multi",
    default=["All"],
)

category_filter = None
if select_category and "All" not in select_category:
    category_filter = [
        category.lower()
        for category in select_category
    ]

status_options = ["All", "Uploaded", "Organized", "Failed"]
select_status = st.segmented_control(
    label="Filter status",
    options=status_options,
    selection_mode="multi",
    default=["All"],
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

            except FileNotFoundError as error:
                st.error(str(error))

            except Exception:
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
    files = query_files(
        session=session,
        search_term=search_term_input,
        category=category_filter,
        status=status_filter,
    )
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

            file_path = Path(file_record.storage_path)
            if file_path.is_file():
                st.download_button(
                    label="Download",
                    data=lambda path=file_path: path.read_bytes(),
                    file_name=file_record.original_name,
                    mime="application/octet-stream", # Unknown binary file (stream of 8-bit bytes)
                    key=f"download_{file_record.id}",
                    icon=":material/download:",
                    on_click="ignore",
                )
            else: 
                st.warning("The database record exists, but the stored file is missing.")

            if st.button(
                "Delete",
                key=f"delete_{file_record.id}",
            ):
                confirm_delete(
                    file_id=file_record.id,
                    original_name=file_record.original_name,
                )
