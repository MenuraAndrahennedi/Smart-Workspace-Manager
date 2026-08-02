import logging

import streamlit as st

from backend.database.db import get_db_session
from backend.services.file_service import read_managed_file_bytes
from backend.services.xlsx_to_csv_service import (
    XLSXConversionError,
    convert_xlsx_to_csv,
    discard_conversion_output,
    get_convertible_xlsx_files,
    get_xlsx_sheet_names,
    preview_xlsx_sheet,
)
from backend.utils.file_utils import format_file_size
from frontend.ui_helpers import commit_session_changes


logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="XLSX to CSV",
    page_icon=":material/csv:",
    layout="wide",
)

st.title("XLSX to CSV")
st.caption("Convert one worksheet from an organized XLSX workbook into CSV.")

with get_db_session() as session:
    try:
        workbooks = get_convertible_xlsx_files(session)
    except Exception:
        logger.exception("Could not load XLSX workbooks.")
        st.error("Available XLSX workbooks could not be loaded. Please try again.")
        st.stop()

    if not workbooks:
        st.info("No organized XLSX workbooks are available for conversion.")
        st.stop()

    workbook_lookup = {
        file_record.id: file_record
        for file_record in workbooks
    }
    selected_file_id = st.selectbox(
        "Select XLSX workbook",
        options=list(workbook_lookup),
        format_func=lambda file_id: (
            f"{workbook_lookup[file_id].original_name} - "
            f"{format_file_size(workbook_lookup[file_id].size_bytes)}"
        ),
    )

    try:
        sheet_names = get_xlsx_sheet_names(session, selected_file_id)
    except XLSXConversionError as error:
        st.error(str(error))
        st.stop()
    except Exception:
        logger.exception(
            "Could not read worksheet names for file ID %s.",
            selected_file_id,
        )
        st.error("The workbook could not be read. Please try again.")
        st.stop()

    selected_sheet = st.selectbox("Select worksheet", options=sheet_names)
    preview_rows = st.number_input(
        "Preview rows",
        min_value=1,
        max_value=50,
        value=10,
        step=1,
    )

    with st.container(horizontal=True):
        preview_clicked = st.button(
            "Preview worksheet",
            icon=":material/preview:",
        )
        convert_clicked = st.button(
            "Convert to CSV",
            type="primary",
            icon=":material/sync_alt:",
        )

    current_selection = (selected_file_id, selected_sheet)

    if preview_clicked:
        try:
            with st.spinner("Loading worksheet preview..."):
                preview_result = preview_xlsx_sheet(
                    session=session,
                    file_id=selected_file_id,
                    sheet_name=selected_sheet,
                    preview_rows=preview_rows,
                )
            st.session_state["xlsx_preview_result"] = preview_result
            st.session_state["xlsx_preview_selection"] = current_selection
        except XLSXConversionError as error:
            st.error(str(error))
        except Exception:
            logger.exception(
                "Could not preview worksheet %s for file ID %s.",
                selected_sheet,
                selected_file_id,
            )
            st.error("The worksheet preview could not be loaded. Please try again.")

    preview_result = st.session_state.get("xlsx_preview_result")
    preview_selection = st.session_state.get("xlsx_preview_selection")
    if preview_result is not None and preview_selection == current_selection:
        metric1, metric2 = st.columns(2)
        metric1.metric("Rows", preview_result.row_count)
        metric2.metric("Columns", preview_result.column_count)
        st.subheader("Worksheet preview")
        st.dataframe(
            preview_result.dataframe,
            width="stretch",
            hide_index=True,
        )

    if convert_clicked:
        conversion_result = None
        committed = False
        try:
            with st.spinner("Converting worksheet to CSV..."):
                conversion_result = convert_xlsx_to_csv(
                    session=session,
                    file_id=selected_file_id,
                    sheet_name=selected_sheet,
                )
                committed = commit_session_changes(
                    session,
                    logger,
                    "The CSV was created, but its database record could not be saved.",
                )

            if committed:
                st.session_state["xlsx_conversion_result"] = conversion_result
                st.session_state["xlsx_conversion_bytes"] = read_managed_file_bytes(
                    conversion_result.csv_path
                )
                st.success("Worksheet converted and saved as an organized CSV.")
            else:
                discard_conversion_output(conversion_result.csv_path)
        except XLSXConversionError as error:
            st.error(str(error))
        except (OSError, ValueError):
            logger.exception(
                "Could not convert worksheet %s for file ID %s.",
                selected_sheet,
                selected_file_id,
            )
            if conversion_result is not None and not committed:
                discard_conversion_output(conversion_result.csv_path)
            if committed:
                st.error(
                    "The CSV was saved, but its download could not be prepared."
                )
            else:
                st.error("The CSV could not be created. Please try again.")
        except Exception:
            logger.exception(
                "Unexpected XLSX conversion failure for file ID %s.",
                selected_file_id,
            )
            if conversion_result is not None and not committed:
                discard_conversion_output(conversion_result.csv_path)
            st.error("An unexpected error occurred while converting the workbook.")

    saved_result = st.session_state.get("xlsx_conversion_result")
    saved_bytes = st.session_state.get("xlsx_conversion_bytes")
    if saved_result is not None and saved_bytes is not None:
        st.subheader("Latest converted CSV")
        detail1, detail2, detail3 = st.columns(3)
        detail1.metric("Rows", saved_result.row_count)
        detail2.metric("Columns", saved_result.column_count)
        detail3.metric("File size", format_file_size(saved_result.size_bytes))
        st.write(f"Filename: {saved_result.csv_filename}")
        st.download_button(
            "Download CSV",
            data=saved_bytes,
            file_name=saved_result.csv_filename,
            mime="text/csv",
            icon=":material/download:",
            on_click="ignore",
        )
