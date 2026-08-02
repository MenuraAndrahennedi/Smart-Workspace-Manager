import json

import pandas as pd
import pytest
from sqlalchemy import select

from backend.config.settings import MAX_CSV_ANALYSIS_SIZE_MB
from backend.database.models import AnalysisJob
from backend.database.repositories import create_file
from backend.services import analysis_service
from backend.services.analysis_service import (
    CSVAnalysisError,
    CSVAnalysisResult,
    CSVLimitError,
    analyze_csv,
    analyze_dataframe,
    analyze_file_and_record_job,
    filter_csv_data,
    get_analyzable_csv_files,
    load_csv_with_limits,
)


@pytest.fixture
def analysis_data_root(temporary_data_root):
    return temporary_data_root


@pytest.fixture
def organized_analysis_csv(test_session, analysis_data_root):
    csv_path = analysis_data_root / "organized.csv"
    csv_path.write_text(
        "name,age,city\n"
        "Alice,22,Colombo\n"
        "Bob,30,Kandy\n"
        "Alicia,25,Galle\n",
        encoding="utf-8",
    )

    return create_file(
        session=test_session,
        original_name="organized.csv",
        stored_name="organized.csv",
        extension="csv",
        category="spreadsheets",
        size_bytes=csv_path.stat().st_size,
        storage_path=str(csv_path),
        status="organized",
    )

# Test analyze_csv (load_csv_with_limits) - Invalid data
def test_analyze_csv_invalid_encoding(analysis_data_root):
    csv_path = analysis_data_root / "non-unicode.csv"
    csv_path.write_bytes(b"name,city\nMenura,\xff\xfe")

    with pytest.raises(CSVAnalysisError, match="not encoded as UTF-8"):
        analyze_csv(csv_path)

def test_analyze_csv_malformed_csv(analysis_data_root):
    csv_path = analysis_data_root / "malformed.csv"
    csv_path.write_text(
        'name,age\n'
        '"Alice,22\n'
        'Bob,25\n',
        encoding="utf-8",
    )

    with pytest.raises(CSVAnalysisError, match="invalid | malformed"):
        analyze_csv(csv_path)

def test_analyze_csv_empty_file(analysis_data_root):
    csv_path = analysis_data_root / "empty.csv"
    csv_path.touch() 

    with pytest.raises(CSVAnalysisError, match="empty"):
        analyze_csv(csv_path)

def test_analyze_csv_path_failures(tmp_path, analysis_data_root):
    csv_path = analysis_data_root / "missing.csv"
    with pytest.raises(FileNotFoundError, match="not exist"):
        analyze_csv(csv_path)

    csv_path_1 = tmp_path / "file.csv"
    csv_path_1.write_text("name,age\nAlice,22\n", encoding="utf-8")
    with pytest.raises(ValueError, match="not related to data root"):
        analyze_csv(csv_path_1)

    csv_path = analysis_data_root
    with pytest.raises(ValueError, match="not a file"):
        analyze_csv(csv_path)

    pdf_path = analysis_data_root / "file.pdf"
    pdf_path.write_text("name,age\nAlice,22\n", encoding="utf-8")
    with pytest.raises(ValueError, match="not point to a CSV file"):
        analyze_csv(pdf_path)

    csv_path = analysis_data_root / "file.csv"
    csv_path.write_text("name,age\nAlice,22\n", encoding="utf-8")
    size = (MAX_CSV_ANALYSIS_SIZE_MB  * (1024**2)) + 1
    csv_path.write_bytes(b"x" * size)
    with pytest.raises(CSVLimitError, match="10 MB analysis limit"):
        analyze_csv(csv_path)



# Test load_csv_with_limits - Valid data
def test_load_csv_with_limits_valid_csv(analysis_data_root):
    csv_path = analysis_data_root / "valid.csv"
    csv_path.write_text(
        "name,age,city\n"
        "Menura,22,Colombo\n"
        "Alice,25,Kandy\n",
        encoding="utf-8",
    )

    result_df = load_csv_with_limits(csv_path)

    assert result_df.shape == (2,3)
    assert result_df.columns.tolist() == ["name", "age", "city"]
    assert result_df.iloc[0]["name"] == "Menura"


