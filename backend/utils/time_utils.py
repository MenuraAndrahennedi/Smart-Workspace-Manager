from datetime import datetime, timezone


def time_now() -> datetime:
    return datetime.now(timezone.utc)
