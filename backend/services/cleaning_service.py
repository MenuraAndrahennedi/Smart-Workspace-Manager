from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session

import pandas as pd

from backend.config import settings
from backend.database.repositories import create_file
from backend.services.analysis_service import (
    CSVAnalysisError,
    get_organized_csv_record,
    load_organized_csv,
)
from backend.utils.file_utils import ensure_dated_directory, generate_safe_filename
from backend.utils.time_utils import time_now


class DataCleaningError(Exception):
    pass

@dataclass(frozen=True)
class CleaningOptions:
    remove_duplicates: bool = False
    duplicate_columns: tuple[str, ...] | None = None

    numeric_fill_column: str | None = None
    numeric_fill_strategy: str | None = None
    numeric_fill_value: float | None = None

    text_fill_column: str | None = None
    text_fill_value: str | None = None

    drop_missing_rows: bool = False
    drop_missing_columns: tuple[str, ...] | None = None


@dataclass
class DuplicateRemovalResult:
    cleaned_dataframe: pd.DataFrame
    original_row_count: int
    cleaned_row_count: int
    removed_duplicate_count: int

@dataclass
class MissingValueActionResult:
    cleaned_dataframe: pd.DataFrame
    original_missing_count: int
    remaining_missing_count: int
    rows_removed: int
    values_filled: int

@dataclass
class CleaningPreviewResult:
    cleaned_dataframe: pd.DataFrame
    original_row_count: int
    cleaned_row_count: int
    duplicates_removed: int
    missing_values_filled: int
    rows_dropped: int
    remaining_missing_values: int

@dataclass
class CleaningSaveResult:
    csv_file_id: int
    excel_file_id: int
    csv_path: Path
    excel_path: Path
    csv_filename: str
    excel_filename: str
    row_count: int
    column_count: int


@dataclass(frozen=True)
class CleaningColumnOptions:
    numeric_columns: list[str]
    text_columns: list[str]


def load_cleaning_source(
    session: Session,
    file_id: int,
) -> pd.DataFrame:
    try:
        _, dataframe = load_organized_csv(session, file_id)
        return dataframe
    except CSVAnalysisError as error:
        raise DataCleaningError(str(error)) from error


def get_cleaning_column_options(
    dataframe: pd.DataFrame,
) -> CleaningColumnOptions:
    return CleaningColumnOptions(
        numeric_columns=dataframe.select_dtypes(
            include="number"
        ).columns.tolist(),
        text_columns=dataframe.select_dtypes(
            include=["object", "string"]
        ).columns.tolist(),
    )

# Duplicate Remover
def remove_duplicates(
    original_df: pd.DataFrame,
    subset: list[str] | None = None,
) -> DuplicateRemovalResult:
    working_df = original_df.copy()

    if subset is not None:
        if not subset:
            raise DataCleaningError("Select at least one duplicate-check column.")

        if not set(subset).issubset(set(original_df.columns.tolist())):
            raise DataCleaningError("Duplicate checking can only use columns from the original CSV.")

        cleaned_df = working_df.drop_duplicates(
            subset=subset,
            keep="first",
        ).reset_index(drop=True)

    else:
        cleaned_df = working_df.drop_duplicates(
            keep="first",
        ).reset_index(drop=True)
   

    return DuplicateRemovalResult(
        cleaned_dataframe = cleaned_df,
        original_row_count = original_df.shape[0],
        cleaned_row_count = cleaned_df.shape[0],
        removed_duplicate_count = original_df.shape[0] - cleaned_df.shape[0]
    )

