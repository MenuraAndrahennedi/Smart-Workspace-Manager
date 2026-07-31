from datetime import datetime, timezone

import pandas as pd
import pytest

from backend.database.repositories import create_file
from backend.services.cleaning_service import (
    CleaningOptions,
    DataCleaningError,
    DuplicateRemovalResult,
    preview_cleaning,
    save_cleaning_result,
    drop_rows_with_missing_values,
    fill_numeric_missing_values,
    fill_text_missing_values,
    remove_duplicates,
)


@pytest.fixture
def cleaning_data_root(tmp_path, monkeypatch):
    data_root = tmp_path / "data"
    data_root.mkdir()
    monkeypatch.setattr("backend.services.cleaning_service.DATA_ROOT", data_root)
    monkeypatch.setattr("backend.services.analysis_service.DATA_ROOT", data_root)
    return data_root


@pytest.fixture
def organized_csv_file(test_session, cleaning_data_root):
    csv_path = cleaning_data_root / "sample.csv"
    csv_path.write_text(
        "name,age,city\n"
        "Menura,22,Matara\n"
        "Sahas,,\n"
        "Kamal,30,Gampaha\n"
        "Menura,22,Matara\n",
        encoding="utf-8",
    )

    return create_file(
        session=test_session,
        original_name="sample.csv",
        stored_name="sample.csv",
        extension="csv",
        category="spreadsheets",
        size_bytes=csv_path.stat().st_size,
        storage_path=str(csv_path),
        status="organized",
    )


def test_remove_duplicates():
    df = pd.DataFrame(
        {
            "name": ["Menura", "Menura", "Menura"],
            "age": [22, 25, 22],
        }
    )

    cleaned_df = pd.DataFrame(
        {
            "name": ["Menura", "Menura"],
            "age": [22, 25],
        }
    )

    subset_cleaned_df = pd.DataFrame(
        {
            "name": ["Menura"],
            "age": [22],
        }
    )

    subset_valid = ["name"]
    subset_empty = []
    subset_invalid = ["city", "name"]

    with pytest.raises(DataCleaningError, match="cannot be an empty list"):
        remove_duplicates(df, subset_empty)

    with pytest.raises(DataCleaningError, match="can only contain original columns"):
        remove_duplicates(df, subset_invalid)

    no_subset_result: DuplicateRemovalResult = remove_duplicates(df)

    assert no_subset_result.cleaned_dataframe.equals(cleaned_df)
    assert no_subset_result.original_row_count == 3
    assert no_subset_result.cleaned_row_count == 2
    assert no_subset_result.removed_duplicate_count == 1

    subset_result: DuplicateRemovalResult = remove_duplicates(df, subset_valid)
    
    assert subset_result.cleaned_dataframe.equals(subset_cleaned_df)
    assert subset_result.original_row_count == 3
    assert subset_result.cleaned_row_count == 1
    assert subset_result.removed_duplicate_count == 2



def test_drop_rows_with_missing_values():
    df = pd.DataFrame(
        {
            "name": ["Menura", "Sahas", "Kamal"],
            "age": [22, 25, None],
            "city":["Matara", None , "Gampaha"],
        }
    )

    cleaned_df = pd.DataFrame(
        {
            "name": ["Menura"],
            "age": [22.0],
            "city":["Matara"],
        }
    )

    columns_cleaned_df = pd.DataFrame(
        {
            "name": ["Menura", "Sahas"],
            "age": [22.0, 25.0],
            "city":["Matara", None],
        }
    )

    valid_columns = ["name", "age"]
    invalid_columns = ["name", "address"]
    empty_columns = []


    with pytest.raises(DataCleaningError, match="cannot be an empty list"):
        drop_rows_with_missing_values(df, empty_columns)
    
    with pytest.raises(DataCleaningError, match="can only contain original columns"):
        drop_rows_with_missing_values(df, invalid_columns)

    drop_all_results = drop_rows_with_missing_values(df)
    assert drop_all_results.cleaned_dataframe.equals(cleaned_df)
    assert drop_all_results.original_missing_count == 2
    assert drop_all_results.remaining_missing_count == 0
    assert drop_all_results.rows_removed == 2
    assert drop_all_results.values_filled == 0

    drop_columns_results = drop_rows_with_missing_values(df, valid_columns)
    assert drop_columns_results.cleaned_dataframe.equals(columns_cleaned_df)
    assert drop_columns_results.original_missing_count == 2
    assert drop_columns_results.remaining_missing_count == 1
    assert drop_columns_results.rows_removed == 1
    assert drop_columns_results.values_filled == 0



