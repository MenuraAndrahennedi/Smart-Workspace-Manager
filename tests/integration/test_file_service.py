from pathlib import Path

import pytest
from sqlalchemy import select

import backend.services.file_service as file_service
from backend.database.models import FileRecord
from backend.services.file_service import upload_file
from backend.services.storage_service import initialize_storage


def test_upload_file_creates_storage_file_and_database_record(
    temporary_data_root,
    test_session,
):
    initialize_storage()
    file_bytes = b"name,age\nMenura,22\n"

    result = upload_file(
        filename="student_data.csv",
        file_bytes=file_bytes,
        session=test_session,
    )

    saved_path = Path(result.saved_path)
    records = test_session.scalars(select(FileRecord)).all()

    assert saved_path.exists()
    assert saved_path.read_bytes() == file_bytes
    assert result.stored_filename != "student_data.csv"
    assert saved_path.suffix == ".csv"

    assert len(records) == 1
    assert records[0].original_name == "student_data.csv"
    assert records[0].stored_name == result.stored_filename
    assert records[0].size_bytes == len(file_bytes)
    assert records[0].storage_path == result.saved_path
    assert records[0].status == "uploaded"


def test_upload_file_allows_same_original_filename_twice(
    temporary_data_root,
    test_session,
):
    initialize_storage()

    first = upload_file("report.csv", b"name,score\nAsha,95\n", test_session)
    second = upload_file("report.csv", b"name,score\nNimal,88\n", test_session)

    records = test_session.scalars(select(FileRecord)).all()

    assert len(records) == 2
    assert records[0].original_name == "report.csv"
    assert records[1].original_name == "report.csv"
    assert first.stored_filename != second.stored_filename
    assert Path(first.saved_path).exists()
    assert Path(second.saved_path).exists()


def test_upload_file_rejects_invalid_extension_without_storage_or_database(
    temporary_data_root,
    test_session,
):
    initialize_storage()

    with pytest.raises(ValueError):
        upload_file("malware.exe", b"bad", test_session)

    records = test_session.scalars(select(FileRecord)).all()
    saved_files = list((temporary_data_root / "uploads").iterdir())

    assert records == []
    assert saved_files == []


def test_upload_file_cleans_up_real_saved_file_when_database_create_fails(
    temporary_data_root,
    test_session,
    monkeypatch,
):
    initialize_storage()
    saved_paths = []

    real_save_uploaded_bytes = file_service.save_uploaded_bytes

    def tracking_save_uploaded_bytes(stored_filename, file_bytes):
        saved_path = real_save_uploaded_bytes(stored_filename, file_bytes)
        saved_paths.append(saved_path)
        return saved_path

    def failing_create_file(*args, **kwargs):
        raise RuntimeError("Database insert failed")

    monkeypatch.setattr(file_service, "save_uploaded_bytes", tracking_save_uploaded_bytes)
    monkeypatch.setattr(file_service, "create_file", failing_create_file)

    with pytest.raises(RuntimeError, match="Database insert failed"):
        upload_file("student_data.csv", b"name,age\nMenura,22\n", test_session)

    records = test_session.scalars(select(FileRecord)).all()

    assert len(saved_paths) == 1
    assert not saved_paths[0].exists()
    assert records == []
