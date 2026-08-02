import pandas as pd
import pytest
import plotly.graph_objects as go

from backend.database.repositories import create_file
from backend.services import analysis_service, visualization_service
from backend.services.visualization_service import (
    ChartConfiguration,
    GeneratedChart,
    VisualizationError,
    _validate_column_exists,
    _validate_numeric_column,
    _validate_ordered_column,
    generate_chart,
    generate_chart_for_file,
    get_chart_selection_options,
)


def test_validate_column_exists_returns_existing_column():
    dataframe = pd.DataFrame({"sales": [10, 20]})

    result = _validate_column_exists(dataframe, "sales", "X-axis")

    assert result == "sales"


@pytest.mark.parametrize("column", [None, "", "   "])
def test_validate_column_exists_rejects_missing_selection(column):
    dataframe = pd.DataFrame({"sales": [10, 20]})

    with pytest.raises(VisualizationError, match="Select a column"):
        _validate_column_exists(dataframe, column, "X-axis")


def test_validate_column_exists_rejects_unknown_column():
    dataframe = pd.DataFrame({"sales": [10, 20]})

    with pytest.raises(VisualizationError, match="does not exist"):
        _validate_column_exists(dataframe, "profit", "Y-axis")


def test_validate_numeric_column_accepts_numeric_column():
    dataframe = pd.DataFrame({"sales": [10, 20]})

    _validate_numeric_column(dataframe, "sales")


def test_validate_numeric_column_rejects_text_column():
    dataframe = pd.DataFrame({"region": ["North", "South"]})

    with pytest.raises(VisualizationError, match="must be numeric"):
        _validate_numeric_column(dataframe, "region")


def test_validate_numeric_column_rejects_unknown_column():
    dataframe = pd.DataFrame({"sales": [10, 20]})

    with pytest.raises(VisualizationError, match="does not exist"):
        _validate_numeric_column(dataframe, "profit")


@pytest.mark.parametrize(
    ("column", "values"),
    [
        ("sequence", [1, 2]),
        ("recorded_at", pd.to_datetime(["2026-07-31", "2026-08-01"])),
    ],
)
def test_validate_ordered_column_accepts_numeric_and_datetime_columns(
    column,
    values,
):
    dataframe = pd.DataFrame({column: values})

    _validate_ordered_column(dataframe, column)


def test_validate_ordered_column_rejects_text_column():
    dataframe = pd.DataFrame({"month": ["July", "August"]})

    with pytest.raises(VisualizationError, match="numeric or datetime"):
        _validate_ordered_column(dataframe, "month")


def test_validate_ordered_column_rejects_unknown_column():
    dataframe = pd.DataFrame({"sequence": [1, 2]})

    with pytest.raises(VisualizationError, match="does not exist"):
        _validate_ordered_column(dataframe, "recorded_at")


def test_get_chart_selection_options_matches_supported_column_types():
    dataframe = pd.DataFrame(
        {
            "sequence": [1, 2],
            "sales": [10.0, 20.0],
            "recorded_at": pd.to_datetime(["2026-07-31", "2026-08-01"]),
            "date_text": ["2026-07-31", "2026-08-01"],
            "region": ["North", "South"],
        }
    )

    result = get_chart_selection_options(dataframe)

    assert result.numeric_columns == ["sequence", "sales"]
    assert result.datetime_columns == ["recorded_at"]
    assert result.categorical_columns == ["date_text", "region"]
    assert result.available_chart_types == [
        "histogram",
        "scatter",
        "line",
        "bar",
    ]


def test_get_chart_selection_options_rejects_dataframe_without_columns():
    with pytest.raises(VisualizationError, match="does not contain any chartable columns"):
        get_chart_selection_options(pd.DataFrame())


