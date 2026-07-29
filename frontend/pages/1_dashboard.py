from pathlib import Path
import sys

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from backend.database.db import get_db_session
from backend.services.dashboard_service import get_dashboard_data
from backend.utils.file_utils import format_file_size

st.set_page_config(
    page_title="Dashboard", 
    page_icon=":material/dashboard:", 
    layout="wide"
)

st.title("Dashboard")
st.caption("Overview of your managed workspace files.")

try:
    with get_db_session() as session:
        dashboard_data = get_dashboard_data(
            session=session,
            recent_limit=5,
        )

    column1, column2, column3, column4 = st.columns(4)

    column1.metric(
        "Total Files",
        dashboard_data["total_files"],
    )

    column2.metric(
        "Total Size",
        format_file_size(dashboard_data["total_size_bytes"]),
    )

    column3.metric(
        "Organized Files",
        dashboard_data["organized_files"],
    )

    column4.metric(
        "Failed Files",
        dashboard_data["failed_files"],
    )

    st.subheader("Recent Activity")
    recent_files = dashboard_data["recent_files"]
    if not recent_files:
        st.info("No recent file activity is available.")

    for file_record in recent_files:
        with st.container(border=True):
            st.subheader(file_record["original_name"])
    
            st.write(f"Stored name: {file_record['stored_name']}")
            st.write(f"Type: {file_record['category']} / .{file_record['extension']}")
            st.write(f"Size: {format_file_size(file_record['size_bytes'])}")
            st.write(f"Status: {file_record['status']}")
            st.write(
                f"Updated at: {file_record['updated_at'].strftime('%d %B %Y, %I:%M %p')}"
            )


    st.subheader("Category Summary")
    category_summary = dashboard_data["category_summary"]
    st.table(
        category_summary,
        border = "horizontal"
    )

except Exception:
    st.error("Dashboard information could not be loaded.")
    st.stop()