def test_fill_numeric_missing_values():
    df = pd.DataFrame(
        {
            "name": ["Menura", "Sahas", "Kamal"],
            "age": [22, 25, None],
            "city":["Matara", None , "Gampaha"],
        }
    )
    mean = df["age"].mean()
    median = df["age"].median()
    fill_value = 20.0

    mean_filled_df = pd.DataFrame(
        {
            "name": ["Menura", "Sahas", "Kamal"],
            "age": [22.0, 25.0, mean],
            "city":["Matara", None , "Gampaha"],
        }
    )

    median_filled_df = pd.DataFrame(
        {
            "name": ["Menura", "Sahas", "Kamal"],
            "age": [22.0, 25.0, median],
            "city":["Matara", None , "Gampaha"],
        }
    )

    constant_filled_df = pd.DataFrame(
        {
            "name": ["Menura", "Sahas", "Kamal"],
            "age": [22.0, 25.0, fill_value],
            "city":["Matara", None , "Gampaha"],
        }
    )



    valid_column = "age"
    invalid_column = "address"
    text_column = "city"

    # Empty column
    with pytest.raises(DataCleaningError, match="cannot be an empty"):
        fill_numeric_missing_values(df, None, "mean")

    # Invalid Column
    with pytest.raises(DataCleaningError, match="must be an original column"):
        fill_numeric_missing_values(df, invalid_column, "mean")

    # Text Column
    with pytest.raises(DataCleaningError, match="must be numeric"):
        fill_numeric_missing_values(df, text_column, "mean")

    # Constant -> No fill value
    with pytest.raises(DataCleaningError, match="fill value is required"):
        fill_numeric_missing_values(df, valid_column, "constant")

    # Invalid Strategy
    with pytest.raises(DataCleaningError, match="strategy is unsupported"):
        fill_numeric_missing_values(df, valid_column, "10")
        

    fill_mean_results = fill_numeric_missing_values(df, valid_column, "mean")
    assert fill_mean_results.cleaned_dataframe.equals(mean_filled_df)
    assert fill_mean_results.original_missing_count == 2
    assert fill_mean_results.remaining_missing_count == 1
    assert fill_mean_results.rows_removed == 0
    assert fill_mean_results.values_filled == 1

    fill_median_results = fill_numeric_missing_values(df, valid_column, "median")
    assert fill_median_results.cleaned_dataframe.equals(median_filled_df)
    assert fill_median_results.original_missing_count == 2
    assert fill_median_results.remaining_missing_count == 1
    assert fill_median_results.rows_removed == 0
    assert fill_median_results.values_filled == 1

    fill_constant_results = fill_numeric_missing_values(df, valid_column, "constant", fill_value)
    assert fill_constant_results.cleaned_dataframe.equals(constant_filled_df)
    assert fill_constant_results.original_missing_count == 2
    assert fill_constant_results.remaining_missing_count == 1
    assert fill_constant_results.rows_removed == 0
    assert fill_constant_results.values_filled == 1


def test_fill_text_missing_values():
    df = pd.DataFrame(
        {
            "name": ["Menura", "Sahas", "Kamal"],
            "age": [22, 25, None],
            "city": ["Matara", None, "Gampaha"],
        }
    )

    fill_value = "Unknown"

    text_filled_df = pd.DataFrame(
        {
            "name": ["Menura", "Sahas", "Kamal"],
            "age": [22.0, 25.0, None],
            "city": ["Matara", fill_value, "Gampaha"],
        }
    )

    valid_column = "city"
    invalid_column = "address"
    numeric_column = "age"

    # Empty column
    with pytest.raises(DataCleaningError, match="cannot be an empty"):
        fill_text_missing_values(df, None, fill_value)

    # Invalid Column
    with pytest.raises(DataCleaningError, match="must be an original column"):
        fill_text_missing_values(df, invalid_column, fill_value)

    # Numeric Column
    with pytest.raises(DataCleaningError, match="text column"):
        fill_text_missing_values(df, numeric_column, fill_value)

    # Empty fill value
    with pytest.raises(DataCleaningError, match="Fill value cannot be empty"):
        fill_text_missing_values(df, valid_column, "")

    fill_text_results = fill_text_missing_values(df, valid_column, fill_value)
    assert fill_text_results.cleaned_dataframe.equals(text_filled_df)
    assert fill_text_results.original_missing_count == 2
    assert fill_text_results.remaining_missing_count == 1
    assert fill_text_results.rows_removed == 0
    assert fill_text_results.values_filled == 1


def test_preview_cleaning_applies_selected_actions(test_session, organized_csv_file):
    options = CleaningOptions(
        remove_duplicates=True,
        numeric_fill_column="age",
        numeric_fill_strategy="mean",
        text_fill_column="city",
        text_fill_value="Unknown",
    )

    result = preview_cleaning(
        session=test_session,
        file_id=organized_csv_file.id,
        cleaning_options=options,
    )

    expected_df = pd.DataFrame(
        {
            "name": ["Menura", "Sahas", "Kamal"],
            "age": [22.0, 26.0, 30.0],
            "city": ["Matara", "Unknown", "Gampaha"],
        }
    )

    assert result.cleaned_dataframe.equals(expected_df)
    assert result.original_row_count == 4
    assert result.cleaned_row_count == 3
    assert result.duplicates_removed == 1
    assert result.missing_values_filled == 2
    assert result.rows_dropped == 0
    assert result.remaining_missing_values == 0


def test_save_cleaning_result_creates_csv_and_excel_files(
    test_session,
    organized_csv_file,
):
    cleaned_df = pd.DataFrame(
        {
            "name": ["Menura", "Sahas"],
            "age": [22.0, 26.0],
            "city": ["Matara", "Unknown"],
        }
    )

    result = save_cleaning_result(
        session=test_session,
        file_id=organized_csv_file.id,
        cleaned_dataframe=cleaned_df,
        date_value=datetime(2026, 7, 31, tzinfo=timezone.utc),
    )

    assert result.csv_path.is_file()
    assert result.excel_path.is_file()
    assert result.csv_path.suffix == ".csv"
    assert result.excel_path.suffix == ".xlsx"
    assert result.csv_path.parent.name == "07"
    assert result.excel_path.parent.name == "07"
    assert result.row_count == 2
    assert result.column_count == 3

    saved_csv = pd.read_csv(result.csv_path, encoding="utf-8-sig")
    assert saved_csv.equals(cleaned_df)
