# Checks path resolution, directory creation, and existence checks.

import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

from backend.utils.file_utils import (
    resolve_project_path,
    ensure_directory,
    get_or_create_path,
    resolve_data_path,
    file_exists,
    directory_exists,
    format_file_size,
    generate_safe_filename,
)

# Test resolve_project_path
def test_resolve_project_path_string():
    result = resolve_project_path("backend/utils") 
    assert result == PROJECT_ROOT / "backend" / "utils"

def test_resolve_project_path():
    path = Path("backend/utils")
    result = resolve_project_path(path) 
    assert result == PROJECT_ROOT / "backend" / "utils"


# Test ensure_directory & directory_exists
def test_ensure_directory(tmp_path):
    new_folder = tmp_path / "new_test_folder"
    # Test is new folder NOT exists
    assert directory_exists(new_folder) is False
    result = ensure_directory(new_folder)
    # Test is new folder created
    assert directory_exists(new_folder) is True
    # Test new folder's path
    assert result == new_folder.resolve()


# Test get_or_create_path
def test_get_or_create_path(tmp_path):
    new_folder = tmp_path / "new_test_folder"
    result = get_or_create_path(new_folder)
    assert result == new_folder.resolve()

    existing_folder = tmp_path / "existing_folder"
    existing_folder.mkdir()
    result = get_or_create_path(existing_folder)
    assert result == existing_folder.resolve()


# Test resolve_data_path
def test_resolve_data_path(tmp_path):
    data_path = tmp_path / "data"
    data_path.mkdir()
    result = resolve_data_path(data_path, ["uploads", "report.csv"])
    expected = data_path / "uploads" / "report.csv"
    assert result == expected.resolve()


# Test file_exists & directory_exists
def test_file_exists_and_directory_exists(tmp_path):
    new_existing_folder = tmp_path / "existing_folder"
    new_existing_folder.mkdir()
    new_file = new_existing_folder / "new_test_file.txt"
    new_file.write_text("hello")

    assert file_exists(new_file) is True
    assert directory_exists(new_existing_folder) is True


def test_generate_safe_filename_stays_within_filesystem_limit():
    original_name = f"{'a' * 251}.csv"

    stored_name = generate_safe_filename(original_name)

    assert len(stored_name) <= 255
    assert stored_name.endswith(".csv")


@pytest.mark.parametrize(
    ("size_bytes", "expected"),
    [
        (0, "0 bytes"),
        (512, "512 bytes"),
        (1024, "1.00 KB"),
        (1024**2, "1.00 MB"),
        (1024**3, "1.00 GB"),
    ],
)
def test_format_file_size_uses_correct_unit(size_bytes, expected):
    assert format_file_size(size_bytes) == expected


def test_format_file_size_rejects_negative_values():
    with pytest.raises(ValueError, match="cannot be negative"):
        format_file_size(-1)

