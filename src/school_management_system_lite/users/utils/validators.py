import re
from datetime import date

from pydantic_core import PydanticCustomError

from school_management_system_lite.users.utils.constants import (
    NON_STUDENT_MAX_AGE,
    NON_STUDENT_MIN_AGE,
    STUDENT_MAX_AGE,
    STUDENT_MIN_AGE,
)

_NAME_PATTERN = re.compile(r"^[A-Za-zÀ-ÖØ-öø-ÿ]+(?:['\-][A-Za-zÀ-ÖØ-öø-ÿ]+)*$")


def validate_name(value: str, field: str) -> str:
    if not _NAME_PATTERN.fullmatch(value):
        raise PydanticCustomError(
            f"invalid_{field}_characters",
            f"{field.capitalize()} can only contain letters, hyphens, and apostrophes",
        )

    return re.sub(
        r"([A-Za-zÀ-ÖØ-öø-ÿ]+)",
        lambda m: m.group(0).capitalize(),
        value,
    )


def validate_first_name(firstname: str) -> str:
    return validate_name(firstname, "first_name")


def validate_last_name(lastname: str) -> str:
    return validate_name(lastname, "last_name")


def validate_middle_name(middlename: str) -> str:
    return validate_name(middlename, "middle_name")


def _validate_date_of_birth(
    birth_date: date, *, min_age: int, max_age: int, subject: str
) -> date:
    if birth_date >= datetime.now(UTC).date():
        raise PydanticCustomError(
            "date_of_birth_not_in_past", "Date of birth must be in the past"
        )

    age = calculate_age(birth_date)
    if age < min_age:
        raise PydanticCustomError(
            "date_of_birth_too_young", f"{subject} must be at least {min_age} years old"
        )

    if age > max_age:
        raise PydanticCustomError(
            "date_of_birth_too_old", f"{subject} must be {max_age} years old or younger"
        )

    return birth_date


def validate_date_of_birth_student(birth_date: date) -> date:
    return _validate_date_of_birth(
        birth_date, min_age=STUDENT_MIN_AGE, max_age=STUDENT_MAX_AGE, subject="Student"
    )


def validate_date_of_birth_non_student(birth_date: date) -> date:
    return _validate_date_of_birth(
        birth_date,
        min_age=NON_STUDENT_MIN_AGE,
        max_age=NON_STUDENT_MAX_AGE,
        subject="User",
    )
