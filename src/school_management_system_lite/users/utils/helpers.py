from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from school_management_system_lite.core.config import get_settings


def school_today() -> date:
    """Current date in the school's timezone."""
    return datetime.now(ZoneInfo(get_settings().SCHOOL_TIMEZONE)).date()


def calculate_age(birth_date: date, today: date | None = None) -> int:
    today = today or school_today()

    return (
        today.year
        - birth_date.year
        - ((today.month, today.day) < (birth_date.month, birth_date.day))
    )


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)

    return value
