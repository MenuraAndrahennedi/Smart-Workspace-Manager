from dataclasses import dataclass
from typing import Tuple

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy.orm import Session

from backend.config.settings import MAX_BAR_CATEGORIES, MAX_CHART_ROWS
from backend.database.repositories import read_file_by_id
from backend.services.analysis_service import load_csv_with_limits
from backend.utils.constants import VALID_AGGREGATIONS

@dataclass(frozen=True)
class ChartSelectionOptions:
    numeric_columns: list[str]
    categorical_columns: list[str]
    datetime_columns: list[str]
    available_chart_types: list[str]

@dataclass(frozen=True)
class ChartConfiguration:
    chart_type: str
    title: str

    x_column: str | None = None
    y_column: str | None = None

    aggregation: str | None = None
    histogram_bins: int | None = None

@dataclass
class GeneratedChart:
    configuration: ChartConfiguration
    figure: go.Figure
    plotted_row_count: int

class VisualizationError(Exception):
    pass

# Helpers
def _validate_column_exists(
    dataframe: pd.DataFrame,
    column: str | None,
    column_label: str,
) -> str:
    if column is None or not column.strip():
        raise VisualizationError(f"Select a column for the {column_label}.")

    if column not in dataframe.columns:
        raise VisualizationError(
            f"The {column_label} column '{column}' does not exist."
        )

    return column


def _validate_numeric_column(
    dataframe: pd.DataFrame,
    column: str,
) -> None:
    if column not in dataframe.columns:
        raise VisualizationError(f"Column '{column}' does not exist.")

    if not pd.api.types.is_numeric_dtype(dataframe[column]):
        raise VisualizationError(f"Column '{column}' must be numeric.")


def _validate_ordered_column(
    dataframe: pd.DataFrame,
    column: str,
) -> None:
    if column not in dataframe.columns:
        raise VisualizationError(f"Column '{column}' does not exist.")

    column_data = dataframe[column]
    if not (
        pd.api.types.is_numeric_dtype(column_data)
        or pd.api.types.is_datetime64_any_dtype(column_data)
    ):
        raise VisualizationError(
            f"Column '{column}' must be numeric or datetime."
        )


def _validate_chart_data(
    chart_data: pd.DataFrame,
    maximum_rows: int,
    limit_name: str = "usable rows",
) -> None:
    if chart_data.empty:
        raise VisualizationError("The selected columns have no usable chart data.")

    if len(chart_data) > maximum_rows:
        raise VisualizationError(
            f"This chart contains more than {maximum_rows} {limit_name}."
        )


# Get avaiable charts and columns for selected CSV
def get_chart_selection_options(
    dataframe: pd.DataFrame,
) -> ChartSelectionOptions:
    if not dataframe.shape[1]:
        raise VisualizationError("Selected CSV file do not have columns to get charts")

    numerical_cols = dataframe.select_dtypes(include="number").columns.tolist()
    datetime_cols = [
        column
        for column in dataframe.columns
        if pd.api.types.is_datetime64_any_dtype(dataframe[column])
    ]
    categorical_cols = [
        column
        for column in dataframe.columns
        if column not in numerical_cols and column not in datetime_cols
    ]

    available_chart_types: list[str] = []

    if numerical_cols:
        available_chart_types.append("histogram")
        if len(numerical_cols) >= 2:
            available_chart_types.append("scatter")
        if datetime_cols or len(numerical_cols) >= 2:
            available_chart_types.append("line")

    if categorical_cols:
        available_chart_types.append("bar")

    return ChartSelectionOptions(
        numeric_columns = numerical_cols,
        categorical_columns = categorical_cols,
        datetime_columns = datetime_cols,
        available_chart_types = available_chart_types,
    )


# Generate Charts
def _create_histogram(
    dataframe: pd.DataFrame,
    configuration: ChartConfiguration,
) -> Tuple[go.Figure, int]:
    x_column = _validate_column_exists(
        dataframe,
        configuration.x_column,
        "X-axis",
    )
    _validate_numeric_column(dataframe, x_column)

    chart_data = dataframe[[x_column]].dropna()
    _validate_chart_data(chart_data, MAX_CHART_ROWS)

    if configuration.histogram_bins is not None and configuration.histogram_bins < 1:
        raise VisualizationError("Histogram bins must be at least 1.")

    figure = px.histogram(
        chart_data,
        x=x_column,
        nbins=configuration.histogram_bins or 20,
        title=configuration.title,
    )

    return figure, chart_data.shape[0]

