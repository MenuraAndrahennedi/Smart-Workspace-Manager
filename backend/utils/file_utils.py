# Reusable helper functions for creating and resolving file/folder paths

from pathlib import Path

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

def resolve_data_path(data_root: Path, paths: list[str | Path]) -> Path:
    data_path = data_root
    for path in paths:
        if isinstance(path,str): path = Path(path)
        data_path = data_path.joinpath(path) 
    return data_path.resolve()

def file_exists(path: str | Path) -> bool:
    if isinstance(path,str): path = Path(path)
    return path.is_file()

def directory_exists(path: str | Path) -> bool:
    if isinstance(path,str): path = Path(path)
    return path.is_dir()