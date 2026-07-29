from datetime import datetime
from pathlib import Path
import logging
from sqlalchemy.orm import Session

from dataclasses import dataclass

from backend.services import storage_service
from backend.utils.validators import validate_file_extension
from backend.utils.constants import ORGANIZER_CATEGORY_RULES, DEFAULT_ORGANIZER_CATEGORY
from backend.config.settings import time_now, DATA_ROOT
from backend.database.repositories import update_file_location, create_automation_log

logger = logging.getLogger(__name__)

@dataclass
class OrganizationResult:
    file_id: int
    category: str
    source_path: Path
    destination_path: Path
    status: str

def detect_file_category(filename: str) -> str:
    extension = validate_file_extension(filename)

    for filecategory in ORGANIZER_CATEGORY_RULES.keys():
        if extension in ORGANIZER_CATEGORY_RULES.get(filecategory):
            return filecategory
    return DEFAULT_ORGANIZER_CATEGORY

def build_destination_directory(
    category: str,
    date_value: datetime | None = None,
) -> Path:
    if date_value is None:
        date_value = time_now()

    allowed_categories = set(ORGANIZER_CATEGORY_RULES.keys()) | {DEFAULT_ORGANIZER_CATEGORY}
    if category not in allowed_categories:
        raise ValueError("The file category is unsupported")

    year = date_value.strftime("%Y")
    month = date_value.strftime("%m")

    return DATA_ROOT / "processed" / category / year / month
    


def organize_uploaded_file(
    session: Session,
    file_id: int, 
    source_path: Path
) -> OrganizationResult:
    source_path = Path(source_path)
    file_category = detect_file_category(source_path.name)
    destination_dir = build_destination_directory(file_category)
    destination_path = destination_dir / source_path.name
    moved_path: Path | None = None

    try:
        moved_path = storage_service.move_file(source_path, destination_path)
        with session.begin_nested():
            updated_file_record = update_file_location(
                session=session,
                file_id = file_id,
                new_path = moved_path,
                category = file_category,
                status = "organized",
            )

            if updated_file_record is None:
                raise FileNotFoundError(
                    f"File record with ID {file_id} was not found."
                )
            create_automation_log(
                session = session,
                action = "organize_file",
                target = f"file:{file_id}:{source_path.name}",
                status = "success",
                message=(f"File organized into '{file_category}' at '{moved_path}'.")
            )
        return OrganizationResult(
            file_id=file_id,
            category=file_category,
            source_path=source_path,
            destination_path=Path(updated_file_record.storage_path),
            status=updated_file_record.status,
        )

    except Exception as error:
        failure_path = source_path
        if moved_path is not None and moved_path.exists() and not source_path.exists():
            try:
                storage_service.move_file(
                    moved_path,
                    source_path,
                )
            except Exception:
                failure_path = moved_path
                logger.exception(
                    'Could not restore file "%s" after organization failed.',
                    source_path.name,
                )

        try:
            with session.begin_nested():
                update_file_location(
                    session=session,
                    file_id=file_id,
                    new_path=failure_path,
                    category=file_category,
                    status="failed",
                )
                create_automation_log(
                    session=session,
                    action="organize_file",
                    target=f"file:{file_id}:{source_path.name}",
                    status="failed",
                    message=str(error),
                )
        except Exception:
            logger.exception(
                "Could not save the organization failure state."
            )

        logger.exception(
            'Failed to organize file "%s".',
            source_path.name,
        )

        raise
    
