from dataclasses import dataclass
from pathlib import Path
import shutil
import uuid

from backend.config import settings
from backend.utils.file_utils import ensure_directory, file_exists
from backend.utils.constants import STORAGE_DIRECTORIES

PENDING_FILE_DELETIONS_KEY = "pending_file_deletions"


@dataclass(frozen=True)
class StagedFileDeletion:
    original_path: Path
    staged_path: Path


def get_storage_root():
    return ensure_directory(settings.DATA_ROOT)


def resolve_managed_path(
    path: Path | str,
    *,
    must_exist: bool = False,
    file_only: bool = False,
) -> Path:
    storage_root = get_storage_root().resolve()
    candidate_path = Path(path)
    if not candidate_path.is_absolute():
        candidate_path = storage_root / candidate_path
    candidate_path = candidate_path.resolve()

    if not candidate_path.is_relative_to(storage_root):
        raise ValueError(f"Path not related to data root: {candidate_path}")
    if must_exist and not candidate_path.exists():
        raise FileNotFoundError(f"Storage path does not exist: {candidate_path}")
    if file_only and candidate_path.exists() and not candidate_path.is_file():
        raise ValueError(f"Storage path is not a file: {candidate_path}")

    return candidate_path

def resolve_storage_path(path: Path | str) -> Path:
    if Path(path).is_absolute():
        raise ValueError("Storage path must be relative")
    return resolve_managed_path(path)


def initialize_storage() -> list[Path] | None:
    if settings.STORAGE_PROVIDER != "local":
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
    path = resolve_managed_path(path, file_only=True)
    if path.is_file():
        path.unlink()
        return True
    return False


def _remove_empty_staging_directories(
    staged_deletions: list[StagedFileDeletion],
) -> None:
    batch_directories = {
        deletion.staged_path.parent
        for deletion in staged_deletions
    }
    for batch_directory in batch_directories:
        if batch_directory.is_dir() and not any(batch_directory.iterdir()):
            batch_directory.rmdir()

    trash_directory = get_storage_root() / ".trash"
    if trash_directory.is_dir() and not any(trash_directory.iterdir()):
        trash_directory.rmdir()


def restore_staged_files(
    staged_deletions: list[StagedFileDeletion],
) -> None:
    for deletion in reversed(staged_deletions):
        if not deletion.staged_path.is_file():
            continue
        if deletion.original_path.exists():
            raise FileExistsError(
                f"Cannot restore file because its original path exists: "
                f"{deletion.original_path}"
            )
        ensure_directory(deletion.original_path.parent)
        shutil.move(deletion.staged_path, deletion.original_path)

    _remove_empty_staging_directories(staged_deletions)


def finalize_staged_files(
    staged_deletions: list[StagedFileDeletion],
) -> None:
    for deletion in staged_deletions:
        if deletion.staged_path.is_file():
            deletion.staged_path.unlink()

    _remove_empty_staging_directories(staged_deletions)


def stage_files_for_deletion(
    paths: list[Path | str],
) -> list[StagedFileDeletion]:
    managed_paths: list[Path] = []
    seen_paths: set[Path] = set()

    for path in paths:
        managed_path = resolve_managed_path(path, file_only=True)
        if managed_path in seen_paths:
            continue
        seen_paths.add(managed_path)

        if managed_path.exists() and not managed_path.is_file():
            raise ValueError(f"Storage path is not a file: {managed_path}")
        if managed_path.is_file():
            managed_paths.append(managed_path)

    if not managed_paths:
        return []

    batch_directory = ensure_directory(
        get_storage_root() / ".trash" / uuid.uuid4().hex
    )
    staged_deletions: list[StagedFileDeletion] = []

    try:
        for index, original_path in enumerate(managed_paths):
            staged_path = batch_directory / f"{index}_{original_path.name}"
            shutil.move(original_path, staged_path)
            staged_deletions.append(
                StagedFileDeletion(
                    original_path=original_path,
                    staged_path=staged_path,
                )
            )
    except Exception:
        restore_staged_files(staged_deletions)
        if batch_directory.is_dir() and not any(batch_directory.iterdir()):
            batch_directory.rmdir()
        raise

    return staged_deletions



def move_file(
    source_path: Path,
    destination_path: Path
) -> Path:
    source_path = resolve_managed_path(source_path, file_only=True)
    if not file_exists(source_path):
        raise ValueError("Source file does not exist")
        
    destination_path = resolve_managed_path(destination_path, file_only=True)
    
    ensure_directory(destination_path.parent)

    if file_exists(destination_path):
        raise FileExistsError(f"File already exists at {destination_path}")

    return Path(shutil.move(source_path, destination_path))

    









