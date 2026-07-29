from pathlib import Path

import pytest
from sqlalchemy import select

from backend.database.models import AutomationLog
from backend.database.repositories import create_file, read_file_by_id
from backend.services import automation_service
from backend.services.automation_service import organize_uploaded_file


def create_uploaded_record(test_session, source: Path):
    return create_file(
        session=test_session,
        original_name=source.name,
        stored_name=source.name,
        extension=source.suffix.lstrip("."),
        category="spreadsheet",
        size_bytes=source.stat().st_size,
        storage_path=str(source),
        status="uploaded",
    )


def get_automation_logs(test_session) -> list[AutomationLog]:
    return test_session.scalars(
        select(AutomationLog).order_by(AutomationLog.id)
    ).all()


def test_organizer_restores_file_when_database_update_fails(
    temporary_data_root,
    test_session,
    monkeypatch,
):
    source = temporary_data_root / "uploads" / "report.csv"
    source.parent.mkdir(parents=True)
    source.write_text("sample data")
    file_record = create_uploaded_record(test_session, source)

    destination_dir = (
        temporary_data_root
        / "processed"
        / "spreadsheets"
        / "2026"
        / "07"
    )
    expected_destination = destination_dir / source.name
    real_update_file_location = automation_service.update_file_location

    def fail_organized_update(*args, **kwargs):
        if kwargs["status"] == "organized":
            raise RuntimeError("Simulated database failure")
        return real_update_file_location(*args, **kwargs)

    monkeypatch.setattr(
        automation_service,
        "build_destination_directory",
        lambda category: destination_dir,
    )
    monkeypatch.setattr(
        automation_service,
        "update_file_location",
        fail_organized_update,
    )

    with pytest.raises(RuntimeError, match="Simulated database failure"):
        organize_uploaded_file(
            session=test_session,
            file_id=file_record.id,
            source_path=source,
        )

    failed_record = read_file_by_id(test_session, file_record.id)
    assert failed_record is not None
    assert failed_record.storage_path == str(source)
    assert failed_record.category == "spreadsheets"
    assert failed_record.status == "failed"
    assert source.exists()
    assert not expected_destination.exists()

    logs = get_automation_logs(test_session)
    assert len(logs) == 1
    assert logs[0].status == "failed"
    assert "Simulated database failure" in logs[0].message


def test_organizer_restores_file_and_logs_invalid_id(
    temporary_data_root,
    test_session,
    monkeypatch,
):
    source = temporary_data_root / "uploads" / "report.csv"
    source.parent.mkdir(parents=True)
    source.write_text("sample data")

    destination_dir = (
        temporary_data_root
        / "processed"
        / "spreadsheets"
        / "2026"
        / "07"
    )
    expected_destination = destination_dir / source.name

    monkeypatch.setattr(
        automation_service,
        "build_destination_directory",
        lambda category: destination_dir,
    )

    with pytest.raises(
        FileNotFoundError,
        match="File record with ID 999 was not found",
    ):
        organize_uploaded_file(
            session=test_session,
            file_id=999,
            source_path=source,
        )

    assert source.exists()
    assert not expected_destination.exists()

    logs = get_automation_logs(test_session)
    assert len(logs) == 1
    assert logs[0].target == "file:999:report.csv"
    assert logs[0].status == "failed"
    assert "File record with ID 999 was not found" in logs[0].message


def test_organizer_logs_duplicate_destination_failure(
    temporary_data_root,
    test_session,
    monkeypatch,
):
    source = temporary_data_root / "uploads" / "report.csv"
    source.parent.mkdir(parents=True)
    source.write_text("new content")
    file_record = create_uploaded_record(test_session, source)

    destination_dir = (
        temporary_data_root
        / "processed"
        / "spreadsheets"
        / "2026"
        / "07"
    )
    destination_dir.mkdir(parents=True)
    existing_destination = destination_dir / source.name
    existing_destination.write_text("existing content")

    monkeypatch.setattr(
        automation_service,
        "build_destination_directory",
        lambda category: destination_dir,
    )

    with pytest.raises(FileExistsError):
        organize_uploaded_file(
            session=test_session,
            file_id=file_record.id,
            source_path=source,
        )

    failed_record = read_file_by_id(test_session, file_record.id)
    assert failed_record is not None
    assert failed_record.storage_path == str(source)
    assert failed_record.status == "failed"
    assert source.read_text() == "new content"
    assert existing_destination.read_text() == "existing content"

    logs = get_automation_logs(test_session)
    assert len(logs) == 1
    assert logs[0].target == f"file:{file_record.id}:report.csv"
    assert logs[0].status == "failed"
    assert "File already exists" in logs[0].message


def test_success_log_failure_rolls_back_location_before_failed_state_is_saved(
    temporary_data_root,
    test_session,
    monkeypatch,
):
    source = temporary_data_root / "uploads" / "report.csv"
    source.parent.mkdir(parents=True)
    source.write_text("sample data")
    file_record = create_uploaded_record(test_session, source)

    destination_dir = (
        temporary_data_root
        / "processed"
        / "spreadsheets"
        / "2026"
        / "07"
    )
    expected_destination = destination_dir / source.name
    real_create_automation_log = automation_service.create_automation_log

    def fail_success_log(*args, **kwargs):
        if kwargs["status"] == "success":
            raise RuntimeError("Simulated success log failure")
        return real_create_automation_log(*args, **kwargs)

    monkeypatch.setattr(
        automation_service,
        "build_destination_directory",
        lambda category: destination_dir,
    )
    monkeypatch.setattr(
        automation_service,
        "create_automation_log",
        fail_success_log,
    )

    with pytest.raises(RuntimeError, match="Simulated success log failure"):
        organize_uploaded_file(
            session=test_session,
            file_id=file_record.id,
            source_path=source,
        )

    failed_record = read_file_by_id(test_session, file_record.id)
    assert failed_record is not None
    assert failed_record.storage_path == str(source)
    assert failed_record.category == "spreadsheets"
    assert failed_record.status == "failed"
    assert source.exists()
    assert not expected_destination.exists()

    logs = get_automation_logs(test_session)
    assert len(logs) == 1
    assert logs[0].status == "failed"
    assert "Simulated success log failure" in logs[0].message
