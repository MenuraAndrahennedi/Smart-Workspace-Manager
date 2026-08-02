from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from backend.database.repositories import create_file, read_file_by_id
from backend.services.xlsx_to_csv_service import (
    XLSXConversionError,
    convert_xlsx_to_csv,
    discard_conversion_output,
    get_convertible_xlsx_files,
    get_organized_xlsx_record,
    get_xlsx_sheet_names,
    preview_xlsx_sheet,
)


def create_workbook_record(
    test_session,
    temporary_data_root,
    *,
    name="sales.xlsx",
    status="organized",
    sheets=None,
):
    if sheets is None:
        sheets = {
            "Sales": pd.DataFrame(
                {
                    "region": ["North", "South"],
                    "revenue": [1250, 980],
                }
            ),
            "Targets": pd.DataFrame({"target": [1000, 1100]}),
        }

    workbook_directory = temporary_data_root / "processed" / "spreadsheets"
    workbook_directory.mkdir(parents=True, exist_ok=True)
    workbook_path = workbook_directory / name
    with pd.ExcelWriter(workbook_path, engine="openpyxl") as writer:
        for sheet_name, dataframe in sheets.items():
            dataframe.to_excel(writer, sheet_name=sheet_name, index=False)

    record = create_file(
        session=test_session,
        original_name=name,
        stored_name=f"stored_{name}",
        extension="xlsx",
        category="spreadsheets",
        size_bytes=workbook_path.stat().st_size,
        storage_path=str(workbook_path),
        status=status,
    )
    return record, workbook_path


def test_get_convertible_xlsx_files_returns_only_organized_workbooks(
    test_session,
    temporary_data_root,
):
    organized, _ = create_workbook_record(
        test_session,
        temporary_data_root,
        name="organized.xlsx",
    )
    create_workbook_record(
        test_session,
        temporary_data_root,
        name="failed.xlsx",
        status="failed",
    )
    create_file(
        session=test_session,
        original_name="data.csv",
        stored_name="stored_data.csv",
        extension="csv",
        category="spreadsheets",
        size_bytes=10,
        storage_path=str(temporary_data_root / "data.csv"),
        status="organized",
    )

    assert get_convertible_xlsx_files(test_session) == [organized]


def test_get_organized_xlsx_record_rejects_missing_wrong_type_and_status(
    test_session,
    temporary_data_root,
):
    failed, _ = create_workbook_record(
        test_session,
        temporary_data_root,
        status="failed",
    )
    csv_record = create_file(
        session=test_session,
        original_name="data.csv",
        stored_name="stored_data.csv",
        extension="csv",
        category="spreadsheets",
        size_bytes=10,
        storage_path=str(temporary_data_root / "data.csv"),
        status="organized",
    )

    with pytest.raises(XLSXConversionError, match="does not exist"):
        get_organized_xlsx_record(test_session, 9999)
    with pytest.raises(XLSXConversionError, match="must be an XLSX"):
        get_organized_xlsx_record(test_session, csv_record.id)
    with pytest.raises(XLSXConversionError, match="must be organized"):
        get_organized_xlsx_record(test_session, failed.id)


def test_get_sheet_names_and_preview_returns_selected_sheet_data(
    test_session,
    temporary_data_root,
):
    workbook, _ = create_workbook_record(test_session, temporary_data_root)

    assert get_xlsx_sheet_names(test_session, workbook.id) == ["Sales", "Targets"]

    preview = preview_xlsx_sheet(
        test_session,
        workbook.id,
        "Sales",
        preview_rows=1,
    )

    assert preview.sheet_name == "Sales"
    assert preview.row_count == 2
    assert preview.column_count == 2
    assert preview.dataframe.to_dict(orient="records") == [
        {"region": "North", "revenue": 1250}
    ]


def test_preview_rejects_invalid_sheet_and_preview_count(
    test_session,
    temporary_data_root,
):
    workbook, _ = create_workbook_record(test_session, temporary_data_root)

    with pytest.raises(XLSXConversionError, match="does not exist"):
        preview_xlsx_sheet(test_session, workbook.id, "Missing")
    with pytest.raises(XLSXConversionError, match="greater than zero"):
        preview_xlsx_sheet(test_session, workbook.id, "Sales", preview_rows=0)


def test_preview_rejects_unreadable_and_empty_workbooks(
    test_session,
    temporary_data_root,
):
    bad_path = temporary_data_root / "processed" / "spreadsheets" / "bad.xlsx"
    bad_path.parent.mkdir(parents=True, exist_ok=True)
    bad_path.write_bytes(b"not an xlsx workbook")
    bad_record = create_file(
        session=test_session,
        original_name="bad.xlsx",
        stored_name="stored_bad.xlsx",
        extension="xlsx",
        category="spreadsheets",
        size_bytes=bad_path.stat().st_size,
        storage_path=str(bad_path),
        status="organized",
    )
    empty_record, _ = create_workbook_record(
        test_session,
        temporary_data_root,
        name="empty.xlsx",
        sheets={"Empty": pd.DataFrame()},
    )

    with pytest.raises(XLSXConversionError, match="not a readable XLSX"):
        get_xlsx_sheet_names(test_session, bad_record.id)
    with pytest.raises(XLSXConversionError, match="does not contain any columns"):
        preview_xlsx_sheet(test_session, empty_record.id, "Empty")


