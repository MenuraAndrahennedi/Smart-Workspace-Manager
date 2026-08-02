import logging
from pathlib import Path

import streamlit as st

from backend.services.file_service import UploadValidationError, upload_file
from backend.services.automation_service import organize_uploaded_file
from backend.database.db import get_db_session
from backend.utils.constants import FILE_TYPE_GROUPS
from backend.utils.file_utils import format_file_size
from backend.config.settings import MAX_UPLOAD_SIZE_MB
from frontend.ui_helpers import commit_session_changes

logger = logging.getLogger(__name__)


def clear_latest_upload_details() -> None:
    st.session_state.pop("latest_upload_details", None)


st.set_page_config(
    page_title="File Upload", 
    page_icon="SWM", 
    layout="wide"
)

st.title("Upload File")
st.write("Select a file to store it in the managed workspace.")
st.caption(
    f"Maximum upload size: {MAX_UPLOAD_SIZE_MB} MB"
)

st.html(
    """
    <style>
    [data-testid="stFileUploader"] button[aria-label="Add files"] {
        display: none;
    }
    </style>
    """
)

st.session_state.setdefault("upload_widget_version", 0)
upload_widget_key = f"file_upload_{st.session_state['upload_widget_version']}"

# Streamlit built-in UploadedFile object -> name, size, type
uploaded_file = st.file_uploader(
    "Choose a single file",
    type=[extension for extensions in FILE_TYPE_GROUPS.values() for extension in extensions],
    accept_multiple_files=False,
    key=upload_widget_key,
    on_change=clear_latest_upload_details,
    max_upload_size=MAX_UPLOAD_SIZE_MB,
)

upload_clicked = st.button("Upload File")

if upload_clicked:
    if uploaded_file is None:
        st.warning("Please select a file before uploading.")
    else:
        filename = uploaded_file.name
        file_bytes = uploaded_file.getvalue() # Get the raw binary data
        with get_db_session() as session:
            with st.spinner("Uploading file..."):
                try:
                    result = upload_file(
                        filename,
                        file_bytes,
                        session
                    )
                    organized = organize_uploaded_file(
                        session,
                        result.file_id,
                        Path(result.saved_path),
                    )
                    if commit_session_changes(
                        session,
                        logger,
                        "The file was processed, but its database changes could not be saved.",
                    ):
                        st.session_state["latest_upload_details"] = {
                            "original_name": result.original_filename,
                            "stored_name": result.stored_filename,
                            "extension": result.extension.upper(),
                            "category": organized.category,
                            "size": format_file_size(result.size_bytes),
                            "location": str(organized.destination_path),
                        }
                        st.session_state["upload_widget_version"] += 1
                        st.rerun()
                except UploadValidationError as error:
                    st.error(str(error))
                except FileExistsError:
                    logger.exception("Could not allocate a unique upload filename.")
                    if commit_session_changes(
                        session,
                        logger,
                        "The upload failure could not be recorded.",
                    ):
                        st.error("The file could not be uploaded because its name conflicts with an existing file.")
                except Exception:
                    logger.exception("Could not upload and organize the selected file.")
                    if commit_session_changes(
                        session,
                        logger,
                        "The upload failed and its database status could not be saved.",
                    ):
                        st.error("The file could not be uploaded and organized. Please try again.")


latest_upload_details = st.session_state.get("latest_upload_details")
if latest_upload_details is not None:
    st.success("File uploaded and organized successfully.")
    st.subheader("Upload Details")
    st.write("Original name:", latest_upload_details["original_name"])
    st.write("Stored name:", latest_upload_details["stored_name"])
    st.write("File type:", latest_upload_details["extension"])
    st.write("Category:", latest_upload_details["category"])
    st.write("File size:", latest_upload_details["size"])
    st.write("Location:", latest_upload_details["location"])



        



 











