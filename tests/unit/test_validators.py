# Checks filename, extension, size, and category validation.

import pytest

from backend.utils.validators import (
    find_unsupported_files,
    get_file_category,
    get_file_extension,
    validate_file_extension,
    validate_file_size,
    validate_filename,
)

TEST_MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024


# Test validate_filename
def test_validate_filename_returns_stripped_filename():
    result = validate_filename("  report.csv  ")
    assert result == "report.csv"

def test_validate_filename_rejects_empty_filename():
    with pytest.raises(ValueError):
        validate_filename("   ")

def test_validate_filename_rejects_longer_filename():
    with pytest.raises(ValueError):
        validate_filename("a" *256 + ".pdf")


# Test get_file_extension
def test_get_file_extension_correctly():
    result = get_file_extension("report.csv")
    assert result == "csv"

def test_get_file_extension_reject_extension_absence():
    with pytest.raises(ValueError):
        get_file_extension("reportcsv")


# Test validate_file_extension
def test_validate_file_extension_accepts_supported_extension():
    result = validate_file_extension("report.pdf")
    assert result == "pdf"

def test_validate_file_extension_rejects_unsupported_extension():
    with pytest.raises(ValueError):
        validate_file_extension("installer.exe")


# Test validate_file_size
def test_validate_file_size_accepts_valid_size():
    result = validate_file_size(1024, TEST_MAX_FILE_SIZE_BYTES)
    assert result == 1024

def test_validate_file_size_rejects_oversized_file():
    oversized_file = TEST_MAX_FILE_SIZE_BYTES + 1
    with pytest.raises(ValueError):
        validate_file_size(oversized_file, TEST_MAX_FILE_SIZE_BYTES)

def test_validate_file_size_rejects_zerosized_file():
    with pytest.raises(ValueError):
        validate_file_size(0, TEST_MAX_FILE_SIZE_BYTES)

def test_validate_file_size_rejects_non_int_size():
    with pytest.raises(TypeError):
        validate_file_size("ten", TEST_MAX_FILE_SIZE_BYTES)


# Test get_file_category
def test_get_file_category_returns_spreadsheet_for_csv():
    result = get_file_category("sales.csv")
    assert result == "spreadsheets"

def test_get_file_category_returns_image_for_png():
    result = get_file_category("profile.png")
    assert result == "images"

def test_get_file_category_rejects_unsupported_file():
    with pytest.raises(ValueError):
        get_file_category("program.exe")


# Test find_unsupported_files
def test_find_unsupported_files_returns_invalid_items():
    result = find_unsupported_files(["data.csv", "program.exe", None, "   ", "report.pdf"])
    assert result == ["program.exe", None, "   "]

def test_find_unsupported_files_returns_empty_list_for_supported_files():
    result = find_unsupported_files(["data.csv", "report.pdf", "profile.png"])
    assert result == []
