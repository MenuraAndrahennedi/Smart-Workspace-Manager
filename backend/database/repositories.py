from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from backend.database.models import FileRecord


def create_file(
    session: Session,
    original_name: str,
    stored_name: str,
    extension: str,
    category: str,
    size_bytes: int,
    storage_path: str,
    status: str = "uploaded",
) -> FileRecord:
    
    file_record = FileRecord()

    file_record.original_name = original_name
    file_record.stored_name = stored_name
    file_record.extension = extension
    file_record.category = category
    file_record.size_bytes = size_bytes
    file_record.storage_path = storage_path
    file_record.status = status

    session.add(file_record)
    session.flush() # Sends the INSERT to the DB
    session.refresh(file_record) # Reloads DB-generated/default values.

    return file_record


def read_file_by_id(
    session: Session,
    file_id: int
) -> FileRecord | None:
    file_record = session.get(FileRecord, file_id)
    return file_record


def get_all_files(
    session: Session
) -> list[FileRecord]:
    file_record_list = session.scalars(select(FileRecord).order_by(desc(FileRecord.created_at))).all()
    return file_record_list


def update_file(
    session: Session,
    file_id: int,
    stored_name: str,
    storage_path: str,
    category: str,
    status: str
) -> FileRecord | None:
    file_record = session.get(FileRecord, file_id)
    if file_record is None:
        return None
    else:
        if not file_record.stored_name == stored_name: 
            file_record.stored_name = stored_name
        if not file_record.storage_path == storage_path: 
            file_record.storage_path = storage_path 
        if not file_record.category == category: 
            file_record.category = category 
        if not file_record.status == status: 
            file_record.status = status

        session.flush() 
        session.refresh(file_record)
        return file_record


def delete_file(
    session: Session,
    file_id: int
) -> bool:
    file_record = session.get(FileRecord, file_id)
    if file_record is None:
        return False
    else:
        session.delete(file_record)
        session.flush() 
        return True
         