def test_load_csv_with_limits_supports_utf8_bom(analysis_data_root):
    csv_path = analysis_data_root / "bom.csv"
    csv_path.write_bytes(
        b"\xef\xbb\xbfname,age\nMenura,22\n"
    )

    result = load_csv_with_limits(csv_path)

    assert result.columns.tolist() == ["name", "age"]
    assert result.to_dict("records") == [{"name": "Menura", "age": 22}]


def test_analyze_csv_rejects_header_only_csv(analysis_data_root):
    csv_path = analysis_data_root / "header-only.csv"
    csv_path.write_text("name,age\n", encoding="utf-8")

    with pytest.raises(CSVAnalysisError, match="no data rows"):
        analyze_csv(csv_path)


def test_load_csv_with_limits_enforces_row_limit(
    analysis_data_root,
    monkeypatch,
):
    csv_path = analysis_data_root / "too-many-rows.csv"
    csv_path.write_text("name\nA\nB\nC\n", encoding="utf-8")
    monkeypatch.setattr(analysis_service, "MAX_CSV_ROWS", 2)

    with pytest.raises(CSVLimitError, match="2-row analysis limit"):
        load_csv_with_limits(csv_path)


def test_load_csv_with_limits_enforces_column_limit(
    analysis_data_root,
    monkeypatch,
):
    csv_path = analysis_data_root / "too-many-columns.csv"
    csv_path.write_text("first,second,third\n1,2,3\n", encoding="utf-8")
    monkeypatch.setattr(analysis_service, "MAX_CSV_COLUMNS", 2)

    with pytest.raises(CSVLimitError, match="2-column analysis limit"):
        load_csv_with_limits(csv_path)


def test_analyze_csv_does_not_modify_source_file(analysis_data_root):
    csv_path = analysis_data_root / "unchanged.csv"
    csv_path.write_bytes(b"name,age\nAlice,22\nBob,25\n")
    original_bytes = csv_path.read_bytes()

    analyze_csv(csv_path)

    assert csv_path.read_bytes() == original_bytes


# Test analyze_dataframe - Valid data
def test_analyze_dataframe_valid():
    valid_df = pd.DataFrame(
        {
            "name": ["Alice", "Bob", "Charlie", "Alice"],
            "age": [22, 25, None, 22],
            "city": ["Colombo", "Kandy", "Galle", "Colombo"],
        }
    )

    result = analyze_dataframe(valid_df)

    assert isinstance(result, CSVAnalysisResult)

    assert result.row_count == 4
    assert result.column_count == 3

    assert result.columns == ["name", "age", "city"]

    assert result.missing_values == {
        "name": 0,
        "age": 1,
        "city": 0,
    }

    assert result.duplicate_count == 1

    assert isinstance(result.preview, pd.DataFrame)
    assert isinstance(result.descriptive_statistics, pd.DataFrame)

# Test analyze_dataframe - invalid data
def test_analyze_dataframe_invalid_preview_rows():
    invalid_df = pd.DataFrame(
        {
            "name": [],
            "age": [],
            "city": [],
        }
    )

    with pytest.raises(CSVAnalysisError, match = "no data rows"):
        analyze_dataframe(invalid_df)

def test_analyze_dataframe_no_rows():
    valid_df = pd.DataFrame(
        {
            "name": ["Alice", "Bob", "Charlie", "Alice"],
            "age": [22, 25, None, 22],
            "city": ["Colombo", "Kandy", "Galle", "Colombo"],
        }
    )

    with pytest.raises(ValueError, match = "greater than zero"):
        analyze_dataframe(valid_df, -1)



# Test analyze_csv - valid data
def test_analyze_csv_valid(
    analysis_data_root,
):
    csv_path = analysis_data_root / "valid.csv"

    csv_path.write_text(
        "name,age,city\n"
        "Alice,22,Colombo\n"
        "Bob,25,Kandy\n"
        "Charlie,,Galle\n"
        "Alice,22,Colombo\n",
        encoding="utf-8",
    )

    result = analysis_service.analyze_csv(csv_path)

    assert result.row_count == 4
    assert result.column_count == 3
    assert result.missing_values["age"] == 1
    assert result.duplicate_count == 1

    statistics = result.descriptive_statistics

    assert statistics.index.tolist() == ["name", "age", "city"]

    assert statistics.loc["age", "count"] == 3
    assert statistics.loc["age", "mean"] == pytest.approx(23.0)
    assert statistics.loc["age", "min"] == pytest.approx(22.0)
    assert statistics.loc["age", "max"] == pytest.approx(25.0)

    assert statistics.loc["name", "unique"] == 3
    assert statistics.loc["name", "top"] == "Alice"
    assert statistics.loc["name", "freq"] == 2


