from pathlib import Path

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from backend.config.settings import time_now
from backend.database.models import AnalysisJob, AutomationLog, FileRecord, Report

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
    file_record_list = session.scalars(
        select(FileRecord).order_by(
            FileRecord.created_at.desc(),
            FileRecord.id.desc(),
        )
    ).all()
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
         

def update_file_location(
    session: Session,
    file_id: int,
    new_path: Path | str,
    category: str,
    status: str = "organized",
) -> FileRecord | None: 
    file_record = session.get(FileRecord, file_id)

    if file_record is None:
        return None

    file_record.storage_path = str(new_path)
    file_record.status = status
    file_record.category = category

    session.flush()
    session.refresh(file_record)

    return file_record
    
    

def create_automation_log(
    session: Session,
    action: str,
    target: str,
    status: str,
    message: str,
) -> AutomationLog:
    log_record = AutomationLog(
        action=action,
        target=target,
        status=status,
        message=message,
    )

    session.add(log_record)
    session.flush()
    session.refresh(log_record)

    return log_record



def _normalize_filter_values(
    values: str | list[str] | None,
) -> list[str]:
    if values is None:
        return []

    if isinstance(values, str):
        values = [values]

    return [
        value.strip()
        for value in values
        if value and value.strip()
    ]


def _escape_like_pattern(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )


def search_files(
    session: Session,
    search_term: str,
) -> list[FileRecord]:
    return query_files(
        session=session,
        search_term=search_term,
    )


def filter_files_by_category(
    session: Session,
    category: str,
) -> list[FileRecord]:
    return query_files(
        session=session,
        category=category,
    )


def filter_files_by_status(
    session: Session,
    status: str,
) -> list[FileRecord]:
    return query_files(
        session=session,
        status=status,
    )


def query_files(
    session: Session,
    search_term: str | None = None,
    category: str | list[str] | None = None,
    status: str | list[str] | None = None,
) -> list[FileRecord]:
    query = select(FileRecord)
    category_values = _normalize_filter_values(category)
    status_values = _normalize_filter_values(status)

    cleaned_search_term = search_term.strip() if search_term else ""
    if cleaned_search_term:
        search_pattern = f"%{_escape_like_pattern(cleaned_search_term)}%"
        query = query.where(
            or_(
                FileRecord.original_name.ilike(search_pattern, escape="\\"),
                FileRecord.stored_name.ilike(search_pattern, escape="\\"),
            )
        )

    if category_values:
        query = query.where(FileRecord.category.in_(category_values))

    if status_values:
        query = query.where(FileRecord.status.in_(status_values))

    return session.scalars(
        query.order_by(
            FileRecord.updated_at.desc(),
            FileRecord.id.desc(),
        )
    ).all()


def get_report_storage_paths(
    session: Session,
    file_id: int,
) -> list[Path]:
    return [
        Path(storage_path)
        for storage_path in session.scalars(
            select(Report.storage_path).where(Report.file_id == file_id)
        ).all()
    ]


def count_files(
    session: Session,
) -> int:
    return session.scalar(select(func.count(FileRecord.id))) or 0

def get_file_summary(
    session: Session,
) -> dict[str, int]:
    total_files = count_files(session)
    total_size_bytes = session.scalar(
        select(
            func.coalesce(
                func.sum(FileRecord.size_bytes),
                0,
            )
        )
    ) or 0

    return {
        "total_files": total_files,
        "total_size_bytes": total_size_bytes,
    }


def group_files_by_category(
    session: Session,
) -> list[dict]:
    results = session.execute(
        select(
            FileRecord.category,
            func.count(FileRecord.id).label("file_count"),
            func.coalesce(
                func.sum(FileRecord.size_bytes),
                0,
            ).label("total_size_bytes"),
        )
        .group_by(FileRecord.category)
        .order_by(
            func.count(FileRecord.id).desc(),
            FileRecord.category.asc(),
        )
    ).all()

    return [
        {
            "category": result.category,
            "file_count": result.file_count,
            "total_size_bytes": result.total_size_bytes,
        }
        for result in results
    ]

def group_files_by_status(
    session: Session,
) -> list[dict]:
    results = session.execute(
        select(
            FileRecord.status,
            func.count(FileRecord.id).label("file_count"),
        )
        .group_by(FileRecord.status)
        .order_by(FileRecord.status.asc())
    ).all()

    return [
        {
            "status": result.status,
            "file_count": result.file_count,
        }
        for result in results
    ]


def get_recent_files(
    session: Session,
    limit: int = 5,
) -> list[FileRecord]:
    recent_files = session.scalars(
        select(FileRecord).order_by(
            FileRecord.updated_at.desc(),
            FileRecord.id.desc()
        ).limit(limit)
    ).all()

    return recent_files


def get_analysis_job_by_id(
    session: Session,
    job_id: int,
) -> AnalysisJob | None:
    return session.get(AnalysisJob, job_id)


def create_analysis_job(
    session: Session,
    file_id: int,
    requested_options: str | None = None,
    status: str = "running",
) -> AnalysisJob:
    analysis_record = AnalysisJob(
        file_id=file_id,
        status=status,
        requested_options=requested_options,
    )
    
    session.add(analysis_record)
    session.flush()
    session.refresh(analysis_record)
    
    return analysis_record


def update_analysis_job(
    session: Session,
    job_id: int,
    *,
    status: str,
    summary: str | None = None,
    error_message: str | None = None,
) -> AnalysisJob:
    analysis_job = get_analysis_job_by_id(session,job_id)

    if analysis_job is None:
        raise ValueError(
            f"Analysis job with ID {job_id} was not found."
        )

    analysis_job.status = status
    analysis_job.summary = summary
    analysis_job.error_message = error_message

    if status in {"completed", "failed"}:
        analysis_job.completed_at = time_now()

    session.flush()

    return analysis_job
