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
from backend.services.storage_service import save_uploaded_bytes, delete_stored_file
from backend.utils.file_utils import generate_safe_filename
from backend.database.repositories import create_file
from backend.config.settings import MAX_FILENAME_ATTEMPTS

logger = logging.getLogger(__name__)


def validate_upload(filename: str, filesize_bytes: int) -> None:
    validate_filename(filename)
    validate_file_extension(filename)
    validate_file_size(filesize_bytes)
    

@dataclass
class FileUploadResult:
    file_id: int
    original_filename: str
    stored_filename: str
    extension: str
    size_bytes: int
    saved_path: str
    status: str

def upload_file(
    filename: str,
    file_bytes: bytes,
    session: Session,
) -> FileUploadResult:
    filesize_bytes = len(file_bytes)
    validate_upload(filename, filesize_bytes)
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


