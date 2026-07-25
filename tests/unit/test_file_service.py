import pytest
from pathlib import Path
from types import SimpleNamespace

import backend.services.file_service as file_service
from backend.services.file_service import (
    validate_upload,
    upload_file
)


def test_validate_upload():
    valid_result = validate_upload("report.csv", 5)
    assert valid_result is None

    with pytest.raises(ValueError):
        validate_upload("report.csv", 0)

    with pytest.raises(ValueError):
        validate_upload(" ", 5)
    
    with pytest.raises(ValueError):
        validate_upload("report.exe", 5)

    with pytest.raises(ValueError):
        validate_upload("report.pdf", 0)


def test_successful_upload_file(monkeypatch):
    fake_saved_path = Path("data/uploads/report_12345678.csv")
    fake_session = SimpleNamespace(rollback=lambda: None)
    file_bytes = b"name,score\nMenura,90\n"

    def fake_generate_safe_filename(filename):
        return "report_12345678.csv"

    def fake_save_uploaded_bytes(stored_filename, received_file_bytes):
        assert stored_filename == "report_12345678.csv"
        assert received_file_bytes == file_bytes
        return fake_saved_path

    def fake_create_file(
        session,
        original_name,
        stored_name,
        extension,
        category,
        size_bytes,
        storage_path,
    ):
        assert session is fake_session
        assert original_name == "report.csv"
        assert stored_name == "report_12345678.csv"
        assert extension == "csv"
        assert category == "spreadsheet"
        assert size_bytes == len(file_bytes)
        assert storage_path == str(fake_saved_path)
        return SimpleNamespace(id=42, status="uploaded")

    monkeypatch.setattr(
        file_service,
        "generate_safe_filename",
        fake_generate_safe_filename,
    )
    monkeypatch.setattr(
        file_service,
        "save_uploaded_bytes",
        fake_save_uploaded_bytes,
    )
    monkeypatch.setattr(
        file_service,
        "create_file",
        fake_create_file,
    )

    result = upload_file("report.csv", file_bytes, fake_session)

    assert result.file_id == 42
    assert result.original_filename == "report.csv"
    assert result.stored_filename == "report_12345678.csv"
    assert result.extension == "csv"
    assert result.size_bytes == len(file_bytes)
    assert result.saved_path == str(fake_saved_path)
    assert result.status == "uploaded"


def test_upload_file_retries_when_stored_filename_exists(monkeypatch):
    fake_session = SimpleNamespace(rollback=lambda: None)
    file_bytes = b"name,score\nAsha,95\n"

    generated_names = [
        "report_first.csv",
        "report_second.csv",
    ]
    generate_calls = []
    save_calls = []

    def fake_generate_safe_filename(filename):
        generate_calls.append(filename)
        return generated_names[len(generate_calls) - 1]

    def fake_save_uploaded_bytes(stored_filename, received_file_bytes):
        save_calls.append(stored_filename)

        if len(save_calls) == 1:
            raise FileExistsError("File already exists")

        return Path(f"data/uploads/{stored_filename}")

    def fake_create_file(
        session,
        original_name,
        stored_name,
        extension,
        category,
        size_bytes,
        storage_path,
    ):
        assert stored_name == "report_second.csv"
        return SimpleNamespace(id=42, status="uploaded")

    monkeypatch.setattr(
        file_service,
        "generate_safe_filename",
        fake_generate_safe_filename,
    )
    monkeypatch.setattr(
        file_service,
        "save_uploaded_bytes",
        fake_save_uploaded_bytes,
    )
    monkeypatch.setattr(
        file_service,
        "create_file",
        fake_create_file,
    )

    result = upload_file("report.csv", file_bytes, fake_session)

    assert result.stored_filename == "report_second.csv"
    assert Path(result.saved_path) == Path("data/uploads/report_second.csv")

    assert len(generate_calls) == 2
    assert save_calls == ["report_first.csv", "report_second.csv"]
    assert result.status == "uploaded"


