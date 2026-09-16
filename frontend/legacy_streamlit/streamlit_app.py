import logging

import streamlit as st

from backend.database.db import get_db_session
from backend.services.auth_service import authenticate_user
from backend.utils.logging_config import configure_logging

configure_logging()
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="Smart Workspace Manager", 
    page_icon="SWM", 
    layout="wide"
)

st.session_state.setdefault("legacy_user_id", None)
st.session_state.setdefault("legacy_user_email", None)


def sign_out() -> None:
    st.session_state["legacy_user_id"] = None
    st.session_state["legacy_user_email"] = None


if st.session_state["legacy_user_id"] is None:
    st.title("Smart Workspace Manager")
    st.caption("Legacy Streamlit interface")

    with st.form("legacy_login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button(
            "Sign in",
            type="primary",
            icon=":material/login:",
        )

    if submitted:
        try:
            with get_db_session() as session:
                user = authenticate_user(session, email, password)
        except Exception:
            logger.exception("Legacy Streamlit sign-in failed.")
            st.error("The database could not be reached. Please try again.")
        else:
            if user is None:
                st.error("Invalid email or password.")
            else:
                st.session_state["legacy_user_id"] = user.id
                st.session_state["legacy_user_email"] = user.email
                st.rerun()

    st.stop()

with st.sidebar:
    st.caption("Signed in as")
    st.write(st.session_state["legacy_user_email"])
    st.button(
        "Sign out",
        icon=":material/logout:",
        on_click=sign_out,
    )

page = st.navigation(
    [
        st.Page("app_pages/1_dashboard.py", title="Dashboard", icon=":material/dashboard:"),
        st.Page("app_pages/2_file_upload.py", title="Upload", icon=":material/upload_file:"),
        st.Page("app_pages/3_file_library.py", title="Library", icon=":material/folder:"),
        st.Page("app_pages/4_csv_analyzer.py", title="CSV analyzer", icon=":material/analytics:"),
        st.Page("app_pages/5_csv_cleaner.py", title="CSV cleaner", icon=":material/cleaning_services:"),
        st.Page("app_pages/6_generate_reports.py", title="Reports", icon=":material/description:"),
        st.Page("app_pages/7_xlsx_to_csv.py", title="XLSX to CSV", icon=":material/table_view:"),
    ]
)
page.run()
