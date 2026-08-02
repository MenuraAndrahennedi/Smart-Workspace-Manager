import pytest
from sqlalchemy import func, inspect, select
from sqlalchemy.orm import Session, sessionmaker

import backend.database.db as database_db
from backend.database.db import (
    Base,
    _finalize_pending_file_deletions,
    _restore_pending_file_deletions,
)
from backend.database.models import AnalysisJob, FileRecord, Report
from backend.database.repositories import create_file
from backend.services.file_service import delete_actual_file


def test_test_database_enables_sqlite_foreign_keys(test_engine) -> None:
    with test_engine.connect() as connection:
        foreign_keys_enabled = connection.exec_driver_sql(
            "PRAGMA foreign_keys"
        ).scalar_one()

    assert foreign_keys_enabled == 1


def test_database_initialization_creates_all_model_tables(test_engine) -> None:
    assert set(inspect(test_engine).get_table_names()) == set(
        Base.metadata.tables
    )


def test_db_session_rolls_back_and_closes_after_failure(
    test_engine,
    monkeypatch,
) -> None:
    sessions = []

    class TrackingSession(Session):
        was_closed = False

        def close(self) -> None:
            self.was_closed = True
            super().close()

    def create_tracking_session():
        session = TrackingSession(bind=test_engine)
        sessions.append(session)
        return session

    monkeypatch.setattr(database_db, "SessionLocal", create_tracking_session)

    with pytest.raises(RuntimeError, match="force rollback"):
        with database_db.get_db_session() as session:
            create_file(
                session=session,
                original_name="rollback.csv",
                stored_name="rollback.csv",
                extension="csv",
                category="spreadsheets",
                size_bytes=10,
                storage_path="uploads/rollback.csv",
            )
            raise RuntimeError("force rollback")

    assert sessions[0].was_closed is True
    with Session(test_engine) as check_session:
        assert check_session.scalar(
            select(func.count()).select_from(FileRecord)
        ) == 0


def test_delete_actual_file_cascades_analysis_jobs_and_reports(
    temporary_data_root,
    test_session,
) -> None:
    stored_file = temporary_data_root / "uploads" / "sales.csv"
    stored_file.parent.mkdir(parents=True)
    stored_file.write_text("name,score\nMenura,90")

    file_record = create_file(
        session=test_session,
        original_name="sales.csv",
        stored_name="stored_sales.csv",
        extension="csv",
        category="spreadsheets",
        size_bytes=stored_file.stat().st_size,
        storage_path=str(stored_file),
        status="organized",
    )

    analysis_job = AnalysisJob(
        file_id=file_record.id,
        status="completed",
    )
    test_session.add(analysis_job)
    test_session.flush()

    report = Report(
        file_id=file_record.id,
        report_type="summary",
        storage_path=str(temporary_data_root / "reports" / "sales_summary.txt"),
        status="completed",
    )
    report_file = temporary_data_root / "reports" / "sales_summary.txt"
    report_file.parent.mkdir(parents=True)
    report_file.write_text("Sales summary")
    test_session.add(report)
    test_session.flush()
    test_session.commit()

    result = delete_actual_file(
        session=test_session,
        file_id=file_record.id,
    )

    assert result["database_deleted"] is True
    assert result["storage_deleted"] is True
    assert result["report_files_deleted"] == 1
    assert not stored_file.exists()
    assert not report_file.exists()
    assert test_session.scalar(
        select(func.count()).select_from(FileRecord)
    ) == 0
    assert test_session.scalar(
        select(func.count()).select_from(AnalysisJob)
    ) == 0
    assert test_session.scalar(
        select(func.count()).select_from(Report)
    ) == 0

    test_session.commit()
    _finalize_pending_file_deletions(test_session)
    assert not (temporary_data_root / ".trash").exists()


def test_delete_actual_file_restores_files_and_records_after_rollback(
    temporary_data_root,
    test_session,
) -> None:
    stored_file = temporary_data_root / "uploads" / "sales.csv"
    stored_file.parent.mkdir(parents=True)
    stored_file.write_text("name,score\nMenura,90")
    report_file = temporary_data_root / "reports" / "sales_summary.txt"
    report_file.parent.mkdir(parents=True)
    report_file.write_text("Sales summary")

    file_record = create_file(
        session=test_session,
        original_name="sales.csv",
        stored_name="stored_sales.csv",
        extension="csv",
        category="spreadsheets",
        size_bytes=stored_file.stat().st_size,
        storage_path=str(stored_file),
        status="organized",
    )
    analysis_job = AnalysisJob(file_id=file_record.id, status="completed")
    test_session.add(analysis_job)
    test_session.flush()
    test_session.add(
        Report(
            file_id=file_record.id,
            report_type="summary",
            storage_path=str(report_file),
            status="completed",
        )
    )
    test_session.commit()

    delete_actual_file(test_session, file_record.id)
    test_session.rollback()
    _restore_pending_file_deletions(test_session)

    assert stored_file.is_file()
    assert report_file.is_file()
    assert test_session.get(FileRecord, file_record.id) is not None
    assert test_session.scalar(
        select(func.count()).select_from(AnalysisJob)
    ) == 1
    assert test_session.scalar(
        select(func.count()).select_from(Report)
    ) == 1


def test_db_session_context_finalizes_staged_deletion_after_commit(
    temporary_data_root,
    test_engine,
    monkeypatch,
) -> None:
    testing_session = sessionmaker(
        bind=test_engine,
        autoflush=False,
        expire_on_commit=False,
    )
    stored_file = temporary_data_root / "uploads" / "sales.csv"
    stored_file.parent.mkdir(parents=True)
    stored_file.write_text("name,score\nMenura,90")

    with testing_session() as seed_session:
        file_record = create_file(
            session=seed_session,
            original_name="sales.csv",
            stored_name="stored_sales.csv",
            extension="csv",
            category="spreadsheets",
            size_bytes=stored_file.stat().st_size,
            storage_path=str(stored_file),
            status="organized",
        )
        file_id = file_record.id
        seed_session.commit()

    monkeypatch.setattr(database_db, "SessionLocal", testing_session)

    with database_db.get_db_session() as session:
        delete_actual_file(session, file_id)
        assert not stored_file.exists()
        assert (temporary_data_root / ".trash").is_dir()

    assert not (temporary_data_root / ".trash").exists()
    with testing_session() as check_session:
        assert check_session.get(FileRecord, file_id) is None
