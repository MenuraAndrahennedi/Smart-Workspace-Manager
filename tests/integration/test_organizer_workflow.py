import pytest
from types import SimpleNamespace

from backend.services import automation_service
from backend.services.automation_service import organize_uploaded_file

# Test organize_uploaded_file()
def test_organizer_restores_file_for_database_update_fails(temporary_data_root, monkeypatch):
    source = temporary_data_root / "uploads" / "report.csv"
    source.parent.mkdir(parents=True)
    source.write_text("sample data")

    destination_dir = temporary_data_root / "processed" / "spreadsheets" / "2026" / "07"
    expected_destination = destination_dir / source.name

    captured_log = {}
    
    # Force to fail
    def fake_update_file_location(*args, **kwargs): 
        raise RuntimeError("Simulated database failure")

    def fake_create_automation_log(
        session,
        action,
        target,
        status,
        message,
    ):
        captured_log["action"] = action
        captured_log["target"] = target
        captured_log["status"] = status
        captured_log["message"] = message

    monkeypatch.setattr(
        automation_service,
        "update_file_location",
        fake_update_file_location,
    )
    monkeypatch.setattr(
        automation_service,
        "build_destination_directory",
        lambda category: destination_dir,
    )

    monkeypatch.setattr(
        automation_service,
        "create_automation_log",
        fake_create_automation_log,
    )

    with pytest.raises(
        RuntimeError,
        match="Simulated database failure",
    ):
        organize_uploaded_file(
            session=SimpleNamespace(),
            file_id=1,
            source_path=source,
        )

    assert source.exists()
    assert not expected_destination.exists()

    assert captured_log["action"] == "organize_file"
    assert captured_log["status"] == "failed"
    assert "Simulated database failure" in captured_log["message"]

def test_organizer_restores_file_for_invalid_id(temporary_data_root, monkeypatch):
    source = temporary_data_root / "uploads" / "report.csv"
    source.parent.mkdir(parents=True)
    source.write_text("sample data")

    destination_dir = temporary_data_root / "processed" / "spreadsheets" / "2026" / "07"
    expected_destination = destination_dir / source.name

    captured_log = {}

    # Returns None when the file ID does not exist
    def fake_update_file_location(*args, **kwargs): 
        return None

    def fake_create_automation_log(
        session,
        action,
        target,
        status,
        message,
    ):
        captured_log["action"] = action
        captured_log["target"] = target
        captured_log["status"] = status
        captured_log["message"] = message

    monkeypatch.setattr(
        automation_service,
        "update_file_location",
        fake_update_file_location,
    )

    monkeypatch.setattr(
        automation_service,
        "build_destination_directory",
        lambda category: destination_dir,
    )

    monkeypatch.setattr(
        automation_service,
        "create_automation_log",
        fake_create_automation_log,
    )

    with pytest.raises(FileNotFoundError):
        organize_uploaded_file(
            session=SimpleNamespace(),
            file_id=999,
            source_path=source,
        )

    assert source.exists()
    assert not expected_destination.exists()

    assert captured_log["action"] == "organize_file"
    assert captured_log["status"] == "failed"
    assert "File record with ID 999 was not found." in captured_log["message"]

def test_organizer_logs_duplicate_destination_failure(temporary_data_root, monkeypatch):
    source = temporary_data_root / "uploads" / "report.csv"
    source.parent.mkdir(parents=True)
    source.write_text("new content")

    destination_dir = temporary_data_root / "processed" / "spreadsheets" / "2026" / "07"
    destination_dir.mkdir(parents=True)
    existing_destination = destination_dir / source.name
    existing_destination.write_text("existing content")

    captured_log = {}
    update_calls = []

    def fake_update_file_location(*args, **kwargs):
        update_calls.append((args, kwargs))

    def fake_create_automation_log(
        session,
        action,
        target,
        status,
        message,
    ):
        captured_log["action"] = action
        captured_log["target"] = target
        captured_log["status"] = status
        captured_log["message"] = message

    monkeypatch.setattr(
        automation_service,
        "build_destination_directory",
        lambda category: destination_dir,
    )
    monkeypatch.setattr(
        automation_service,
        "update_file_location",
        fake_update_file_location,
    )
    monkeypatch.setattr(
        automation_service,
        "create_automation_log",
        fake_create_automation_log,
    )

    with pytest.raises(FileExistsError):
        organize_uploaded_file(
            session=SimpleNamespace(),
            file_id=1,
            source_path=source,
        )

    assert source.exists()
    assert source.read_text() == "new content"
    assert existing_destination.exists()
    assert existing_destination.read_text() == "existing content"

    assert update_calls == []
    assert captured_log["action"] == "organize_file"
    assert captured_log["target"] == "file:1:report.csv"
    assert captured_log["status"] == "failed"
    assert "File already exists" in captured_log["message"]
