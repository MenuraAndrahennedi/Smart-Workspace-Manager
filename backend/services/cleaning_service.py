from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session

import pandas as pd

from backend.config.settings import DATA_ROOT, time_now
from backend.database.repositories import read_file_by_id
from backend.services.analysis_service import load_csv_with_limits
from backend.utils.file_utils import ensure_directory, generate_safe_filename


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
    csv_path: Path
    excel_path: Path
    csv_filename: str
    excel_filename: str
    row_count: int
    column_count: int

# Duplicate Remover
def remove_duplicates(
    original_df: pd.DataFrame,
    subset: list[str] | None = None,
) -> DuplicateRemovalResult:
    working_df = original_df.copy()

    if subset is not None:
        if not subset:
            raise DataCleaningError("Column subset list cannot be an empty list")

        if not set(subset).issubset(set(original_df.columns.tolist())):
            raise DataCleaningError("Column subset list can only contain original columns")

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
            raise DataCleaningError("Columns list cannot be an empty list")
    
        if not set(columns).issubset(set(original_df.columns.tolist())):
            raise DataCleaningError("Columns list can only contain original columns")
    
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
        raise DataCleaningError("Column cannot be an empty")
    
    if column not in original_df.columns:
        raise DataCleaningError(f"Column '{column}' must be an original column.")

    if not pd.api.types.is_numeric_dtype(original_df[column]):
        raise DataCleaningError(f"Column {column} must be numeric")
    

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
            raise DataCleaningError(f"Provided '{strategy}' strategy is unsupported")

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
        raise DataCleaningError("Column cannot be an empty")
    
    if column not in original_df.columns:
        raise DataCleaningError(f"Column '{column}' must be an original column.")

    if pd.api.types.is_numeric_dtype(original_df[column]):
        raise DataCleaningError(f"Column {column} must be a text column")
    
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
    file_record = read_file_by_id(session, file_id)

    if file_record is None:
        raise DataCleaningError("The selected file does not exist.")

    if file_record.status.lower() != "organized":
        raise ValueError("Selected CSV file is not organized yet")

    original_df = load_csv_with_limits(file_record.storage_path)
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
    file_record = read_file_by_id(session, file_id)

    if file_record is None:
        raise DataCleaningError("The original file record does not exist.")

    if file_record.status.lower() != "organized":
        raise ValueError("Selected CSV file is not organized yet")

    if date_value is None:
        date_value = time_now()
        
    year = date_value.strftime("%Y")
    month = date_value.strftime("%m")
    
    csv_directory = ensure_directory(DATA_ROOT / "processed" / "cleaned"/ "csv" / year / month)
    excel_directory = ensure_directory(DATA_ROOT / "processed" / "cleaned"/ "excel" / year / month)

    stem = Path(file_record.original_name).stem
    csv_filename = generate_safe_filename(f"{stem}_cleaned.csv")
    excel_filename = generate_safe_filename(f"{stem}_cleaned.xlsx")
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
    except Exception:
        csv_path.unlink(missing_ok=True)
        excel_path.unlink(missing_ok=True)
        raise

    return CleaningSaveResult(
        csv_path = csv_path,
        excel_path = excel_path,
        csv_filename = csv_filename,
        excel_filename = excel_filename,
        row_count = cleaned_dataframe.shape[0],
        column_count = cleaned_dataframe.shape[1]
    )



    






    







