from sqlalchemy.orm import Session

from backend.database.repositories import get_file_summary, get_recent_files, group_files_by_category, group_files_by_status

def get_dashboard_data(
    session: Session,
    recent_limit: int = 5,
) -> dict:
    file_summary = get_file_summary(session)
    category_summary = group_files_by_category(session)
    status_summary = group_files_by_status(session)
    recent_files = get_recent_files(session, recent_limit)

    status_counts = {
        item["status"]: item["file_count"]
        for item in status_summary
    }

    recent_file_data = [
        {
            "id": file.id,
            "original_name": file.original_name,
            "stored_name": file.stored_name,
            "extension": file.extension,
            "category": file.category,
            "size_bytes": file.size_bytes,
            "status": file.status,
            "created_at": file.created_at,
            "updated_at": file.updated_at,
        }
        for file in recent_files
    ]

    return {
        "total_files": file_summary["total_files"],
        "total_size_bytes": file_summary["total_size_bytes"],
        "organized_files": status_counts.get("organized", 0),
        "failed_files": status_counts.get("failed", 0),
        "category_summary": category_summary,
        "recent_files": recent_file_data,
    }