def test_upload_file_stops_after_retry_limit(monkeypatch):
    fake_session = SimpleNamespace(rollback=lambda: None)
    generate_calls = []
    save_calls = []
    create_calls = []

    def fake_generate_safe_filename(filename):
        generate_calls.append(filename)
        return f"report_{len(generate_calls)}.csv"

    def fake_save_uploaded_bytes(stored_filename, file_bytes):
        save_calls.append(stored_filename)
        raise FileExistsError("File already exists")

    def fake_create_file(*args, **kwargs):
        create_calls.append((args, kwargs))

    monkeypatch.setattr(file_service, "MAX_FILENAME_ATTEMPTS", 3)
    monkeypatch.setattr(file_service, "generate_safe_filename", fake_generate_safe_filename)
    monkeypatch.setattr(file_service, "save_uploaded_bytes", fake_save_uploaded_bytes)
    monkeypatch.setattr(file_service, "create_file", fake_create_file)

    with pytest.raises(FileExistsError):
        upload_file("report.csv", b"name,score\nAsha,95\n", fake_session)

    assert len(generate_calls) == 3
    assert len(save_calls) == 3
    assert create_calls == []


def test_upload_file_propagates_storage_failure_without_create_or_cleanup(monkeypatch):
    fake_session = SimpleNamespace(rollback=lambda: None)
    create_calls = []
    cleanup_calls = []

    def fake_save_uploaded_bytes(stored_filename, file_bytes):
        raise OSError("Disk is unavailable")

    def fake_create_file(*args, **kwargs):
        create_calls.append((args, kwargs))

    def fake_delete_stored_file(path):
        cleanup_calls.append(path)

    monkeypatch.setattr(file_service, "generate_safe_filename", lambda filename: "report_12345678.csv")
    monkeypatch.setattr(file_service, "save_uploaded_bytes", fake_save_uploaded_bytes)
    monkeypatch.setattr(file_service, "create_file", fake_create_file)
    monkeypatch.setattr(file_service, "delete_stored_file", fake_delete_stored_file)

    with pytest.raises(OSError, match="Disk is unavailable"):
        upload_file("report.csv", b"name,score\nAsha,95\n", fake_session)

    assert create_calls == []
    assert cleanup_calls == []


def test_upload_file_deletes_saved_file_when_database_create_fails(monkeypatch):
    fake_session = SimpleNamespace(rollback=lambda: None)
    fake_saved_path = Path("data/uploads/report_12345678.csv")
    cleanup_calls = []

    def fake_create_file(*args, **kwargs):
        raise RuntimeError("Database insert failed")

    def fake_delete_stored_file(path):
        cleanup_calls.append(path)
        return True

    monkeypatch.setattr(file_service, "generate_safe_filename", lambda filename: "report_12345678.csv")
    monkeypatch.setattr(file_service, "save_uploaded_bytes", lambda stored_filename, file_bytes: fake_saved_path)
    monkeypatch.setattr(file_service, "create_file", fake_create_file)
    monkeypatch.setattr(file_service, "delete_stored_file", fake_delete_stored_file)

    with pytest.raises(RuntimeError, match="Database insert failed"):
        upload_file("report.csv", b"name,score\nAsha,95\n", fake_session)

    assert cleanup_calls == [fake_saved_path]


def test_upload_file_logs_cleanup_failure_and_reraises_database_error(monkeypatch, caplog):
    fake_session = SimpleNamespace(rollback=lambda: None)
    fake_saved_path = Path("data/uploads/report_12345678.csv")

    def fake_create_file(*args, **kwargs):
        raise RuntimeError("Database insert failed")

    def fake_delete_stored_file(path):
        raise OSError("Cleanup failed")

    monkeypatch.setattr(file_service, "generate_safe_filename", lambda filename: "report_12345678.csv")
    monkeypatch.setattr(file_service, "save_uploaded_bytes", lambda stored_filename, file_bytes: fake_saved_path)
    monkeypatch.setattr(file_service, "create_file", fake_create_file)
    monkeypatch.setattr(file_service, "delete_stored_file", fake_delete_stored_file)

    with caplog.at_level("ERROR", logger=file_service.logger.name):
        with pytest.raises(RuntimeError, match="Database insert failed"):
            upload_file("report.csv", b"name,score\nAsha,95\n", fake_session)

    assert "Failed to clean up partially uploaded file" in caplog.text
