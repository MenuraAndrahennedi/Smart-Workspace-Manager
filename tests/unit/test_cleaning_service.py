from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

from backend.database.repositories import create_file, read_file_by_id
from backend.services.analysis_service import get_analyzable_csv_files
from backend.services.cleaning_service import (
    CleaningOptions,
    DataCleaningError,
    DuplicateRemovalResult,
    discard_cleaning_result,
    get_cleaning_column_options,
    load_cleaning_source,
    preview_cleaning,
    save_cleaning_result,
    drop_rows_with_missing_values,
    fill_numeric_missing_values,
    fill_text_missing_values,
    remove_duplicates,
)
from backend.services.xlsx_to_csv_service import get_convertible_xlsx_files


@pytest.fixture
def cleaning_data_root(temporary_data_root):
    return temporary_data_root


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

    with pytest.raises(DataCleaningError, match="at least one duplicate-check column"):
        remove_duplicates(df, subset_empty)

    with pytest.raises(DataCleaningError, match="columns from the original CSV"):
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


def test_load_cleaning_source_and_detect_column_options(
    test_session,
    organized_csv_file,
):
    dataframe = load_cleaning_source(test_session, organized_csv_file.id)
    options = get_cleaning_column_options(dataframe)

    assert dataframe.shape == (4, 3)
    assert options.numeric_columns == ["age"]
    assert options.text_columns == ["name", "city"]



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


    with pytest.raises(DataCleaningError, match="at least one column"):
        drop_rows_with_missing_values(df, empty_columns)
    
    with pytest.raises(DataCleaningError, match="columns from the original CSV"):
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
    with pytest.raises(DataCleaningError, match="Select a numeric column"):
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
    with pytest.raises(DataCleaningError, match="strategy is not supported"):
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


@pytest.mark.parametrize("strategy", ["mean", "median"])
def test_fill_numeric_missing_values_rejects_all_missing_column(strategy):
    dataframe = pd.DataFrame(
        {"age": pd.Series([None, None], dtype="float64")}
    )

    with pytest.raises(DataCleaningError, match="no usable numeric values"):
        fill_numeric_missing_values(dataframe, "age", strategy)


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
    with pytest.raises(DataCleaningError, match="Select a text column"):
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


def test_each_cleaning_preview_reloads_the_original_csv(
    test_session,
    organized_csv_file,
):
    source_path = Path(organized_csv_file.storage_path)
    original_bytes = source_path.read_bytes()

    first_preview = preview_cleaning(
        session=test_session,
        file_id=organized_csv_file.id,
        cleaning_options=CleaningOptions(remove_duplicates=True),
    )
    first_preview.cleaned_dataframe.loc[0, "name"] = "Changed in memory"

    second_preview = preview_cleaning(
        session=test_session,
        file_id=organized_csv_file.id,
        cleaning_options=CleaningOptions(),
    )

    assert second_preview.cleaned_dataframe.iloc[0]["name"] == "Menura"
    assert second_preview.cleaned_row_count == 4
    assert source_path.read_bytes() == original_bytes


def test_save_cleaning_result_creates_csv_and_excel_files(
    test_session,
    organized_csv_file,
):
    source_path = Path(organized_csv_file.storage_path)
    original_bytes = source_path.read_bytes()
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

    csv_record = read_file_by_id(test_session, result.csv_file_id)
    excel_record = read_file_by_id(test_session, result.excel_file_id)
    assert csv_record.storage_path == str(result.csv_path)
    assert csv_record.extension == "csv"
    assert csv_record.status == "organized"
    assert excel_record.storage_path == str(result.excel_path)
    assert excel_record.extension == "xlsx"
    assert excel_record.status == "organized"

    analyzable_ids = {
        file_record.id
        for file_record in get_analyzable_csv_files(test_session)
    }
    convertible_ids = {
        file_record.id
        for file_record in get_convertible_xlsx_files(test_session)
    }
    assert result.csv_file_id in analyzable_ids
    assert result.excel_file_id in convertible_ids

    saved_csv = pd.read_csv(result.csv_path, encoding="utf-8-sig")
    assert saved_csv.equals(cleaned_df)
    assert source_path.read_bytes() == original_bytes


def test_save_cleaning_result_removes_partial_outputs_after_failure(
    test_session,
    organized_csv_file,
    cleaning_data_root,
    monkeypatch,
):
    cleaned_df = pd.DataFrame({"name": ["Menura"], "age": [22]})

    def fail_excel_export(self, *args, **kwargs):
        raise OSError("Excel export failed")

    monkeypatch.setattr(pd.DataFrame, "to_excel", fail_excel_export)

    with pytest.raises(OSError, match="Excel export failed"):
        save_cleaning_result(
            session=test_session,
            file_id=organized_csv_file.id,
            cleaned_dataframe=cleaned_df,
            date_value=datetime(2026, 8, 1, tzinfo=timezone.utc),
        )

    cleaned_root = cleaning_data_root / "processed" / "cleaned"
    assert list(cleaned_root.rglob("*.csv")) == []
    assert list(cleaned_root.rglob("*.xlsx")) == []


def test_save_cleaning_result_removes_outputs_after_database_failure(
    test_session,
    organized_csv_file,
    cleaning_data_root,
    monkeypatch,
):
    real_create_file = create_file
    create_calls = 0

    def fail_second_create(**kwargs):
        nonlocal create_calls
        create_calls += 1
        if create_calls == 2:
            raise RuntimeError("database failure")
        return real_create_file(**kwargs)

    monkeypatch.setattr(
        "backend.services.cleaning_service.create_file",
        fail_second_create,
    )

    with pytest.raises(RuntimeError, match="database failure"):
        save_cleaning_result(
            session=test_session,
            file_id=organized_csv_file.id,
            cleaned_dataframe=pd.DataFrame({"name": ["Menura"]}),
        )

    cleaned_root = cleaning_data_root / "processed" / "cleaned"
    assert list(cleaned_root.rglob("*.csv")) == []
    assert list(cleaned_root.rglob("*.xlsx")) == []


def test_discard_cleaning_result_removes_both_exports(
    test_session,
    organized_csv_file,
):
    result = save_cleaning_result(
        session=test_session,
        file_id=organized_csv_file.id,
        cleaned_dataframe=pd.DataFrame({"name": ["Menura"]}),
    )

    discard_cleaning_result(result)

    assert not result.csv_path.exists()
    assert not result.excel_path.exists()
