from dataclasses import dataclass
import logging
from pathlib import Path
from sqlalchemy.orm import Session

from backend.utils.validators import (
    validate_filename, 
    validate_file_extension, 
    validate_file_size,
    get_file_extension,
    get_file_category
)
from backend.services.storage_service import (
    PENDING_FILE_DELETIONS_KEY,
    delete_stored_file,
    restore_staged_files,
    save_uploaded_bytes,
    stage_files_for_deletion,
)
from backend.utils.file_utils import generate_safe_filename
from backend.database.repositories import (
    create_file,
    delete_file,
    get_report_storage_paths,
    read_file_by_id,
)
from backend.config.settings import MAX_FILENAME_ATTEMPTS, MAX_UPLOAD_SIZE_BYTES

logger = logging.getLogger(__name__)

@dataclass
class FileUploadResult:
    file_id: int
    original_filename: str
    stored_filename: str
    extension: str
    size_bytes: int
    saved_path: str
    status: str
    
def validate_upload(filename: str, filesize_bytes: int) -> str:
    cleaned_filename = validate_filename(filename)
    validate_file_extension(cleaned_filename)
    validate_file_size(filesize_bytes, MAX_UPLOAD_SIZE_BYTES)
    return cleaned_filename

def upload_file(
    filename: str,
    file_bytes: bytes,
    session: Session,
) -> FileUploadResult:
    filesize_bytes = len(file_bytes)
    filename = validate_upload(filename, filesize_bytes)
    saved_path: Path | None = None

    try:
        for attempt in range(MAX_FILENAME_ATTEMPTS):
            stored_filename = generate_safe_filename(filename)
            try:
                saved_path = save_uploaded_bytes(stored_filename, file_bytes)
                break
            except FileExistsError:
                continue
        else:
            raise FileExistsError(
                "Could not generate a unique stored filename"
            )

        extension = get_file_extension(stored_filename)
        file_record = create_file(
            session,
            filename,
            stored_filename,
            extension,
            get_file_category(filename),
            filesize_bytes,
            str(saved_path)
        )
        return FileUploadResult(
            file_id=file_record.id,
            original_filename=filename,
            stored_filename=stored_filename,
            extension=extension,
            size_bytes=filesize_bytes,
            saved_path=str(saved_path),
            status=file_record.status,
        )
    except Exception:
        session.rollback()
        try:
            if saved_path is not None:
                delete_stored_file(saved_path)
        except OSError:
            logger.exception("Failed to clean up partially uploaded file")
        raise


def delete_actual_file(
    session: Session,
    file_id: int,
) -> dict[str, object]:
    file_record = read_file_by_id(
        session=session,
        file_id=file_id,
    )

    if file_record is None:
        raise FileNotFoundError(f"File record with ID {file_id} was not found.")

    original_name = file_record.original_name
    storage_path = Path(file_record.storage_path).resolve()
    physical_file_existed = storage_path.is_file()
    report_paths = get_report_storage_paths(
        session=session,
        file_id=file_id,
    )
    staged_deletions = stage_files_for_deletion(
        [storage_path, *report_paths]
    )

    try:
        db_record_deleted = delete_file(
            session=session,
            file_id=file_id,
        )
        if not db_record_deleted:
            raise FileNotFoundError(
                f"File record with ID {file_id} was not found."
            )
    except Exception:
        restore_staged_files(staged_deletions)
        raise

    session.info.setdefault(PENDING_FILE_DELETIONS_KEY, []).extend(
        staged_deletions
    )
    staged_original_paths = {
        deletion.original_path
        for deletion in staged_deletions
    }

    return {
        "file_id": file_id,
        "original_name": original_name,
        "database_deleted": db_record_deleted,
        "storage_deleted": storage_path in staged_original_paths,
        "report_files_deleted": sum(
            Path(report_path).resolve() in staged_original_paths
            for report_path in report_paths
        ),
        "physical_file_was_missing": not physical_file_existed,
    }
