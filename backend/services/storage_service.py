# Manage storage paths without other parts of the system needing to know whether the root is

from pathlib import Path

from backend.config.settings import DATA_ROOT, STORAGE_PROVIDER
from backend.utils.file_utils import ensure_directory, file_exists
from backend.utils.constants import STORAGE_DIRECTORIES

def get_storage_root():
    return ensure_directory(DATA_ROOT)

def resolve_storage_path(path: Path | str) -> Path:
    if isinstance(path,str): path = Path(path)

    if path.is_absolute():
        raise ValueError("Storage path must be relative")
    else:
        storage_root = get_storage_root()
        candidate_path = (storage_root.joinpath(path)).resolve()

    if not candidate_path.is_relative_to(DATA_ROOT): 
        raise ValueError("Path cannot escape the storage directory.")

    return candidate_path


def initialize_storage() -> list[Path] | None:
    if not STORAGE_PROVIDER == "local":
        raise NotImplementedError("Current system supports only filesystem storage")

    relative_paths: list = []
    for relative_directory in STORAGE_DIRECTORIES:
        path = ensure_directory(resolve_storage_path(relative_directory))
        relative_paths.append(path)

    return relative_paths


def save_uploaded_bytes(stored_filename: str, file_bytes: bytes) -> Path:
    if not Path(stored_filename).name == stored_filename:
        raise ValueError("The file name is not valid")

    upload_directory = ensure_directory(resolve_storage_path("uploads"))
    destination_path = upload_directory / stored_filename

    if destination_path.exists():
        raise FileExistsError("File already exists")

    if not isinstance(file_bytes, bytes):
        raise TypeError("File-bytes must be bytes.")
    else:
        destination_path.write_bytes(file_bytes)

    return destination_path


def delete_stored_file(path: Path) -> bool:
    if path.exists() and file_exists(path):
        path.unlink()
        return True
    return False

    




