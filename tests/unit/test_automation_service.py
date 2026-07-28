import pytest
from datetime import datetime
from pathlib import Path

from backend.services.automation_service import detect_file_category, build_destination_directory
import backend.services.automation_service as automation_service

# Several extensions to be tested with one functio
@pytest.mark.parametrize(
    "filename, expected_category",
    [
        ("sales.csv", "spreadsheets"),
        ("report.xlsx", "spreadsheets"),
        ("old_data.xls", "spreadsheets"),
        ("photo.jpg", "images"),
        ("logo.PNG", "images"),
        ("document.docx", "documents"),
        ("slides.pptx", "documents"),
        ("research.pdf", "pdf"),
        ("backup.zip", "others"),
        ("script.py", "others"),
    ],
)

# Test detect_file_category
def test_detect_file_category_valid(filename, expected_category):
    assert detect_file_category(filename) == expected_category

# Test build_destination_directory
def test_build_destination_directory_valid(monkeypatch, tmp_path):
    fixed_date = datetime(2026, 7, 27)

    monkeypatch.setattr(
        automation_service,
        "DATA_ROOT",
        tmp_path,
    )

    result = build_destination_directory(
        category="spreadsheets",
        date_value=fixed_date,
    )

    expected_path = tmp_path / "processed" / "spreadsheets" / "2026" / "07"

    assert result == expected_path

def test_build_destination_directory_invalid_category():
    with pytest.raises(ValueError):
        build_destination_directory("audio")


