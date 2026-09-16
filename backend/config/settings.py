import os 
from pathlib import Path
from urllib.parse import urlsplit
from dotenv import load_dotenv

from backend.utils.file_utils import PROJECT_ROOT, get_or_create_path
from backend.utils.time_utils import time_now

ENV_FILE = PROJECT_ROOT / ".env"
ACCEPTED_LOG_VALUES: list[str] = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL","NOTSET"]
ACCEPTED_JWT_ALGORITHMS: list[str] = ["HS256"]


load_dotenv(dotenv_path=ENV_FILE, override=False)

def get_env_variable(name: str) -> str:
    value = os.getenv(name)
    if value is None:
        raise ValueError(f"Environment variable '{name}' is not set.")
    return value

def get_int(name: str) -> int:
    value = get_env_variable(name)
    try:
        return int(value)
    except ValueError:
        raise ValueError(f"Environment variable '{name}' must be an integer.")
    
def get_positive_int(name: str) -> int:
    value = get_int(name)
    if value <= 0:
        raise ValueError(f"Environment variable '{name}' must be a positive integer.")
    return value

def get_valid_database_url(name: str) -> str:
    value = get_env_variable(name)

    valid_prefixes = (
        "sqlite:///",
        "mssql+pyodbc://",
    )

    if not value.startswith(valid_prefixes):
        raise ValueError(
            f"Environment variable '{name}' must be a valid SQLite or Azure SQL URL."
        )

    return value

def get_valid_storage_provider(name: str) -> str:
    value = get_env_variable(name)
    valid_providers = ["local"]
    if value not in valid_providers:
        raise ValueError(f"Environment variable '{name}' must be one of {valid_providers}.")
    return value

def get_secret_key(name: str) -> str:
    value = get_env_variable(name)
    if len(value) < 32:
        raise ValueError(f"Environment variable '{name}' must be at least 32 characters long.")
    return value


def get_algorithm(name: str) -> str:
    value = get_env_variable(name).upper()
    if value not in ACCEPTED_JWT_ALGORITHMS:
        raise ValueError(
            f"Environment variable '{name}' must be one of {ACCEPTED_JWT_ALGORITHMS}."
        )
    return value


def get_valid_access_token_expire_time(name: str) -> int:
    value = get_positive_int(name)
    if value > 1440:
        raise ValueError(f"Environment variable '{name}' must not exceed 1440 minutes.")
    return value

def get_upload_size(name: str) -> int:
    value = get_positive_int(name)
    if value > 10:
        raise ValueError(f"Environment variable '{name}' must not exceed 10 MB.")
    return value


def get_log_value_accepted(log_value: str) -> str:
    log_value = get_env_variable(log_value).upper()
    if log_value in ACCEPTED_LOG_VALUES:
        return log_value
    else:
        raise ValueError(f"Cannot accept {log_value} log value")

def get_valid_frontend_origins(
    name: str,
    legacy_name: str | None = None,
) -> list[str]:
    value = os.getenv(name)

    if value is None and legacy_name is not None:
        value = os.getenv(legacy_name)

    if value is None:
        raise ValueError(f"Environment variable '{name}' is not set.")

    origins: list[str] = []

    for configured_origin in value.split(","):
        origin = configured_origin.strip().rstrip("/")
        if not origin:
            continue

        parsed_origin = urlsplit(origin)
        if (
            parsed_origin.scheme not in {"http", "https"}
            or not parsed_origin.netloc
            or parsed_origin.path
            or parsed_origin.query
            or parsed_origin.fragment
            or parsed_origin.username is not None
            or parsed_origin.password is not None
        ):
            raise ValueError(
                f"Environment variable '{name}' contains an invalid frontend origin."
            )

        if origin not in origins:
            origins.append(origin)

    if not origins:
        raise ValueError(
            f"Environment variable '{name}' must contain at least one frontend origin."
        )

    return origins

DATABASE_URL = get_valid_database_url("DATABASE_URL")
DATA_ROOT = get_or_create_path(get_env_variable("DATA_ROOT"))
MAX_UPLOAD_SIZE_MB = get_upload_size("MAX_UPLOAD_SIZE_MB")
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024
SECRET_KEY = get_secret_key("SECRET_KEY")
ALGORITHM = get_algorithm("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = get_valid_access_token_expire_time("ACCESS_TOKEN_EXPIRE_MINUTES")
STORAGE_PROVIDER = get_valid_storage_provider("STORAGE_PROVIDER")
LOG_LEVEL = get_log_value_accepted("LOG_LEVEL")
MAX_FILENAME_ATTEMPTS = get_positive_int("MAX_FILENAME_ATTEMPTS")

TIME_SYSTEM_STARTED = time_now()

MAX_CSV_ANALYSIS_SIZE_MB = get_upload_size("MAX_CSV_ANALYSIS_SIZE_MB")
MAX_CSV_ROWS=get_int("MAX_CSV_ROWS")
MAX_CSV_COLUMNS=get_int("MAX_CSV_COLUMNS")

MAX_CHART_ROWS=get_int("MAX_CHART_ROWS")
MAX_BAR_CATEGORIES=get_int("MAX_BAR_CATEGORIES")
MAX_REPORT_CHARTS=get_int("MAX_REPORT_CHARTS")

FRONTEND_ORIGINS = get_valid_frontend_origins(
    "FRONTEND_ORIGINS",
    legacy_name="FRONTEND_ORIGIN",
)