# Missing-Value Cleaning Actions
def drop_rows_with_missing_values(
    original_df: pd.DataFrame,
    columns: list[str] | None = None,
) -> MissingValueActionResult:
    working_df = original_df.copy()
    
    if columns is not None:
        if not columns:
            raise DataCleaningError("Select at least one column for missing-value removal.")
    
        if not set(columns).issubset(set(original_df.columns.tolist())):
            raise DataCleaningError("Missing-value removal can only use columns from the original CSV.")
    
        cleaned_df = working_df.dropna(
            subset=columns,
        ).reset_index(drop=True)
    
    else:
        cleaned_df = working_df.dropna().reset_index(drop=True)
    
    
    return MissingValueActionResult(
        cleaned_dataframe = cleaned_df,
        original_missing_count = int(original_df.isna().sum().sum()),
        remaining_missing_count = int(cleaned_df.isna().sum().sum()),
        rows_removed = len(original_df) - len(cleaned_df),
        values_filled = 0,
    )


def fill_numeric_missing_values(
    original_df: pd.DataFrame,
    column: str,
    strategy: str,
    fill_value: float | None = None,
) -> MissingValueActionResult:
    cleaned_df = original_df.copy()
    
    if not column:
        raise DataCleaningError("Select a numeric column to fill.")
    
    if column not in original_df.columns:
        raise DataCleaningError(f"Column '{column}' must be an original column.")

    if not pd.api.types.is_numeric_dtype(original_df[column]):
        raise DataCleaningError(f"Column '{column}' must be numeric.")
    

    replacement = None
    match strategy:
        case "mean":
            replacement = original_df[column].mean()
        case "median":
            replacement = original_df[column].median()
        case "constant":
            if fill_value is None:
                raise DataCleaningError("A fill value is required for the constant strategy.")
            replacement = fill_value
        case _:
            raise DataCleaningError(f"The '{strategy}' fill strategy is not supported.")

    if pd.isna(replacement):
        raise DataCleaningError(
            f"Column '{column}' has no usable numeric values for the '{strategy}' strategy.")

    cleaned_df[column] = (
        cleaned_df[column].fillna(replacement)
    )
    
    
    return MissingValueActionResult(
        cleaned_dataframe = cleaned_df,
        original_missing_count = int(original_df.isna().sum().sum()),
        remaining_missing_count = int(cleaned_df.isna().sum().sum()),
        rows_removed = 0,
        values_filled = int(original_df[column].isna().sum()),
    )



def fill_text_missing_values(
    original_df: pd.DataFrame,
    column: str,
    fill_value: str,
) -> MissingValueActionResult:
    cleaned_df = original_df.copy()
    
    if not column:
        raise DataCleaningError("Select a text column to fill.")
    
    if column not in original_df.columns:
        raise DataCleaningError(f"Column '{column}' must be an original column.")

    if pd.api.types.is_numeric_dtype(original_df[column]):
        raise DataCleaningError(f"Column '{column}' must be a text column.")
    
    if fill_value is None or fill_value == "":
        raise DataCleaningError("Fill value cannot be empty.")

    cleaned_df[column] = (
        cleaned_df[column].fillna(fill_value)
    )
    
    
    return MissingValueActionResult(
        cleaned_dataframe = cleaned_df,
        original_missing_count = int(original_df.isna().sum().sum()),
        remaining_missing_count = int(cleaned_df.isna().sum().sum()),
        rows_removed = 0,
        values_filled = int(original_df[column].isna().sum()),
    )