def test_sheet_lookup_rejects_missing_managed_workbook(
    test_session,
    temporary_data_root,
):
    missing_record = create_file(
        session=test_session,
        original_name="missing.xlsx",
        stored_name="stored_missing.xlsx",
        extension="xlsx",
        category="spreadsheets",
        size_bytes=10,
        storage_path=str(temporary_data_root / "missing.xlsx"),
        status="organized",
    )

    with pytest.raises(XLSXConversionError, match="unavailable in managed storage"):
        get_xlsx_sheet_names(test_session, missing_record.id)


def test_sheet_lookup_enforces_workbook_size_limit(
    test_session,
    temporary_data_root,
    monkeypatch,
):
    workbook, workbook_path = create_workbook_record(
        test_session,
        temporary_data_root,
    )
    monkeypatch.setattr(
        "backend.config.settings.MAX_UPLOAD_SIZE_BYTES",
        workbook_path.stat().st_size - 1,
    )

    with pytest.raises(XLSXConversionError, match="conversion limit"):
        get_xlsx_sheet_names(test_session, workbook.id)


def test_preview_enforces_row_and_column_limits(
    test_session,
    temporary_data_root,
    monkeypatch,
):
    workbook, _ = create_workbook_record(test_session, temporary_data_root)

    monkeypatch.setattr("backend.config.settings.MAX_CSV_ROWS", 1)
    with pytest.raises(XLSXConversionError, match="row conversion limit"):
        preview_xlsx_sheet(test_session, workbook.id, "Sales")

    monkeypatch.setattr("backend.config.settings.MAX_CSV_ROWS", 10)
    monkeypatch.setattr("backend.config.settings.MAX_CSV_COLUMNS", 1)
    with pytest.raises(XLSXConversionError, match="column conversion limit"):
        preview_xlsx_sheet(test_session, workbook.id, "Sales")


def test_convert_xlsx_to_csv_saves_managed_csv_and_preserves_source(
    test_session,
    temporary_data_root,
):
    workbook, workbook_path = create_workbook_record(
        test_session,
        temporary_data_root,
    )
    original_bytes = workbook_path.read_bytes()

    result = convert_xlsx_to_csv(
        test_session,
        workbook.id,
        "Sales",
        date_value=datetime(2026, 8, 2),
    )

    assert result.source_file_id == workbook.id
    assert result.sheet_name == "Sales"
    assert result.row_count == 2
    assert result.column_count == 2
    assert result.csv_path.parent == (
        temporary_data_root / "processed" / "spreadsheets" / "2026" / "08"
    )
    assert result.csv_path.read_bytes().startswith(b"\xef\xbb\xbf")
    assert pd.read_csv(result.csv_path).to_dict(orient="records") == [
        {"region": "North", "revenue": 1250},
        {"region": "South", "revenue": 980},
    ]
    assert workbook_path.read_bytes() == original_bytes

    converted_record = read_file_by_id(test_session, result.file_id)
    assert converted_record.original_name == "sales_Sales.csv"
    assert converted_record.stored_name == result.csv_filename
    assert converted_record.extension == "csv"
    assert converted_record.category == "spreadsheets"
    assert converted_record.status == "organized"
    assert converted_record.storage_path == str(result.csv_path)
    assert converted_record.size_bytes == result.size_bytes


def test_repeated_conversions_create_unique_files(
    test_session,
    temporary_data_root,
):
    workbook, _ = create_workbook_record(test_session, temporary_data_root)

    first = convert_xlsx_to_csv(test_session, workbook.id, "Sales")
    second = convert_xlsx_to_csv(test_session, workbook.id, "Sales")

    assert first.file_id != second.file_id
    assert first.csv_filename != second.csv_filename
    assert first.csv_path != second.csv_path
    assert first.csv_path.is_file()
    assert second.csv_path.is_file()


def test_conversion_write_failure_removes_partial_output(
    test_session,
    temporary_data_root,
    monkeypatch,
):
    workbook, _ = create_workbook_record(test_session, temporary_data_root)

    def fail_write(dataframe, path, **kwargs):
        Path(path).write_bytes(b"partial")
        raise OSError("write failed")

    monkeypatch.setattr(pd.DataFrame, "to_csv", fail_write)

    with pytest.raises(OSError, match="write failed"):
        convert_xlsx_to_csv(test_session, workbook.id, "Sales")

    generated_csv_files = list(
        temporary_data_root.glob("processed/spreadsheets/*/*/*.csv")
    )
    assert generated_csv_files == []


def test_database_failure_removes_generated_csv(
    test_session,
    temporary_data_root,
    monkeypatch,
):
    workbook, _ = create_workbook_record(test_session, temporary_data_root)

    def fail_create_file(**kwargs):
        raise RuntimeError("database failed")

    monkeypatch.setattr(
        "backend.services.xlsx_to_csv_service.create_file",
        fail_create_file,
    )

    with pytest.raises(RuntimeError, match="database failed"):
        convert_xlsx_to_csv(test_session, workbook.id, "Sales")

    assert list(temporary_data_root.glob("processed/spreadsheets/*/*/*.csv")) == []


def test_discard_conversion_output_deletes_managed_file(temporary_data_root):
    csv_path = temporary_data_root / "processed" / "spreadsheets" / "output.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.write_text("value\n1\n", encoding="utf-8")

    discard_conversion_output(csv_path)

    assert not csv_path.exists()