@pytest.mark.parametrize(
    ("configuration", "expected_trace_type", "expected_rows"),
    [
        (
            ChartConfiguration(
                chart_type="histogram",
                title="Sales distribution",
                x_column="sales",
                histogram_bins=5,
            ),
            "histogram",
            3,
        ),
        (
            ChartConfiguration(
                chart_type="bar",
                title="Regional counts",
                x_column="region",
            ),
            "bar",
            2,
        ),
        (
            ChartConfiguration(
                chart_type="bar",
                title="Mean regional sales",
                x_column="region",
                y_column="sales",
                aggregation="Mean",
            ),
            "bar",
            2,
        ),
        (
            ChartConfiguration(
                chart_type="line",
                title="Sales over time",
                x_column="recorded_at",
                y_column="sales",
            ),
            "scatter",
            3,
        ),
        (
            ChartConfiguration(
                chart_type="scatter",
                title="Sales and profit",
                x_column="sales",
                y_column="profit",
            ),
            "scatter",
            3,
        ),
    ],
)
def test_generate_chart_creates_supported_chart_types(
    configuration,
    expected_trace_type,
    expected_rows,
):
    dataframe = pd.DataFrame(
        {
            "region": ["North", "South", "North"],
            "sales": [10.0, 20.0, 30.0],
            "profit": [1.0, 3.0, 5.0],
            "recorded_at": pd.to_datetime(
                ["2026-08-01", "2026-08-02", "2026-08-03"]
            ),
        }
    )

    result = generate_chart(dataframe, configuration)

    assert isinstance(result, GeneratedChart)
    assert isinstance(result.figure, go.Figure)
    assert result.figure.data[0].type == expected_trace_type
    assert result.plotted_row_count == expected_rows


@pytest.mark.parametrize(
    ("aggregation", "expected_values"),
    [
        ("Mean", [15.0, 5.0]),
        ("Sum", [30.0, 5.0]),
        ("Minimum", [10.0, 5.0]),
        ("Maximum", [20.0, 5.0]),
        ("Count", [2, 1]),
    ],
)
def test_bar_chart_supports_every_aggregation(
    aggregation,
    expected_values,
):
    dataframe = pd.DataFrame(
        {
            "region": ["North", "North", "South"],
            "sales": [10.0, 20.0, 5.0],
        }
    )

    result = generate_chart(
        dataframe,
        ChartConfiguration(
            chart_type="bar",
            title=f"{aggregation} sales",
            x_column="region",
            y_column="sales",
            aggregation=aggregation,
        ),
    )

    assert list(result.figure.data[0].y) == expected_values


def test_line_chart_accepts_numeric_x_and_sorts_data():
    dataframe = pd.DataFrame(
        {
            "sequence": [3, 1, 2],
            "sales": [30.0, 10.0, 20.0],
        }
    )

    result = generate_chart(
        dataframe,
        ChartConfiguration(
            chart_type="line",
            title="Ordered sales",
            x_column="sequence",
            y_column="sales",
        ),
    )

    assert list(result.figure.data[0].x) == [1, 2, 3]
    assert list(result.figure.data[0].y) == [10.0, 20.0, 30.0]


def test_scatter_chart_rejects_identical_x_and_y_columns():
    dataframe = pd.DataFrame({"sales": [10.0, 20.0]})

    with pytest.raises(VisualizationError, match="different columns"):
        generate_chart(
            dataframe,
            ChartConfiguration(
                chart_type="scatter",
                title="Invalid scatter",
                x_column="sales",
                y_column="sales",
            ),
        )


def test_chart_generation_does_not_modify_source_dataframe():
    dataframe = pd.DataFrame(
        {
            "region": ["North", "South", "North"],
            "sequence": [3, 1, 2],
            "sales": [30.0, 10.0, 20.0],
            "profit": [3.0, 1.0, 2.0],
        }
    )
    original = dataframe.copy(deep=True)
    configurations = [
        ChartConfiguration("histogram", "Histogram", x_column="sales"),
        ChartConfiguration("bar", "Bar", x_column="region"),
        ChartConfiguration(
            "line",
            "Line",
            x_column="sequence",
            y_column="sales",
        ),
        ChartConfiguration(
            "scatter",
            "Scatter",
            x_column="sales",
            y_column="profit",
        ),
    ]

    for configuration in configurations:
        generate_chart(dataframe, configuration)

    pd.testing.assert_frame_equal(dataframe, original)


