import pandas as pd
import pytest

from backend.config.settings import MAX_CSV_ANALYSIS_SIZE_MB
from backend.services.analysis_service import CSVAnalysisResult, CSVAnalysisError, CSVLimitError, analyze_csv, analyze_dataframe, load_csv_with_limits


@pytest.fixture
def analysis_data_root(tmp_path, monkeypatch):
    data_root = tmp_path / "data"
    data_root.mkdir()
    monkeypatch.setattr("backend.services.analysis_service.DATA_ROOT", data_root)
    return data_root

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
    with pytest.raises(ValueError, match="escape the storage directory"):
        analyze_csv(csv_path_1)

    csv_path = analysis_data_root
    with pytest.raises(ValueError, match="not point to a file"):
        analyze_csv(csv_path)

    pdf_path = analysis_data_root / "file.pdf"
    pdf_path.write_text("name,age\nAlice,22\n", encoding="utf-8")
    with pytest.raises(ValueError, match="not point to a CSV file"):
        analyze_csv(pdf_path)

    csv_path = analysis_data_root / "file.csv"
    csv_path.write_text("name,age\nAlice,22\n", encoding="utf-8")
    size = (MAX_CSV_ANALYSIS_SIZE_MB  * (1024**2)) + 1
    csv_path.write_bytes(b"x" * size)
    with pytest.raises(CSVLimitError, match="exceeds the analysable file size limit"):
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
from backend.services import analysis_service


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
