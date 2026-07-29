from datetime import datetime, timezone
from pathlib import Path
import shutil
import sqlite3
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))


ANALYSIS_JOBS_DDL = """
CREATE TABLE analysis_jobs (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL,
    status VARCHAR(30) NOT NULL,
    requested_options TEXT,
    summary TEXT,
    error_message TEXT,
    created_at DATETIME NOT NULL,
    completed_at DATETIME,
    FOREIGN KEY(file_id) REFERENCES files (id) ON DELETE CASCADE
)
"""

REPORTS_DDL = """
CREATE TABLE reports (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL,
    analysis_job_id INTEGER NOT NULL,
    report_type VARCHAR(30) NOT NULL,
    storage_path VARCHAR(500) NOT NULL UNIQUE,
    status VARCHAR(30) NOT NULL,
    created_at DATETIME NOT NULL,
    FOREIGN KEY(file_id) REFERENCES files (id) ON DELETE CASCADE,
    FOREIGN KEY(analysis_job_id) REFERENCES analysis_jobs (id)
        ON DELETE CASCADE
)
"""


def _table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    return connection.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
        """,
        (table_name,),
    ).fetchone() is not None


def _has_current_cascade_schema(connection: sqlite3.Connection) -> bool:
    if not _table_exists(connection, "analysis_jobs"):
        return False
    if not _table_exists(connection, "reports"):
        return False

    analysis_foreign_keys = connection.execute(
        "PRAGMA foreign_key_list(analysis_jobs)"
    ).fetchall()
    report_foreign_keys = connection.execute(
        "PRAGMA foreign_key_list(reports)"
    ).fetchall()
    report_columns = {
        row[1]: row
        for row in connection.execute("PRAGMA table_info(reports)").fetchall()
    }

    return (
        len(analysis_foreign_keys) == 1
        and analysis_foreign_keys[0][6].upper() == "CASCADE"
        and len(report_foreign_keys) == 2
        and all(row[6].upper() == "CASCADE" for row in report_foreign_keys)
        and report_columns["file_id"][3] == 1
        and report_columns["analysis_job_id"][3] == 1
    )


def _rebuild_analysis_tables(connection: sqlite3.Connection) -> bool:
    if _has_current_cascade_schema(connection):
        return False

    analysis_rows = []
    report_rows = []
    if _table_exists(connection, "analysis_jobs"):
        analysis_rows = connection.execute(
            "SELECT * FROM analysis_jobs ORDER BY id"
        ).fetchall()
    if _table_exists(connection, "reports"):
        report_rows = connection.execute(
            "SELECT * FROM reports ORDER BY id"
        ).fetchall()

    if any(row["file_id"] is None for row in analysis_rows):
        raise ValueError("Cannot migrate an analysis job without a file ID.")
    if any(
        row["file_id"] is None or row["analysis_job_id"] is None
        for row in report_rows
    ):
        raise ValueError("Cannot migrate a report with a missing foreign key.")

    connection.execute("PRAGMA foreign_keys=OFF")
    connection.execute("BEGIN IMMEDIATE")
    try:
        connection.execute("DROP TABLE IF EXISTS reports")
        connection.execute("DROP TABLE IF EXISTS analysis_jobs")
        connection.execute(ANALYSIS_JOBS_DDL)
        connection.execute(REPORTS_DDL)

        if analysis_rows:
            connection.executemany(
                """
                INSERT INTO analysis_jobs (
                    id, file_id, status, requested_options, summary,
                    error_message, created_at, completed_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [tuple(row) for row in analysis_rows],
            )
        if report_rows:
            connection.executemany(
                """
                INSERT INTO reports (
                    id, file_id, analysis_job_id, report_type,
                    storage_path, status, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [tuple(row) for row in report_rows],
            )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.execute("PRAGMA foreign_keys=ON")

    return True


def migrate_database(
    database_path: Path,
    project_root: Path,
    backup_directory: Path,
) -> dict[str, object]:
    database_path = database_path.resolve()
    project_root = project_root.resolve()
    backup_directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    backup_path = backup_directory / (
        f"{database_path.stem}.on_{timestamp}{database_path.suffix}"
    )
    shutil.copy2(database_path, backup_path)

    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    try:
        schema_rebuilt = _rebuild_analysis_tables(connection)

        stale_file_ids = []
        for row in connection.execute(
            "SELECT id, storage_path FROM files ORDER BY id"
        ).fetchall():
            storage_path = Path(row["storage_path"])
            if not storage_path.is_absolute():
                storage_path = project_root / storage_path
            if not storage_path.is_file():
                stale_file_ids.append(row["id"])

        if stale_file_ids:
            placeholders = ", ".join("?" for _ in stale_file_ids)
            connection.execute(
                f"DELETE FROM files WHERE id IN ({placeholders})",
                stale_file_ids,
            )

        normalized_logs = connection.execute(
            """
            UPDATE automation_logs
            SET status = 'failed'
            WHERE status = 'failure'
            """
        ).rowcount
        connection.commit()

        foreign_key_errors = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()
        integrity_result = connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]
        if foreign_key_errors or integrity_result != "ok":
            raise RuntimeError("Database validation failed after migration.")
    finally:
        connection.close()

    return {
        "backup_path": backup_path,
        "schema_rebuilt": schema_rebuilt,
        "stale_file_ids_removed": stale_file_ids,
        "automation_logs_normalized": normalized_logs,
    }


def organize_remaining_uploads() -> list[int]:
    from sqlalchemy import select

    from backend.database.db import get_db_session
    from backend.database.models import FileRecord
    from backend.services.automation_service import organize_uploaded_file

    organized_file_ids = []
    with get_db_session() as session:
        records = session.scalars(
            select(FileRecord)
            .where(FileRecord.status == "uploaded")
            .order_by(FileRecord.id)
        ).all()
        for record in records:
            source_path = Path(record.storage_path)
            if source_path.is_file():
                organize_uploaded_file(
                    session=session,
                    file_id=record.id,
                    source_path=source_path,
                )
                organized_file_ids.append(record.id)
    return organized_file_ids


def main() -> None:
    from backend.config.settings import DATA_ROOT
    from backend.database.db import engine

    database_path = Path(engine.url.database or "")
    if not database_path.is_absolute():
        database_path = PROJECT_ROOT / database_path

    engine.dispose()
    result = migrate_database(
        database_path=database_path,
        project_root=PROJECT_ROOT,
        backup_directory=DATA_ROOT / "backups",
    )
    result["organized_file_ids"] = organize_remaining_uploads()

    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
