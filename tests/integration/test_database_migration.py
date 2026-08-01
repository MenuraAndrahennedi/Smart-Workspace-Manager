import sqlite3

from scripts.migrate_database import migrate_database


def test_day7_migration_rebuilds_schema_and_cleans_stale_rows(tmp_path):
    project_root = tmp_path / "project"
    data_root = project_root / "data"
    uploads = data_root / "uploads"
    uploads.mkdir(parents=True)
    database_path = data_root / "workspace.db"
    existing_file = uploads / "existing.csv"
    existing_file.write_text("name,score\nMenura,90")

    connection = sqlite3.connect(database_path)
    connection.executescript(
        """
        CREATE TABLE files (
            id INTEGER PRIMARY KEY,
            storage_path TEXT NOT NULL
        );
        CREATE TABLE analysis_jobs (
            id INTEGER PRIMARY KEY,
            file_id INTEGER,
            status TEXT NOT NULL,
            requested_options TEXT,
            summary TEXT,
            error_message TEXT,
            created_at TEXT NOT NULL,
            completed_at TEXT,
            FOREIGN KEY(file_id) REFERENCES files(id)
        );
        CREATE TABLE reports (
            id INTEGER PRIMARY KEY,
            file_id INTEGER,
            analysis_job_id INTEGER,
            report_type TEXT NOT NULL,
            storage_path TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(file_id) REFERENCES files(id),
            FOREIGN KEY(analysis_job_id) REFERENCES analysis_jobs(id)
        );
        CREATE TABLE automation_logs (
            id INTEGER PRIMARY KEY,
            status TEXT NOT NULL
        );
        """
    )
    connection.executemany(
        "INSERT INTO files (id, storage_path) VALUES (?, ?)",
        [
            (1, str(existing_file)),
            (2, str(uploads / "missing.csv")),
        ],
    )
    connection.execute(
        """
        INSERT INTO analysis_jobs (
            id, file_id, status, created_at
        )
        VALUES (1, 1, 'completed', CURRENT_TIMESTAMP)
        """
    )
    connection.execute(
        """
        INSERT INTO reports (
            id, file_id, analysis_job_id, report_type, storage_path,
            status, created_at
        )
        VALUES (
            1, 1, 1, 'summary', 'data/reports/summary.txt',
            'completed', CURRENT_TIMESTAMP
        )
        """
    )
    connection.execute(
        "INSERT INTO automation_logs (id, status) VALUES (1, 'failure')"
    )
    connection.commit()
    connection.close()

    result = migrate_database(
        database_path=database_path,
        project_root=project_root,
        backup_directory=data_root / "backups",
    )

    assert result["schema_rebuilt"] is True
    assert result["stale_file_ids_removed"] == [2]
    assert result["automation_logs_normalized"] == 1
    assert result["backup_path"].is_file()

    connection = sqlite3.connect(database_path)
    try:
        assert connection.execute(
            "SELECT id FROM files ORDER BY id"
        ).fetchall() == [(1,)]
        assert connection.execute(
            "SELECT status FROM automation_logs"
        ).fetchone() == ("failed",)
        assert {
            (row[2], row[6])
            for row in connection.execute(
                "PRAGMA foreign_key_list(reports)"
            ).fetchall()
        } == {("files", "CASCADE")}
        report_columns = {
            row[1]: row
            for row in connection.execute(
                "PRAGMA table_info(reports)"
            ).fetchall()
        }
        assert report_columns["file_id"][3] == 1
        assert "analysis_job_id" not in report_columns
        assert connection.execute(
            """
            SELECT id, file_id, report_type, storage_path, status
            FROM reports
            """
        ).fetchone() == (
            1,
            1,
            "summary",
            "data/reports/summary.txt",
            "completed",
        )
    finally:
        connection.close()
