
import pytest

from backend.services.storage_service import (
    finalize_staged_files,
    initialize_storage,
    move_file,
    resolve_storage_path,
    restore_staged_files,
    stage_files_for_deletion,
)
from backend.utils.constants import STORAGE_DIRECTORIES


def test_initialize_storage_creates_all_required_directories(
    temporary_data_root,
):
    created_directories = initialize_storage()

    assert created_directories is not None
    assert set(created_directories) == {
        (temporary_data_root / directory).resolve()
        for directory in STORAGE_DIRECTORIES
    }
    assert all(path.is_dir() for path in created_directories)


def test_resolve_storage_path_rejects_paths_outside_data_root(
    temporary_data_root,
):
    with pytest.raises(ValueError, match="not related to data root"):
        resolve_storage_path("../outside.txt")


#Test move_file()
def test_move_file_moves_source_to_destination(temporary_data_root):
    source = temporary_data_root / "uploads" / "report.csv"
    destination = (
        temporary_data_root
        / "processed"
        / "spreadsheets"
        / "report.csv"
    )

    source.parent.mkdir(parents=True)
    source.write_text("name,score\nMenura,90")

    moved_path = move_file(source, destination)

    assert moved_path == destination
    assert not source.exists()
    assert destination.exists()
    assert destination.read_text() == "name,score\nMenura,90"

def test_move_file_rejects_duplicate_destination(temporary_data_root):
    source = temporary_data_root / "uploads" / "report.csv"
    destination = (
        temporary_data_root
        / "processed"
        / "spreadsheets"
        / "report.csv"
    )

    source.parent.mkdir(parents=True)
    destination.parent.mkdir(parents=True)

    source.write_text("new content")
    destination.write_text("existing content")

    with pytest.raises(FileExistsError):
        move_file(source, destination)

    assert source.exists()
    assert destination.exists()
    assert destination.read_text() == "existing content"


def test_move_file_rejects_source_and_destination_outside_data_root(
    temporary_data_root,
    tmp_path,
):
    managed_source = temporary_data_root / "uploads" / "report.csv"
    managed_source.parent.mkdir(parents=True)
    managed_source.write_text("content")
    outside_source = tmp_path / "outside.csv"
    outside_source.write_text("outside")
    managed_destination = temporary_data_root / "processed" / "report.csv"
    outside_destination = tmp_path / "outside-destination.csv"

    with pytest.raises(ValueError, match="not related to data root"):
        move_file(outside_source, managed_destination)

    with pytest.raises(ValueError, match="not related to data root"):
        move_file(managed_source, outside_destination)

    assert outside_source.is_file()
    assert managed_source.is_file()


def test_stage_files_for_deletion_can_restore_files(temporary_data_root):
    source = temporary_data_root / "uploads" / "report.csv"
    source.parent.mkdir(parents=True)
    source.write_text("content")

    staged = stage_files_for_deletion([source])

    assert not source.exists()
    assert staged[0].staged_path.is_file()

    restore_staged_files(staged)

    assert source.read_text() == "content"
    assert not (temporary_data_root / ".trash").exists()


def test_stage_files_for_deletion_can_finalize_files(temporary_data_root):
    source = temporary_data_root / "reports" / "report.txt"
    source.parent.mkdir(parents=True)
    source.write_text("content")

    staged = stage_files_for_deletion([source])
    finalize_staged_files(staged)

    assert not source.exists()
    assert not (temporary_data_root / ".trash").exists()


def test_stage_files_for_deletion_validates_all_paths_before_moving(
    temporary_data_root,
    tmp_path,
):
    source = temporary_data_root / "uploads" / "report.csv"
    source.parent.mkdir(parents=True)
    source.write_text("content")
    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("outside")

    with pytest.raises(ValueError, match="not related to data root"):
        stage_files_for_deletion([source, outside_file])

    assert source.is_file()
    assert outside_file.is_file()


