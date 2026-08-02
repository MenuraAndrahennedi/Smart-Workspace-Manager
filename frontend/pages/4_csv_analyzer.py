import logging

import pandas as pd
import streamlit as st

from backend.database.db import get_db_session
from backend.services.analysis_service import CSVAnalysisError, CSVLimitError, analyze_file_and_record_job, filter_csv_data
from frontend.ui_helpers import commit_session_changes, select_analyzable_csv

logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="CSV Analyzer", 
    page_icon=":material/folder_open:", 
    layout="wide"
)

st.title("CSV Analyzer")
st.caption("Select an organized CSV file and inspect its contents.")



with get_db_session() as session:
    with st.form("csv_analysis_form"):
        selected_file_id = select_analyzable_csv(
            session,
            empty_message="No organized CSV files are available for analysis.",
        )
        
        preview_rows = st.number_input(
            "Preview rows",
            min_value=1,
            max_value=50,
            value=10,
            step=1,
        )

        analyze_clicked = st.form_submit_button(
            "Analyze CSV",
            type="primary",
        )

    if analyze_clicked:
        if selected_file_id is None:
            st.warning("Please select a file to analyze.")

        else:
            st.session_state.pop("csv_analysis_result", None)
            st.session_state.pop("analyzed_file_id", None)
            st.session_state.pop("analysis_job_id", None)
            st.session_state.pop("filtered_csv_data", None)
            st.session_state.pop("filtered_csv_configuration", None)

            try:
                with st.spinner("Analyzing CSV file..."):
                    recorded_analysis = (
                        analyze_file_and_record_job(
                            session=session,
                            file_id=selected_file_id,
                            preview_rows=int(preview_rows),
                        )
                    )

                if commit_session_changes(
                    session,
                    logger,
                    "The analysis completed, but its database record could not be saved.",
                ):
                    st.session_state["csv_analysis_result"] = recorded_analysis.result
                    st.session_state["analyzed_file_id"] = selected_file_id
                    st.session_state["analysis_job_id"] = recorded_analysis.job_id
                    st.success(f"File analyzed successfully. Analysis job ID: {recorded_analysis.job_id}")

            except CSVLimitError as error:
                if commit_session_changes(
                    session,
                    logger,
                    "The analysis failure could not be recorded.",
                ):
                    st.warning(str(error))

            except CSVAnalysisError as error:
                if commit_session_changes(
                    session,
                    logger,
                    "The analysis failure could not be recorded.",
                ):
                    st.error(str(error))

            except Exception:
                logger.exception(
                    "Unexpected analysis failure for file ID %s.",
                    selected_file_id,
                )
                if commit_session_changes(
                    session,
                    logger,
                    "The analysis failure could not be recorded.",
                ):
                    st.error("An unexpected error occurred while analyzing the CSV.")

    result = st.session_state.get("csv_analysis_result")
    analyzed_file_id = st.session_state.get("analyzed_file_id")
    
    if result is not None and analyzed_file_id == selected_file_id:
        st.header("Analysis details")

        row1, row2, row3, row4 = st.columns(4)

        missing_count = sum(result.missing_values.values())

        row1.metric("Rows", result.row_count)
        row2.metric("Columns", result.column_count)
        row3.metric("Missing values", missing_count)
        row4.metric("Duplicate rows", result.duplicate_count)

        st.subheader("Data Preview")
        st.dataframe(
            result.preview,
            width="stretch",
            hide_index=True,
        )

        column_summary = pd.DataFrame(
            {
                "Column": result.columns,
                "Data type": [
                    result.data_types[column]
                    for column in result.columns
                ],
                "Missing values": [
                    result.missing_values[column]
                    for column in result.columns
                ],
            }
        )

        st.subheader("Column Summary")
        st.dataframe(
            column_summary,         
            width="stretch", 
            hide_index=True,
        )

        st.subheader("Descriptive Statistics")
        st.dataframe(
            result.descriptive_statistics,
            width="stretch",
        )

        # Detailed missing values
        missing_table = pd.DataFrame(
            {
                "Column": result.columns,
                "Missing count": [
                    result.missing_values[column]
                    for column in result.columns
                ],
            }
        )

        missing_table["Missing percentage"] = (
            missing_table["Missing count"]
            / result.row_count
            * 100
        ).round(2)

        missing_table = missing_table[
            missing_table["Missing count"] > 0
        ]

        st.subheader("Missing Values")

        if missing_table.empty:
            st.success("No missing values were detected.")
        else:
            st.dataframe(
                missing_table,
                width="stretch",
                hide_index=True,
            )

        # Custom Data Display 
        st.subheader("Custom Data Display")

        selected_columns = st.multiselect(
            "Columns to display",
            options=result.columns,
            default=None,
            key=f"csv_columns_{analyzed_file_id}",
        )

        filter_options = ["No filter", *result.columns]

        selected_filter_column = st.selectbox(
            "Filter column",
            options=filter_options,
            key=f"csv_filter_column_{analyzed_file_id}",
        )

        filter_column: str | None = None
        operator: str | None = None
        filter_value: str | None = None

        if selected_filter_column != "No filter":
            filter_column = selected_filter_column

            dtype_name = result.data_types[filter_column].lower()

            is_numeric_column = dtype_name.startswith(("int", "uint", "float"))

            if is_numeric_column:
                operator = st.selectbox(
                    "Condition",
                    options=[
                        "Equals",
                        "Greater than",
                        "Less than",
                    ],
                    key=f"csv_numeric_operator_{analyzed_file_id}",
                )

                filter_value = st.text_input(
                    "Numeric value",
                    key=f"csv_numeric_value_{analyzed_file_id}",
                )

            else:
                operator = st.selectbox(
                    "Condition",
                    options=[
                        "Contains",
                        "Equals",
                        "Starts with",
                    ],
                    key=f"csv_text_operator_{analyzed_file_id}",
                )

                filter_value = st.text_input(
                    "Text value",
                    key=f"csv_text_value_{analyzed_file_id}",
                )

        apply_filter_clicked = st.button(
            "Apply Selection and Filter",
            type="primary",
            key=f"apply_csv_filter_{analyzed_file_id}",
        )

        current_filter_configuration = (
            analyzed_file_id,
            tuple(selected_columns),
            filter_column,
            operator,
            filter_value,
        )

        if apply_filter_clicked:
            if not selected_columns:
                st.warning("Select at least one column.")

            else:
                try:
                    with st.spinner("Applying selection and filter..."):
                        filtered_dataframe = filter_csv_data(
                            session=session,
                            file_id=analyzed_file_id,
                            selected_columns=selected_columns,
                            filter_column=filter_column,
                            operator=operator,
                            filter_value=filter_value,
                            maximum_result_rows=100,
                        )

                    st.session_state["filtered_csv_data"] = (filtered_dataframe)
                    st.session_state["filtered_csv_configuration"] = (current_filter_configuration)

                except CSVLimitError as error:
                    st.warning(str(error))
                except CSVAnalysisError as error:
                    st.error(str(error))
                except Exception:
                    logger.exception(
                        "Unexpected filtering failure for file ID %s.",
                        analyzed_file_id,
                    )
                    st.error("The CSV filter could not be applied. Please try again.")

        filtered_dataframe = st.session_state.get("filtered_csv_data")
        applied_configuration = st.session_state.get("filtered_csv_configuration")

        if (filtered_dataframe is not None and applied_configuration == current_filter_configuration):
            st.subheader("Selected Data")

            st.caption(f"Showing {len(filtered_dataframe)} row(s), limited to a maximum of 100 rows.")

            st.dataframe(
                filtered_dataframe,
                width="stretch",
                hide_index=True,
            )

        elif filtered_dataframe is not None:
            st.info("The controls have changed. Click 'Apply Selection and Filter' button to update the table.")