def _create_bar_chart(
    dataframe: pd.DataFrame,
    configuration: ChartConfiguration,
) -> Tuple[go.Figure, int]:
    x_column = _validate_column_exists(
        dataframe,
        configuration.x_column,
        "X-axis",
    )

    if configuration.y_column is None:
        chart_data = (
            dataframe[configuration.x_column]
            .fillna("Missing")
            .value_counts()
            .rename_axis(configuration.x_column)
            .reset_index(name="count")
        )
        _validate_chart_data(
            chart_data,
            MAX_BAR_CATEGORIES,
            "categories",
        )

        figure = px.bar(
            chart_data,
            x=configuration.x_column,
            y="count",
            title=configuration.title,
        )
    else:
        if configuration.aggregation not in VALID_AGGREGATIONS:
            raise VisualizationError(f"Unsupported aggregation: {configuration.aggregation}")

        y_column = _validate_column_exists(
            dataframe,
            configuration.y_column,
            "Y-axis",
        )

        _validate_numeric_column(dataframe, y_column)

        pandas_aggregation = VALID_AGGREGATIONS[
            configuration.aggregation
        ]

        chart_data = (
            dataframe[[x_column, y_column]]
            .dropna()
            .groupby(x_column, as_index=False)[y_column]
            .agg(pandas_aggregation)
        )
        _validate_chart_data(
            chart_data,
            MAX_BAR_CATEGORIES,
            "categories",
        )

        figure = px.bar(
            chart_data,
            x=x_column,
            y=y_column,
            title=configuration.title,
        )


    return figure, chart_data.shape[0]


def _create_line_chart(
    dataframe: pd.DataFrame,
    configuration: ChartConfiguration,
) -> Tuple[go.Figure, int]:
    x_column = _validate_column_exists(
        dataframe,
        configuration.x_column,
        "X-axis",
    )
    _validate_ordered_column(dataframe, x_column)

    y_column = _validate_column_exists(
        dataframe,
        configuration.y_column,
        "Y-axis",
    )
    _validate_numeric_column(dataframe, y_column)

    chart_data = (
        dataframe[[x_column, y_column]]
        .dropna()
        .sort_values(by=x_column)
    )

    _validate_chart_data(chart_data, MAX_CHART_ROWS)

    figure = px.line(
        chart_data,
        x=x_column,
        y=y_column,
        title=configuration.title,
        markers=True,
    )

    return figure, chart_data.shape[0]

def _create_scatter_chart(
    dataframe: pd.DataFrame,
    configuration: ChartConfiguration,
) -> Tuple[go.Figure, int]:
    x_column = _validate_column_exists(
        dataframe,
        configuration.x_column,
        "X-axis",
    )
    _validate_numeric_column(dataframe, x_column)

    y_column = _validate_column_exists(
        dataframe,
        configuration.y_column,
        "Y-axis",
    )
    _validate_numeric_column(dataframe, y_column)

    if x_column != y_column:
        chart_data = dataframe[
            [configuration.x_column, configuration.y_column]
        ].dropna()

        _validate_chart_data(chart_data, MAX_CHART_ROWS)

        figure = px.scatter(
            chart_data,
            x=configuration.x_column,
            y=configuration.y_column,
            title=configuration.title,
        )
    else:
        raise VisualizationError(f"Cannot scatter plot the similar {x_column} and {y_column}")

    return figure, chart_data.shape[0]



def generate_chart(
    dataframe: pd.DataFrame,
    configuration: ChartConfiguration,
) -> GeneratedChart:
    if not configuration:
        raise VisualizationError("Invalid chart configuration")

    chart_type = configuration.chart_type.lower()

    if chart_type == "histogram":
        figure, row_count = _create_histogram(dataframe, configuration)

    elif chart_type == "bar":
        figure, row_count = _create_bar_chart(dataframe, configuration)

    elif chart_type == "line":
        figure, row_count = _create_line_chart(dataframe, configuration)

    elif chart_type == "scatter":
        figure, row_count = _create_scatter_chart(dataframe, configuration)

    else:
        raise VisualizationError(f"Unsupported chart type: {configuration.chart_type}")

    return GeneratedChart(
        configuration = configuration,
        figure = figure,
        plotted_row_count = row_count,
    )

def generate_chart_for_file(
    session: Session,
    file_id: int,
    configuration: ChartConfiguration,
) -> GeneratedChart:
    file_record = read_file_by_id(session, file_id)

    if file_record is None:
        raise VisualizationError("The selected file does not exist.")
    
    if file_record.status.lower() != "organized":
        raise VisualizationError("Selected CSV file is not organized yet.")
        
    df = load_csv_with_limits(file_record.storage_path)

    result: GeneratedChart = generate_chart(df, configuration)

    return result