def test_generate_chart_rejects_invalid_configurations():
    dataframe = pd.DataFrame(
        {
            "region": ["North", "South"],
            "sales": [10.0, 20.0],
        }
    )

    with pytest.raises(VisualizationError, match="at least 1"):
        generate_chart(
            dataframe,
            ChartConfiguration(
                chart_type="histogram",
                title="Invalid bins",
                x_column="sales",
                histogram_bins=0,
            ),
        )

    with pytest.raises(VisualizationError, match="Unsupported aggregation"):
        generate_chart(
            dataframe,
            ChartConfiguration(
                chart_type="bar",
                title="Invalid aggregation",
                x_column="region",
                y_column="sales",
                aggregation="Median",
            ),
        )

    with pytest.raises(VisualizationError, match="Unsupported chart type"):
        generate_chart(
            dataframe,
            ChartConfiguration(chart_type="pie", title="Unsupported"),
        )


def test_generate_chart_rejects_empty_usable_data():
    dataframe = pd.DataFrame(
        {"sales": pd.Series([float("nan"), float("nan")], dtype="float64")}
    )

    with pytest.raises(VisualizationError, match="no usable chart data"):
        generate_chart(
            dataframe,
            ChartConfiguration(
                chart_type="histogram",
                title="Empty",
                x_column="sales",
            ),
        )


@pytest.mark.parametrize("chart_type", ["histogram", "line", "scatter"])
def test_generate_chart_enforces_raw_row_limit(monkeypatch, chart_type):
    monkeypatch.setattr(visualization_service, "MAX_CHART_ROWS", 2)
    dataframe = pd.DataFrame(
        {
            "sequence": [1, 2, 3],
            "sales": [10.0, 20.0, 30.0],
            "profit": [1.0, 2.0, 3.0],
        }
    )
    configurations = {
        "histogram": ChartConfiguration(
            chart_type="histogram",
            title="Histogram",
            x_column="sales",
        ),
        "line": ChartConfiguration(
            chart_type="line",
            title="Line",
            x_column="sequence",
            y_column="sales",
        ),
        "scatter": ChartConfiguration(
            chart_type="scatter",
            title="Scatter",
            x_column="sales",
            y_column="profit",
        ),
    }

    with pytest.raises(VisualizationError, match="more than 2 usable rows"):
        generate_chart(dataframe, configurations[chart_type])


def test_generate_chart_enforces_bar_category_limit(monkeypatch):
    monkeypatch.setattr(visualization_service, "MAX_BAR_CATEGORIES", 2)
    dataframe = pd.DataFrame({"region": ["North", "South", "West"]})

    with pytest.raises(VisualizationError, match="more than 2 categories"):
        generate_chart(
            dataframe,
            ChartConfiguration(
                chart_type="bar",
                title="Too many categories",
                x_column="region",
            ),
        )


@pytest.fixture
def visualization_csv_file(test_session, temporary_data_root):
    data_root = temporary_data_root
    csv_path = data_root / "visualization.csv"
    csv_path.write_text(
        "region,sales\nNorth,10\nSouth,20\n",
        encoding="utf-8",
    )

    return create_file(
        session=test_session,
        original_name="visualization.csv",
        stored_name="visualization.csv",
        extension="csv",
        category="spreadsheets",
        size_bytes=csv_path.stat().st_size,
        storage_path=str(csv_path),
        status="organized",
    )


def test_generate_chart_for_file_loads_organized_csv(
    test_session,
    visualization_csv_file,
):
    result = generate_chart_for_file(
        session=test_session,
        file_id=visualization_csv_file.id,
        configuration=ChartConfiguration(
            chart_type="bar",
            title="Regional counts",
            x_column="region",
        ),
    )

    assert result.plotted_row_count == 2
    assert result.figure.data[0].type == "bar"


def test_generate_chart_for_file_rejects_missing_record(test_session):
    with pytest.raises(VisualizationError, match="does not exist"):
        generate_chart_for_file(
            session=test_session,
            file_id=999,
            configuration=ChartConfiguration(
                chart_type="bar",
                title="Missing",
                x_column="region",
            ),
        )
