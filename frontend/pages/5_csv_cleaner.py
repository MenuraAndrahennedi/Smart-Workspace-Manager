import logging

import streamlit as st

from backend.database.db import get_db_session
from backend.services.analysis_service import CSVAnalysisError, CSVLimitError
from backend.services.cleaning_service import (
    CleaningOptions,
    DataCleaningError,
    discard_cleaning_result,
    get_cleaning_column_options,
    load_cleaning_source,
    preview_cleaning,
    save_cleaning_result,
)
from backend.services.file_service import read_managed_file_bytes
from frontend.ui_helpers import commit_session_changes, select_analyzable_csv

logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="CSV Cleaner", 
    page_icon=":material/folder_open:", 
    layout="wide"
)

st.title("CSV Cleaner")
st.caption("Select an organized CSV file and save & export the cleaned data.")

with get_db_session() as session:
    with st.form("csv_cleaning_form"):
        cleaning_file_id = select_analyzable_csv(
            session,
            empty_message="No organized CSV files are available for cleaning.",
        )

        preview_rows = st.number_input(
            "Preview rows",
            min_value=1,
            max_value=50,
            value=10,
            step=1,
        )
    
        select_file_clicked = st.form_submit_button(
            "Select to Clean",
            type="primary",
        )

        if select_file_clicked:
            st.session_state["cleaning_file_id"] = cleaning_file_id
            st.session_state.pop("cleaned_results", None)
            st.session_state.pop("cleaned_results_file_id", None)
            if cleaning_file_id is None:
                st.warning("Please select a file to clean.")

            else: 
                st.session_state.pop("original_file_preview", None)
                st.session_state.pop("cleaning_options", None)
                st.session_state.pop("cleaned_results", None)
                st.session_state.pop("cleaned_results_file_id", None)
                try:
                    selected_file_df = load_cleaning_source(
                        session,
                        cleaning_file_id,
                    )
                    st.session_state["original_file_preview"] = selected_file_df
                    st.session_state["cleaning_file_id"] = cleaning_file_id

                except CSVLimitError as error:
                    st.warning(str(error))
    
                except CSVAnalysisError as error:
                    st.error(str(error))

                except DataCleaningError as error:
                    st.error(str(error))

                except Exception:
                    logger.exception(
                        "Unexpected CSV loading failure for file ID %s.",
                        cleaning_file_id,
                    )
                    st.error("An unexpected error occurred while loading the CSV.")
            
                        
    cleaning_options = st.session_state.get("cleaning_options")
    cleaning_file_id = st.session_state.get("cleaning_file_id")
    selected_file_df = st.session_state.get("original_file_preview")

    if cleaning_file_id is not None and selected_file_df is not None:
        cleaning_column_options = get_cleaning_column_options(selected_file_df)

        # Remove Duplicates
        remove_duplicates = st.checkbox(label = "Remove duplicate rows")
        if remove_duplicates:
            remove_duplictes_option = st.radio(
                label = "Compare using:",
                options = ["All columns", "Selected Columns"],
            )
            if remove_duplictes_option == "Selected Columns":
                remove_duplicate_subset = st.multiselect(
                    "Columns to drop duplicates",
                    options=selected_file_df.columns,
                    default=None,
                    key=f"duplicate_columns_{cleaning_file_id}",
                )
            elif remove_duplictes_option == "All columns":
                remove_duplicate_subset = None
        else:
            remove_duplicate_subset = None

        # Fill numerical missing values
        fill_numeric_missing = st.checkbox(label = "Fill numerical missing values")
        if fill_numeric_missing:
            fill_numeric_column = st.selectbox(
                "Column to fill",
                options=cleaning_column_options.numeric_columns,
                index=None,
                key=f"numeric_fill_column_{cleaning_file_id}",
            )

            fill_numeric_strategy = st.radio(
                label = "Strategy:",
                options = ["Mean", "Median", "Constant"],
            )
            if fill_numeric_strategy == "Constant":
                numeric_fill_value = st.number_input(
                    "Fill value:"
                )
            elif fill_numeric_strategy == "Mean" or fill_numeric_strategy == "Median":
                numeric_fill_value = None
        else:
            fill_numeric_column = None
            fill_numeric_strategy = None
            numeric_fill_value = None

        # Fill text missing values
        fill_text_missing = st.checkbox(label = "Fill text missing values")
        if fill_text_missing:
            fill_text_column = st.selectbox(
                "Column to fill",
                options=cleaning_column_options.text_columns,
                index=None,
                key=f"text_fill_column_{cleaning_file_id}",
            )

            text_fill_value = st.text_input(
                label = "Fill value:",
            )
        else:
            fill_text_column =None
            text_fill_value=None

        # Drop remaining missing values
        drop_remaining_missing = st.checkbox(label = "Remove remaining missing values")
        if drop_remaining_missing:
            remaining_missing_option = st.radio(
                label = "Check:",
                options = ["All columns", "Selected Columns"],
            )
            if remaining_missing_option == "Selected Columns":
                remaining_missing_subset = st.multiselect(
                    "Columns to drop missing values",
                    options=selected_file_df.columns,
                    default=None,
                    key=f"missing_columns_{cleaning_file_id}",
                )
            else:
                remaining_missing_subset =None
        else:
            remaining_missing_subset = None

        cleaning_options = CleaningOptions(
            remove_duplicates = remove_duplicates,
            duplicate_columns = (
                tuple(remove_duplicate_subset)
                if remove_duplicate_subset is not None
                else None
            ),

            numeric_fill_column = fill_numeric_column,
            numeric_fill_strategy = (
                fill_numeric_strategy.lower()
                if fill_numeric_strategy is not None
                else None
            ),
            numeric_fill_value = numeric_fill_value,
            
            text_fill_column = fill_text_column,
            text_fill_value =  text_fill_value,
             
            drop_missing_rows = drop_remaining_missing,
            drop_missing_columns = (
                tuple(remaining_missing_subset)
                if remaining_missing_subset is not None
                else None
            ),
        )

        previous_options = st.session_state.get("cleaning_options")
        if previous_options != cleaning_options:
            st.session_state.pop("cleaned_results", None)
            st.session_state.pop("cleaned_results_file_id", None)

        st.session_state["cleaning_options"] = cleaning_options

    clean_clicked = st.button(
        "Proceed Cleaning",
        type="primary",
    )

    if clean_clicked: 
        if cleaning_file_id is None or cleaning_options is None:
            st.warning("Please select a CSV file before cleaning.")
        else:
            try:
                with st.spinner("Cleaning CSV file..."):
                    cleaned_results = preview_cleaning(
                            session=session,
                            file_id=cleaning_file_id,
                            cleaning_options=cleaning_options,
                    )
                    st.session_state["cleaned_results"] = cleaned_results
                    st.session_state["cleaned_results_file_id"] = cleaning_file_id
                 
            except DataCleaningError as error:
                st.error(str(error))

            except CSVLimitError as error:
                st.warning(str(error))

            except CSVAnalysisError as error:
                st.error(str(error))

            except Exception:
                logger.exception(
                    "Unexpected cleaning failure for file ID %s.",
                    cleaning_file_id,
                )
                st.error("An unexpected error occurred while cleaning the CSV.")

    cleaned_results = st.session_state.get("cleaned_results")
    cleaned_results_file_id = st.session_state.get("cleaned_results_file_id")

    if (
        cleaned_results is not None
        and cleaned_results_file_id == cleaning_file_id
    ):
        st.header("Analysis details")
        row1, row2, row3, row4, row5, row6 = st.columns(6)

        row1.metric("Original Row Count", cleaned_results.original_row_count)
        row2.metric("Cleaned Row Count", cleaned_results.cleaned_row_count)
        row3.metric("Duplicates Removed", cleaned_results.duplicates_removed)
        row4.metric("Missing Values Filled", cleaned_results.missing_values_filled)
        row5.metric("Rows Dropped", cleaned_results.rows_dropped)
        row6.metric("Remaining Missing Values", cleaned_results.remaining_missing_values)

        st.subheader("Cleaned Data Preview")
        st.dataframe(
            cleaned_results.cleaned_dataframe.iloc[0:preview_rows],
            width="stretch",
            hide_index=True,
        )

        save_clicked = st.button(
            "Save Cleaned Data",
            type="primary",
        )

        if save_clicked:
            try:
                with st.spinner("Saving cleaned data..."):
                    saved_results = save_cleaning_result(
                        session=session,
                        file_id=cleaning_file_id,
                        cleaned_dataframe=cleaned_results.cleaned_dataframe,
                    )
                    saved = commit_session_changes(
                        session,
                        logger,
                        "The cleaned files were created, but their database records could not be saved.",
                    )

                if saved:
                    st.success(f"Cleaned data is saved as CSV in {saved_results.csv_path} ")
                    st.success(f"Cleaned data is saved as Excel in {saved_results.excel_path} ")

                    with st.container(horizontal=True):
                        st.download_button(
                            label="Download CSV",
                            data=read_managed_file_bytes(saved_results.csv_path),
                            file_name=saved_results.csv_filename,
                            mime="text/csv",
                            key=f"download_csv_{cleaning_file_id}",
                            icon=":material/download:",
                            on_click="ignore",
                        )
                        st.download_button(
                            label="Download Excel",
                            data=read_managed_file_bytes(saved_results.excel_path),
                            file_name=saved_results.excel_filename,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key=f"download_excel_{cleaning_file_id}",
                            icon=":material/download:",
                            on_click="ignore",
                        )
                else:
                    discard_cleaning_result(saved_results)

            except DataCleaningError as error:
                st.error(str(error))

            except (OSError, ValueError):
                logger.exception(
                    "Could not save cleaned files for file ID %s.",
                    cleaning_file_id,
                )
                st.error("The cleaned files could not be saved. Please try again.")

            except Exception:
                logger.exception(
                    "Unexpected cleaning export failure for file ID %s.",
                    cleaning_file_id,
                )
                st.error(
                    "An unexpected error occurred while saving the cleaned files."
                )











                



            


                



            
