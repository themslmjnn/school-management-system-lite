from datetime import UTC, date, datetime


def calculate_age(birth_date: date, today: date | None = None) -> int:
    today = today or datetime.now(UTC).date()

    return (
        today.year
        - birth_date.year
        - ((today.month, today.day) < (birth_date.month, birth_date.day))
    )
