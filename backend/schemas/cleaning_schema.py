from pydantic import BaseModel

class CleaningRequest(BaseModel):
    remove_duplicates: bool = False
    duplicate_columns: tuple[str, ...] | None = None
    
    numeric_fill_column: str | None = None
    numeric_fill_strategy: str | None = None
    numeric_fill_value: float | None = None
    
    text_fill_column: str | None = None
    text_fill_value: str | None = None
    
    drop_missing_rows: bool = False
    drop_missing_columns: tuple[str, ...] | None = None

class CleaningResultResponse(BaseModel):
    cleaned_dataframe: list[dict]
    original_row_count: int
    cleaned_row_count: int
    duplicates_removed: int
    missing_values_filled: int
    rows_dropped: int
    remaining_missing_values: int

class CleaningSaveResponse(BaseModel):
    csv_file_id: int
    excel_file_id: int
    csv_filename: str
    excel_filename: str
    row_count: int
    column_count: int