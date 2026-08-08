import os 
from pathlib import Path
from dotenv import load_dotenv

from backend.utils.file_utils import PROJECT_ROOT, get_or_create_path
from backend.utils.time_utils import time_now

ENV_FILE = PROJECT_ROOT / ".env"
ACCEPTED_LOG_VALUES: list[str] = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL","NOTSET"]


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
    
    if not value.startswith("sqlite:///") : #and not value.startswith("postgresql://"):
        raise ValueError(f"Environment variable '{name}' must be a valid database URL.")
    return value

def get_valid_storage_provider(name: str) -> str:
    value = get_env_variable(name)
    valid_providers = ["local"]
    if value not in valid_providers:
        raise ValueError(f"Environment variable '{name}' must be one of {valid_providers}.")
    return value

# def get_secret_key(name: str) -> str:
#     value = get_env_variable(name)
#     if len(value) < 32:
#         raise ValueError(f"Environment variable '{name}' must be at least 32 characters long.")
#     return value

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


DATABASE_URL = get_valid_database_url("DATABASE_URL")
DATA_ROOT = get_or_create_path(get_env_variable("DATA_ROOT"))
MAX_UPLOAD_SIZE_MB = get_upload_size("MAX_UPLOAD_SIZE_MB")
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024
SECRET_KEY = get_secret_key("SECRET_KEY")
STORAGE_PROVIDER = get_valid_storage_provider("STORAGE_PROVIDER")
LOG_LEVEL = get_log_value_accepted("LOG_LEVEL")
MAX_FILENAME_ATTEMPTS = get_positive_int("MAX_FILENAME_ATTEMPTS")

TIME_SYSTEM_STARTED = time_now()

MAX_CSV_ANALYSIS_SIZE_MB = MAX_UPLOAD_SIZE_MB
MAX_CSV_ROWS=get_int("MAX_CSV_ROWS")
MAX_CSV_COLUMNS=get_int("MAX_CSV_COLUMNS")

MAX_CHART_ROWS=get_int("MAX_CHART_ROWS")
MAX_BAR_CATEGORIES=get_int("MAX_BAR_CATEGORIES")
MAX_REPORT_CHARTS=get_int("MAX_REPORT_CHARTS")
