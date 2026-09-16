from sqlalchemy import func, select

from backend.database.models import AnalysisJob, FileRecord, Report, User


def test_user_owns_files_and_file_owns_derived_records(test_session):
    user = User(
        email="model-owner@example.com",
        password_hash="test-only-hash",
    )
    file_record = FileRecord(
        owner=user,
        original_name="sales.csv",
        stored_name="ownership-sales.csv",
        extension="csv",
        category="spreadsheets",
        size_bytes=100,
        storage_path="processed/spreadsheets/ownership-sales.csv",
        status="organized",
    )
    analysis_job = AnalysisJob(file=file_record, status="completed")
    report = Report(
        file=file_record,
        report_type="html",
        storage_path="reports/html/ownership-report.html",
        status="completed",
    )
    test_session.add_all([user, file_record, analysis_job, report])
    test_session.flush()

    assert file_record.user_id == user.id
    assert file_record.owner is user
    assert analysis_job.file.owner is user
    assert report.file.owner is user
    assert user.created_at is not None


def test_deleting_user_cascades_to_owned_files_jobs_and_reports(test_session):
    user = User(
        email="delete-owner@example.com",
        password_hash="test-only-hash",
    )
    file_record = FileRecord(
        owner=user,
        original_name="delete.csv",
        stored_name="ownership-delete.csv",
        extension="csv",
        category="spreadsheets",
        size_bytes=100,
        storage_path="processed/spreadsheets/ownership-delete.csv",
        status="organized",
    )
    file_record.analysis_jobs.append(AnalysisJob(status="completed"))
    file_record.reports.append(
        Report(
            report_type="html",
            storage_path="reports/html/ownership-delete-report.html",
            status="completed",
        )
    )
    test_session.add(user)
    test_session.flush()

    test_session.delete(user)
    test_session.flush()
    test_session.expire_all()

    assert test_session.scalar(select(func.count(FileRecord.id))) == 0
    assert test_session.scalar(select(func.count(AnalysisJob.id))) == 0
    assert test_session.scalar(select(func.count(Report.id))) == 0
