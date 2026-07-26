from pathlib import Path
import sys

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from backend.services.file_service import upload_file
from backend.database.db import get_db_session
from backend.utils.constants import FILE_TYPE_GROUPS
from backend.utils.file_utils import format_file_size
from backend.config.settings import MAX_UPLOAD_SIZE_MB

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

# Streamlit built-in UploadedFile object -> name, size, type
uploaded_file = st.file_uploader(
    "Choose a file",
    type=[extension for extensions in FILE_TYPE_GROUPS.values() for extension in extensions],
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
                    st.success("File uploaded successfully.")
                    st.subheader("Upload Details")
                    st.write("Original name:", result.original_filename)
                    st.write("Stored name:", result.stored_filename)
                    st.write("File type:", result.extension.upper())
                    st.write("File size:", format_file_size(result.size_bytes))
                    st.write("Location:", result.saved_path)
                except Exception as error:
                    st.error(str(error))



        



 












