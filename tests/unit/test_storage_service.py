
import pytest

from backend.services.storage_service import move_file


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