def test_get_analyzable_csv_files_returns_only_organized_csv_files(
    test_session,
    analysis_data_root,
    organized_analysis_csv,
):
    uploaded_path = analysis_data_root / "uploaded.csv"
    uploaded_path.write_text("name\nAlice\n", encoding="utf-8")
    create_file(
        session=test_session,
        original_name="uploaded.csv",
        stored_name="uploaded.csv",
        extension="csv",
        category="spreadsheets",
        size_bytes=uploaded_path.stat().st_size,
        storage_path=str(uploaded_path),
        status="uploaded",
    )

    workbook_path = analysis_data_root / "organized.xlsx"
    workbook_path.write_bytes(b"not a real workbook")
    create_file(
        session=test_session,
        original_name="organized.xlsx",
        stored_name="organized.xlsx",
        extension="xlsx",
        category="spreadsheets",
        size_bytes=workbook_path.stat().st_size,
        storage_path=str(workbook_path),
        status="organized",
    )

    result = get_analyzable_csv_files(test_session)

    assert [file_record.id for file_record in result] == [
        organized_analysis_csv.id
    ]


def test_analyze_file_and_record_job_marks_job_completed(
    test_session,
    organized_analysis_csv,
):
    recorded = analyze_file_and_record_job(
        session=test_session,
        file_id=organized_analysis_csv.id,
        preview_rows=2,
    )

    job = test_session.get(AnalysisJob, recorded.job_id)

    assert job is not None
    assert job.status == "completed"
    assert job.completed_at is not None
    assert job.error_message is None
    assert json.loads(job.requested_options) == {"preview_rows": 2}

    summary = json.loads(job.summary)
    assert summary["row_count"] == 3
    assert summary["column_count"] == 3
    assert summary["duplicate_count"] == 0
    assert recorded.result.preview.shape == (2, 3)


def test_analyze_file_and_record_job_marks_job_failed(
    test_session,
    organized_analysis_csv,
    monkeypatch,
):
    def fail_analysis(*args, **kwargs):
        raise CSVAnalysisError("Invalid CSV")

    monkeypatch.setattr(analysis_service, "analyze_csv", fail_analysis)

    with pytest.raises(CSVAnalysisError, match="Invalid CSV"):
        analyze_file_and_record_job(
            session=test_session,
            file_id=organized_analysis_csv.id,
        )

    job = test_session.scalars(
        select(AnalysisJob).order_by(AnalysisJob.id.desc())
    ).first()

    assert job is not None
    assert job.status == "failed"
    assert job.summary is None
    assert job.error_message == "Invalid CSV"
    assert job.completed_at is not None


def test_filter_csv_data_supports_numeric_and_text_filters(
    test_session,
    organized_analysis_csv,
):
    numeric_result = filter_csv_data(
        session=test_session,
        file_id=organized_analysis_csv.id,
        selected_columns=["name", "age"],
        filter_column="age",
        operator="Greater than",
        filter_value="23",
    )

    text_result = filter_csv_data(
        session=test_session,
        file_id=organized_analysis_csv.id,
        selected_columns=["name", "city"],
        filter_column="name",
        operator="Contains",
        filter_value="ali",
    )

    assert numeric_result.to_dict("records") == [
        {"name": "Bob", "age": 30},
        {"name": "Alicia", "age": 25},
    ]
    assert text_result.to_dict("records") == [
        {"name": "Alice", "city": "Colombo"},
        {"name": "Alicia", "city": "Galle"},
    ]


def test_filter_csv_data_rejects_invalid_configuration(
    test_session,
    organized_analysis_csv,
):
    with pytest.raises(CSVAnalysisError, match="at least one column"):
        filter_csv_data(
            session=test_session,
            file_id=organized_analysis_csv.id,
            selected_columns=[],
        )

    with pytest.raises(CSVAnalysisError, match="valid numeric"):
        filter_csv_data(
            session=test_session,
            file_id=organized_analysis_csv.id,
            selected_columns=["age"],
            filter_column="age",
            operator="Equals",
            filter_value="not-a-number",
        )
