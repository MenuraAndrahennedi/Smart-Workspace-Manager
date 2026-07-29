
import pytest

from backend.services.storage_service import (
    finalize_staged_files,
    move_file,
    restore_staged_files,
    stage_files_for_deletion,
)


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


