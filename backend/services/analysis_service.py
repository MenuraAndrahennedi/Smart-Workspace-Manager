from dataclasses import dataclass
import json
from operator import attrgetter
from pathlib import Path
from typing import Any

import pandas as pd
import logging
from sqlalchemy.orm import Session
from pandas.api.types import is_numeric_dtype

from backend.config.settings import MAX_CSV_ANALYSIS_SIZE_MB, MAX_CSV_ROWS, MAX_CSV_COLUMNS
from backend.database.models import FileRecord
from backend.database.repositories import query_files, read_file_by_id, create_analysis_job, update_analysis_job 
from backend.utils.validators import validate_file_extension
from backend.services.storage_service import resolve_managed_path

logger = logging.getLogger(__name__)


# Custom error classes
class CSVAnalysisError(Exception):
    pass

class CSVLimitError(CSVAnalysisError):
    pass

# Structured result
@dataclass
class CSVAnalysisResult:
    preview: pd.DataFrame
    row_count: int
    column_count: int
    columns: list[str]
    data_types: dict[str, str]
    missing_values: dict[str, int]
    duplicate_count: int
    descriptive_statistics: pd.DataFrame

@dataclass
class RecordedCSVAnalysis:
    job_id: int
    result: CSVAnalysisResult

def load_csv_with_limits(csv_path: Path) -> pd.DataFrame:
    csv_path = resolve_managed_path(
        csv_path,
        must_exist=True,
        file_only=True,
    )

    if validate_file_extension(csv_path.name) != "csv":
        raise ValueError("Path does not point to a CSV file.")

    if csv_path.stat().st_size > MAX_CSV_ANALYSIS_SIZE_MB * (1024**2):
        raise CSVLimitError(
            f"The CSV exceeds the {MAX_CSV_ANALYSIS_SIZE_MB} MB analysis limit."
        )
    
    try:
        header = pd.read_csv(csv_path, nrows=0, encoding="utf-8-sig")
        num_cols = header.shape[1]
        if num_cols > MAX_CSV_COLUMNS:
            raise CSVLimitError(
                f"The CSV exceeds the {MAX_CSV_COLUMNS}-column analysis limit."
            )

        df = pd.read_csv(csv_path, nrows=MAX_CSV_ROWS+1, encoding="utf-8-sig")
        num_rows = df.shape[0]
        if num_rows > MAX_CSV_ROWS:
            raise CSVLimitError(
                f"The CSV exceeds the {MAX_CSV_ROWS}-row analysis limit."
            )

        return df

    except pd.errors.EmptyDataError as error:
        logger.exception("Failed to parse CSV file: %s", csv_path)
        raise CSVAnalysisError("The selected CSV is empty.") from error

    except pd.errors.ParserError as error:
        logger.exception("Failed to parse CSV file: %s", csv_path)
        raise CSVAnalysisError("The CSV structure is invalid or malformed.") from error

    except UnicodeDecodeError as error:
        logger.exception("Failed to parse CSV file: %s", csv_path)
        raise CSVAnalysisError("The CSV is not encoded as UTF-8.") from error

    except OSError as error:
        logger.exception("Failed to parse CSV file: %s", csv_path)
        raise OSError("The operating system could not read the file.") from error

def analyze_dataframe(
    dataframe: pd.DataFrame,
    preview_rows: int = 5,
) -> CSVAnalysisResult:
    if dataframe.empty:
        raise CSVAnalysisError("The selected CSV contains no data rows.")
    if preview_rows <= 0:
        raise ValueError("Preview rows must be greater than zero.")
    
    preview = dataframe.head(preview_rows).copy()
    row_count = dataframe.shape[0]
    column_count = dataframe.shape[1]
    columns = dataframe.columns.tolist()
    data_types = dataframe.dtypes.astype(str).to_dict()
    missing_values = dataframe.isna().sum().astype(int).to_dict()
    duplicate_count = int(dataframe.duplicated().sum())
    descriptive_statistics = dataframe.describe(include="all").transpose() # Get statistics of each column -> get all -> transpose(convert columns to rows)

    return CSVAnalysisResult(
        preview=preview,
        row_count = row_count,
        column_count = column_count,
        columns=columns,
        data_types=data_types,
        missing_values=missing_values,
        duplicate_count=duplicate_count,
        descriptive_statistics=descriptive_statistics,
    )


def analyze_csv(csv_path: Path, preview_rows: int = 5) -> CSVAnalysisResult:
    dataframe = load_csv_with_limits(csv_path)
    if dataframe.empty:
        raise CSVAnalysisError("The selected CSV contains no data rows.")
    
    result: CSVAnalysisResult = analyze_dataframe(dataframe, preview_rows)

    return result
    

    


def get_analyzable_csv_files(session: Session) -> list[FileRecord]:
    files = query_files(
        session,
        category=["spreadsheets"],
        status=["organized"],
    )
    csv_files: list[FileRecord] = []

    for file in files:
        if file.extension.lower() == "csv":
            csv_files.append(file)

    return sorted(csv_files,  key=attrgetter('updated_at'), reverse = True)


