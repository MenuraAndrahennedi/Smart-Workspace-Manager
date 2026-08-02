import logging

import streamlit as st

from backend.config.settings import MAX_REPORT_CHARTS
from backend.database.db import get_db_session
from backend.services.analysis_service import (
    CSVAnalysisError,
    CSVLimitError,
    load_organized_csv,
)
from backend.services.report_service import ReportGenerationError, create_report
from backend.services.file_service import read_managed_file_bytes
from backend.services.visualization_service import (
    ChartConfiguration,
    VisualizationError,
    generate_chart,
    get_chart_selection_options,
)
from backend.utils.constants import VALID_AGGREGATIONS
from frontend.ui_helpers import commit_session_changes, select_analyzable_csv

logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="Generate reports",
    page_icon=":material/description:",
    layout="wide",
)

st.title("Generate reports")
st.caption("Build a report from charts and export it as HTML and PDF.")

st.session_state.setdefault("report_file_id", None)
st.session_state.setdefault("report_charts", [])
st.session_state.setdefault("report_adding_chart", False)
st.session_state.setdefault("saved_report", None)

with get_db_session() as session:
    selected_file_id = select_analyzable_csv(
        session,
        empty_message="No organized CSV files are available for reporting.",
        index=None,
        placeholder="Choose a CSV file",
        key="report_file_select",
    )

    if selected_file_id is None:
        st.info("Select a CSV file to start building a report.")
        st.stop()

    if st.session_state["report_file_id"] != selected_file_id:
        st.session_state["report_file_id"] = selected_file_id
        st.session_state["report_charts"] = []
        st.session_state["report_adding_chart"] = False
        st.session_state["saved_report"] = None

    try:
        _, dataframe = load_organized_csv(session, selected_file_id)
        chart_options = get_chart_selection_options(dataframe)
    except CSVLimitError as error:
        st.warning(str(error))
        st.stop()
    except (CSVAnalysisError, VisualizationError) as error:
        st.error(str(error))
        st.stop()
    except (FileNotFoundError, OSError, ValueError):
        logger.exception(
            "Could not load report source file ID %s.",
            selected_file_id,
        )
        st.error("The selected CSV file is unavailable or could not be read.")
        st.stop()
    except Exception:
        logger.exception(
            "Unexpected report source failure for file ID %s.",
            selected_file_id,
        )
        st.error("The selected CSV file could not be loaded. Please try again.")
        st.stop()

    if not chart_options.available_chart_types:
        st.info("This CSV does not contain columns that can be charted.")
        st.stop()

    report_charts = st.session_state["report_charts"]

    st.subheader("Report charts")
    st.caption(f"{len(report_charts)} of {MAX_REPORT_CHARTS} charts added")

    if not report_charts:
        st.info("Add a chart to begin the report.")

    for index, configuration in enumerate(report_charts):
        with st.container(border=True):
            with st.container(
                horizontal=True,
                horizontal_alignment="distribute",
                vertical_alignment="center",
            ):
                st.markdown(f"**{index + 1}. {configuration.title}**")
                remove_clicked = st.button(
                    "Remove",
                    icon=":material/delete:",
                    key=f"remove_report_chart_{selected_file_id}_{index}",
                )

            if remove_clicked:
                st.session_state["report_charts"].pop(index)
                st.rerun()

            try:
                chart = generate_chart(dataframe, configuration)
                st.plotly_chart(
                    chart.figure,
                    key=f"report_chart_{selected_file_id}_{index}",
                )
            except VisualizationError as error:
                st.error(str(error))

    if len(report_charts) < MAX_REPORT_CHARTS:
        if st.button(
            "Add chart",
            icon=":material/add_chart:",
            disabled=st.session_state["report_adding_chart"],
        ):
            st.session_state["report_adding_chart"] = True

    if st.session_state["report_adding_chart"]:
        with st.container(border=True):
            st.subheader("Add chart")

            chart_type = st.selectbox(
                "Chart type",
                options=chart_options.available_chart_types,
                format_func=str.title,
                key=f"new_report_chart_type_{selected_file_id}",
            )
            chart_title = st.text_input(
                "Chart title",
                value=f"{chart_type.title()} chart",
                key=(
                    f"new_report_chart_title_{selected_file_id}_"
                    f"{len(report_charts)}_{chart_type}"
                ),
            )

            y_column = None
            aggregation = None
            histogram_bins = None

            if chart_type == "histogram":
                x_column = st.selectbox(
                    "Numeric column",
                    options=chart_options.numeric_columns,
                    key=f"new_histogram_x_{selected_file_id}",
                )
                histogram_bins = st.number_input(
                    "Bins",
                    min_value=1,
                    max_value=100,
                    value=20,
                    step=1,
                )

            elif chart_type == "bar":
                x_column = st.selectbox(
                    "Category column",
                    options=chart_options.categorical_columns,
                    key=f"new_bar_x_{selected_file_id}",
                )
                bar_mode = st.segmented_control(
                    "Bar values",
                    options=["Count rows", "Aggregate a numeric column"],
                    default="Count rows",
                )
                if bar_mode == "Aggregate a numeric column":
                    y_column = st.selectbox(
                        "Numeric column",
                        options=chart_options.numeric_columns,
                        key=f"new_bar_y_{selected_file_id}",
                    )
                    aggregation = st.selectbox(
                        "Aggregation",
                        options=list(VALID_AGGREGATIONS),
                    )

            elif chart_type == "line":
                ordered_columns = [
                    *chart_options.datetime_columns,
                    *chart_options.numeric_columns,
                ]
                x_column = st.selectbox(
                    "X-axis column",
                    options=ordered_columns,
                    key=f"new_line_x_{selected_file_id}",
                )
                y_column = st.selectbox(
                    "Y-axis column",
                    options=chart_options.numeric_columns,
                    key=f"new_line_y_{selected_file_id}",
                )

            else:
                x_column = st.selectbox(
                    "X-axis column",
                    options=chart_options.numeric_columns,
                    key=f"new_scatter_x_{selected_file_id}",
                )
                scatter_y_columns = [
                    column
                    for column in chart_options.numeric_columns
                    if column != x_column
                ]
                y_column = st.selectbox(
                    "Y-axis column",
                    options=scatter_y_columns,
                    key=f"new_scatter_y_{selected_file_id}_{x_column}",
                )

            new_configuration = ChartConfiguration(
                chart_type=chart_type,
                title=chart_title.strip() or f"{chart_type.title()} chart",
                x_column=x_column,
                y_column=y_column,
                aggregation=aggregation,
                histogram_bins=(
                    int(histogram_bins)
                    if histogram_bins is not None
                    else None
                ),
            )

            with st.container(horizontal=True):
                add_chart_clicked = st.button(
                    "Preview and add chart",
                    type="primary",
                    icon=":material/add:",
                )
                cancel_clicked = st.button("Cancel")

            if add_chart_clicked:
                try:
                    generate_chart(dataframe, new_configuration)
                    st.session_state["report_charts"].append(new_configuration)
                    st.session_state["report_adding_chart"] = False
                    st.rerun()
                except VisualizationError as error:
                    st.error(str(error))

            if cancel_clicked:
                st.session_state["report_adding_chart"] = False
                st.rerun()

    if len(report_charts) >= MAX_REPORT_CHARTS:
        st.info(f"A report can contain up to {MAX_REPORT_CHARTS} charts.")

    if report_charts:
        if st.button(
            "Save report",
            type="primary",
            icon=":material/save:",
        ):
            try:
                with st.spinner("Generating HTML and PDF reports..."):
                    saved_report = create_report(
                        session=session,
                        file_id=selected_file_id,
                        chart_configurations=report_charts,
                    )
                if commit_session_changes(
                    session,
                    logger,
                    "The reports were generated, but their database records could not be saved.",
                ):
                    st.session_state["saved_report"] = saved_report
                    st.success("HTML and PDF reports were saved successfully.")
            except ReportGenerationError as error:
                if commit_session_changes(
                    session,
                    logger,
                    "The report failure could not be recorded.",
                ):
                    st.error(str(error))
            except (OSError, ValueError):
                logger.exception(
                    "Could not save report for file ID %s.",
                    selected_file_id,
                )
                if commit_session_changes(
                    session,
                    logger,
                    "The report failure could not be recorded.",
                ):
                    st.error("The report could not be saved. Please try again.")
            except Exception:
                logger.exception(
                    "Unexpected report generation failure for file ID %s.",
                    selected_file_id,
                )
                if commit_session_changes(
                    session,
                    logger,
                    "The report failure could not be recorded.",
                ):
                    st.error("An unexpected error occurred while saving the report.")

    saved_report = st.session_state.get("saved_report")
    if (
        saved_report is not None
        and saved_report.source_file_id == selected_file_id
    ):
        st.subheader("Last saved report")
        with st.container(horizontal=True):
            st.download_button(
                "Download HTML",
                data=read_managed_file_bytes(saved_report.html_report_path),
                file_name=saved_report.html_report_filename,
                mime="text/html",
                icon=":material/download:",
                key=f"download_html_report_{saved_report.html_report_id}",
                on_click="ignore",
            )
            st.download_button(
                "Download PDF",
                data=read_managed_file_bytes(saved_report.pdf_report_path),
                file_name=saved_report.pdf_report_filename,
                mime="application/pdf",
                icon=":material/download:",
                key=f"download_pdf_report_{saved_report.pdf_report_id}",
                on_click="ignore",
            )
