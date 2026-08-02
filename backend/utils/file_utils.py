# Reusable helper functions for creating and resolving file/folder paths

from pathlib import Path
from datetime import datetime
import re
import uuid

from backend.utils.validators import validate_filename
from backend.utils.constants import MAX_FILENAME_LENGTH

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def resolve_project_path(path: str | Path) -> Path:
    if isinstance(path,str): path = Path(path)
    if not path.is_absolute():
        path = PROJECT_ROOT.joinpath(path)
    return path.resolve()

def ensure_directory(path: str | Path) -> Path:
    if isinstance(path,str): path = Path(path)
    if not directory_exists(path):
        path.mkdir(parents=True, exist_ok=True)
    return path.resolve()
 
def get_or_create_path(path: str | Path) -> Path:
    path = ensure_directory(resolve_project_path(path))
    return path.resolve()


def ensure_dated_directory(
    base_path: str | Path,
    date_value: datetime,
) -> Path:
    return ensure_directory(
        Path(base_path)
        / date_value.strftime("%Y")
        / date_value.strftime("%m")
    )

def resolve_data_path(data_root: Path, paths: list[str | Path]) -> Path:
    resolved_root = Path(data_root).resolve()
    data_path = resolved_root
    for path in paths:
        if isinstance(path,str): path = Path(path)
        data_path = data_path.joinpath(path) 
    data_path = data_path.resolve()
    if not data_path.is_relative_to(resolved_root):
        raise ValueError("Path cannot escape the data root.")
    return data_path

def file_exists(path: str | Path) -> bool:
    if isinstance(path,str): path = Path(path)
    return path.is_file()

def directory_exists(path: str | Path) -> bool:
    if isinstance(path,str): path = Path(path)
    return path.is_dir()


def generate_safe_filename(original_filename: str) -> str:
    original_filename = validate_filename(original_filename)

    file_path = Path(original_filename)
    file = Path(file_path.name)

    filename = file.stem.lower()
    extension = file.suffix.lower()

    cleaned_filename = re.sub(r'[^\w-]', '', filename).replace(".", "_").strip("_-")

    if not cleaned_filename:
        cleaned_filename = "file"

    unique_id = uuid.uuid4().hex[:8]
    generated_suffix = f"_{unique_id}{extension}"
    max_stem_length = MAX_FILENAME_LENGTH - len(generated_suffix)
    if max_stem_length < 1:
        raise ValueError("The file extension is too long to create a safe filename.")

    stored_filename = f"{cleaned_filename[:max_stem_length]}{generated_suffix}"

    return stored_filename


def format_file_size(size_bytes: int) -> str:
    if size_bytes < 0:
        raise ValueError("File size cannot be negative.")

    if size_bytes >= 1024**3:
        return f"{size_bytes / 1024**3:.2f} GB"
    if size_bytes >= 1024**2:
        return f"{size_bytes / 1024**2:.2f} MB"
    return f"{size_bytes / 1024:.2f} KB"

