from dataclasses import dataclass
from datetime import datetime
from operator import attrgetter
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database.models import FileRecord
from backend.database.repositories import create_file, query_files, read_file_by_id
from backend.services.storage_service import delete_stored_file, resolve_managed_path
from backend.utils.file_utils import ensure_dated_directory, generate_safe_filename
from backend.utils.time_utils import time_now


class XLSXConversionError(Exception):
    pass


@dataclass(frozen=True)
class XLSXPreviewResult:
    dataframe: pd.DataFrame
    sheet_name: str
    row_count: int
    column_count: int


@dataclass(frozen=True)
class XLSXConversionResult:
    file_id: int
    source_file_id: int
    sheet_name: str
    csv_path: Path
    csv_filename: str
    row_count: int
    column_count: int
    size_bytes: int


def get_convertible_xlsx_files(session: Session) -> list[FileRecord]:
    files = query_files(
        session=session,
        category=["spreadsheets"],
        status=["organized"],
    )
    xlsx_files = [
        file_record
        for file_record in files
        if file_record.extension.lstrip(".").lower() == "xlsx"
    ]
    return sorted(xlsx_files, key=attrgetter("updated_at"), reverse=True)


def get_organized_xlsx_record(session: Session, file_id: int) -> FileRecord:
    file_record = read_file_by_id(session, file_id)
    if file_record is None:
        raise XLSXConversionError("The selected workbook does not exist.")
    if file_record.extension.lstrip(".").lower() != "xlsx":
        raise XLSXConversionError("The selected file must be an XLSX workbook.")
    if file_record.status.lower() != "organized":
        raise XLSXConversionError("The selected workbook must be organized.")
    return file_record


def _get_workbook_path(session: Session, file_id: int) -> tuple[FileRecord, Path]:
    file_record = get_organized_xlsx_record(session, file_id)
    try:
        workbook_path = resolve_managed_path(
            file_record.storage_path,
            must_exist=True,
            file_only=True,
        )
    except (FileNotFoundError, OSError, ValueError) as error:
        raise XLSXConversionError(
            "The selected workbook is unavailable in managed storage."
        ) from error
    if workbook_path.stat().st_size > settings.MAX_UPLOAD_SIZE_BYTES:
        raise XLSXConversionError(
            f"The workbook exceeds the {settings.MAX_UPLOAD_SIZE_MB} MB conversion limit."
        )
    return file_record, workbook_path


def _open_workbook(workbook_path: Path) -> pd.ExcelFile:
    try:
        return pd.ExcelFile(workbook_path, engine="openpyxl")
    except Exception as error:
        raise XLSXConversionError(
            "The selected file is not a readable XLSX workbook."
        ) from error


def get_xlsx_sheet_names(session: Session, file_id: int) -> list[str]:
    _, workbook_path = _get_workbook_path(session, file_id)
    with _open_workbook(workbook_path) as workbook:
        sheet_names = list(workbook.sheet_names)
    if not sheet_names:
        raise XLSXConversionError("The selected workbook contains no worksheets.")
    return sheet_names


def _load_xlsx_sheet(
    session: Session,
    file_id: int,
    sheet_name: str,
) -> tuple[FileRecord, pd.DataFrame]:
    if not sheet_name:
        raise XLSXConversionError("Select a worksheet to convert.")

    file_record, workbook_path = _get_workbook_path(session, file_id)
    with _open_workbook(workbook_path) as workbook:
        if sheet_name not in workbook.sheet_names:
            raise XLSXConversionError(
                f"Worksheet '{sheet_name}' does not exist in the selected workbook."
            )
        try:
            dataframe = pd.read_excel(
                workbook,
                sheet_name=sheet_name,
                nrows=settings.MAX_CSV_ROWS + 1,
            )
        except Exception as error:
            raise XLSXConversionError(
                f"Worksheet '{sheet_name}' could not be read."
            ) from error

    if dataframe.shape[1] == 0:
        raise XLSXConversionError(
            f"Worksheet '{sheet_name}' does not contain any columns."
        )
    if dataframe.shape[0] > settings.MAX_CSV_ROWS:
        raise XLSXConversionError(
            f"The worksheet exceeds the {settings.MAX_CSV_ROWS}-row conversion limit."
        )
    if dataframe.shape[1] > settings.MAX_CSV_COLUMNS:
        raise XLSXConversionError(
            f"The worksheet exceeds the {settings.MAX_CSV_COLUMNS}-column conversion limit."
        )
    return file_record, dataframe


def preview_xlsx_sheet(
    session: Session,
    file_id: int,
    sheet_name: str,
    preview_rows: int = 10,
) -> XLSXPreviewResult:
    if preview_rows <= 0:
        raise XLSXConversionError("Preview rows must be greater than zero.")

    _, dataframe = _load_xlsx_sheet(session, file_id, sheet_name)
    return XLSXPreviewResult(
        dataframe=dataframe.head(preview_rows).copy(),
        sheet_name=sheet_name,
        row_count=dataframe.shape[0],
        column_count=dataframe.shape[1],
    )


def _build_csv_name(workbook_name: str, sheet_name: str) -> str:
    suffix = f"_{sheet_name}.csv"
    max_stem_length = max(1, 255 - len(suffix))
    return f"{Path(workbook_name).stem[:max_stem_length]}{suffix}"


def convert_xlsx_to_csv(
    session: Session,
    file_id: int,
    sheet_name: str,
    date_value: datetime | None = None,
) -> XLSXConversionResult:
    file_record, dataframe = _load_xlsx_sheet(session, file_id, sheet_name)
    if date_value is None:
        date_value = time_now()

    csv_directory = ensure_dated_directory(
        settings.DATA_ROOT / "processed" / "spreadsheets",
        date_value,
    )
    original_csv_name = _build_csv_name(file_record.original_name, sheet_name)
    csv_filename = generate_safe_filename(original_csv_name)
    csv_path = csv_directory / csv_filename

    try:
        dataframe.to_csv(csv_path, index=False, encoding="utf-8-sig")
        converted_record = create_file(
            session=session,
            original_name=original_csv_name,
            stored_name=csv_filename,
            extension="csv",
            category="spreadsheets",
            size_bytes=csv_path.stat().st_size,
            storage_path=str(csv_path),
            status="organized",
        )
    except Exception:
        csv_path.unlink(missing_ok=True)
        raise

    return XLSXConversionResult(
        file_id=converted_record.id,
        source_file_id=file_record.id,
        sheet_name=sheet_name,
        csv_path=csv_path,
        csv_filename=csv_filename,
        row_count=dataframe.shape[0],
        column_count=dataframe.shape[1],
        size_bytes=csv_path.stat().st_size,
    )


def discard_conversion_output(csv_path: str | Path) -> None:
    delete_stored_file(Path(csv_path))