# Save cleaned copies
def preview_cleaning(
    session: Session,
    file_id: int,
    cleaning_options: CleaningOptions,
) -> CleaningPreviewResult:
    original_df = load_cleaning_source(session, file_id)
    working_df = original_df.copy()

    duplicates_removed = 0
    missing_values_filled = 0
    rows_dropped = 0

    if cleaning_options.remove_duplicates:
        subset = list(cleaning_options.duplicate_columns) if cleaning_options.duplicate_columns is not None else None
        duplicate_removed_result = remove_duplicates(working_df, subset)

        working_df =  duplicate_removed_result.cleaned_dataframe
        duplicates_removed = duplicate_removed_result.removed_duplicate_count

    if cleaning_options.numeric_fill_column is not None:
        numeric_fill_result = fill_numeric_missing_values(
            working_df, 
            cleaning_options.numeric_fill_column, 
            cleaning_options.numeric_fill_strategy, 
            cleaning_options.numeric_fill_value,
        )

        working_df = numeric_fill_result.cleaned_dataframe
        missing_values_filled += numeric_fill_result.values_filled

    if cleaning_options.text_fill_column is not None:
        text_fill_result = fill_text_missing_values(
            working_df, 
            cleaning_options.text_fill_column, 
            cleaning_options.text_fill_value,
        )

        working_df = text_fill_result.cleaned_dataframe
        missing_values_filled += text_fill_result.values_filled

    if cleaning_options.drop_missing_rows:
        columns = list(cleaning_options.drop_missing_columns) if cleaning_options.drop_missing_columns is not None else None
        drop_result = drop_rows_with_missing_values(working_df, columns)

        working_df = drop_result.cleaned_dataframe
        rows_dropped = drop_result.rows_removed

    return CleaningPreviewResult(
        cleaned_dataframe=working_df,
        original_row_count=len(original_df),
        cleaned_row_count=len(working_df),
        duplicates_removed=duplicates_removed,
        missing_values_filled=missing_values_filled,
        rows_dropped=rows_dropped,
        remaining_missing_values=int(working_df.isna().sum().sum()),
    )

def save_cleaning_result(
    session : Session,
    file_id: int,
    cleaned_dataframe: pd.DataFrame,
    date_value: datetime | None = None,
) -> CleaningSaveResult:
    try:
        file_record = get_organized_csv_record(session, file_id)
    except CSVAnalysisError as error:
        raise DataCleaningError(str(error)) from error

    if date_value is None:
        date_value = time_now()
        
    csv_directory = ensure_dated_directory(
        settings.DATA_ROOT / "processed" / "cleaned" / "csv",
        date_value,
    )
    excel_directory = ensure_dated_directory(
        settings.DATA_ROOT / "processed" / "cleaned" / "excel",
        date_value,
    )

    stem = Path(file_record.original_name).stem
    csv_original_name = f"{stem}_cleaned.csv"
    excel_original_name = f"{stem}_cleaned.xlsx"
    csv_filename = generate_safe_filename(csv_original_name)
    excel_filename = generate_safe_filename(excel_original_name)
    csv_path = csv_directory / csv_filename
    excel_path = excel_directory / excel_filename


    try:
        cleaned_dataframe.to_csv(
            csv_path,
            index=False,
            encoding="utf-8-sig",
        )
        cleaned_dataframe.to_excel(
            excel_path,
            index=False,
        )
        csv_record = create_file(
            session=session,
            original_name=csv_original_name,
            stored_name=csv_filename,
            extension="csv",
            category="spreadsheets",
            size_bytes=csv_path.stat().st_size,
            storage_path=str(csv_path),
            status="organized",
        )
        excel_record = create_file(
            session=session,
            original_name=excel_original_name,
            stored_name=excel_filename,
            extension="xlsx",
            category="spreadsheets",
            size_bytes=excel_path.stat().st_size,
            storage_path=str(excel_path),
            status="organized",
        )
    except Exception:
        session.rollback()
        csv_path.unlink(missing_ok=True)
        excel_path.unlink(missing_ok=True)
        raise

    return CleaningSaveResult(
        csv_file_id=csv_record.id,
        excel_file_id=excel_record.id,
        csv_path = csv_path,
        excel_path = excel_path,
        csv_filename = csv_filename,
        excel_filename = excel_filename,
        row_count = cleaned_dataframe.shape[0],
        column_count = cleaned_dataframe.shape[1]
    )


def discard_cleaning_result(result: CleaningSaveResult) -> None:
    result.csv_path.unlink(missing_ok=True)
    result.excel_path.unlink(missing_ok=True)



    






    