def get_organized_csv_record(
    session: Session,
    file_id: int,
) -> FileRecord:
    file_record = read_file_by_id(session, file_id)
    if file_record is None:
        raise CSVAnalysisError("The selected file does not exist.")
    if file_record.extension.lstrip(".").lower() != "csv":
        raise CSVAnalysisError("The selected file must be a CSV file.")
    if file_record.status.lower() != "organized":
        raise CSVAnalysisError("The selected CSV file must be organized.")
    return file_record


def load_organized_csv(
    session: Session,
    file_id: int,
) -> tuple[FileRecord, pd.DataFrame]:
    file_record = get_organized_csv_record(session, file_id)
    return file_record, load_csv_with_limits(file_record.storage_path)

def analyze_file_and_record_job(
    session: Session,
    file_id: int,
    preview_rows: int = 10,
) -> RecordedCSVAnalysis:
    file_record = get_organized_csv_record(session, file_id)

    requested_options = {
        "preview_rows": preview_rows,
    }

    analysis_job = create_analysis_job(
        session=session,
        file_id=file_record.id,
        status="running",
        requested_options=json.dumps(requested_options),
    )

    try:
        result = analyze_csv(
            csv_path=Path(file_record.storage_path),
            preview_rows=preview_rows,
        )

        summary = {
            "row_count": result.row_count,
            "column_count": result.column_count,
            "columns": result.columns,
            "data_types": result.data_types,
            "missing_values": result.missing_values,
            "total_missing_values": sum(
                result.missing_values.values()
            ),
            "duplicate_count": result.duplicate_count,
        }

        update_analysis_job(
            session=session,
            job_id=analysis_job.id,
            status="completed",
            summary=json.dumps(summary),
            error_message=None,
        )

        return RecordedCSVAnalysis(
            job_id=analysis_job.id,
            result=result,
        )

    except (CSVAnalysisError, CSVLimitError) as error:
        update_analysis_job(
            session=session,
            job_id=analysis_job.id,
            status="failed",
            summary=None,
            error_message=str(error),
        )

        raise

    except Exception as error:
        update_analysis_job(
            session=session,
            job_id=analysis_job.id,
            status="failed",
            summary=None,
            error_message="An unexpected error occurred while analyzing the CSV.",
        )
        raise
    

# Data filtering 
def _apply_numeric_filter(
    dataframe: pd.DataFrame,
    filter_column: str,
    operator: str,
    filter_value: Any,
) -> pd.DataFrame:
    try:
        numeric_value = float(filter_value)
    except (TypeError, ValueError) as error:
        raise CSVAnalysisError(
            "Enter a valid numeric filter value."
        ) from error

    column = dataframe[filter_column]

    if operator == "Equals":
        mask = column == numeric_value

    elif operator == "Greater than":
        mask = column > numeric_value

    elif operator == "Less than":
        mask = column < numeric_value

    else:
        raise CSVAnalysisError(
            f"'{operator}' is not a valid numeric filter operator."
        )

    return dataframe.loc[mask].copy()

def _apply_text_filter(
    dataframe: pd.DataFrame,
    filter_column: str,
    operator: str,
    filter_value: Any,
) -> pd.DataFrame:
    search_value = str(filter_value)
    column = dataframe[filter_column].astype("string")

    if operator == "Contains":
        mask = column.str.contains(
            search_value,
            case=False,
            na=False,
            regex=False,
        )

    elif operator == "Equals":
        mask = (
            column.str.casefold()
            == search_value.casefold()
        )

    elif operator == "Starts with":
        mask = column.str.startswith(
            search_value,
            na=False,
        )

    else:
        raise CSVAnalysisError(
            f"'{operator}' is not a valid text filter operator."
        )

    return dataframe.loc[mask].copy()



def filter_csv_data(
    session: Session,
    file_id: int,
    selected_columns: list[str],
    filter_column: str | None = None,
    operator: str | None = None,
    filter_value: Any | None = None,
    maximum_result_rows: int = 100,
) -> pd.DataFrame:
    if maximum_result_rows < 1:
        raise ValueError("maximum_result_rows must be at least 1.")

    _, dataframe = load_organized_csv(session, file_id)

    if not selected_columns:
        raise CSVAnalysisError("Select at least one column.")

    invalid_columns = [
        column
        for column in selected_columns
        if column not in dataframe.columns
    ]

    if invalid_columns:
        raise CSVAnalysisError(
            f"Invalid selected column(s): {', '.join(invalid_columns)}"
        )

    filtered_dataframe = dataframe.copy()

    if filter_column is not None:
        if filter_column not in dataframe.columns:
            raise CSVAnalysisError(
                f"The filter column '{filter_column}' does not exist."
            )

        if operator is None:
            raise CSVAnalysisError("Select a filter operator.")

        if filter_value is None or str(filter_value).strip() == "":
            raise CSVAnalysisError("Enter a filter value.")

        column_series = dataframe[filter_column]

        if is_numeric_dtype(column_series):
            filtered_dataframe = _apply_numeric_filter(
                dataframe=dataframe,
                filter_column=filter_column,
                operator=operator,
                filter_value=filter_value,
            )
        else:
            filtered_dataframe = _apply_text_filter(
                dataframe=dataframe,
                filter_column=filter_column,
                operator=operator,
                filter_value=filter_value,
            )

    filtered_dataframe = filtered_dataframe.loc[:, selected_columns]

    # Only the displayed output.
    return filtered_dataframe.head(maximum_result_rows).copy()



