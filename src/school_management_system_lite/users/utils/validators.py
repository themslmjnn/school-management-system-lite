import re
from datetime import UTC, date, datetime

from pydantic_core import PydanticCustomError

from school_management_system_lite.users.utils import constants as user_constants
from school_management_system_lite.users.utils.helpers import calculate_age

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
        birth_date,
        min_age=user_constants.STUDENT_MIN_AGE,
        max_age=user_constants.STUDENT_MAX_AGE,
        subject="Student",
    )


def validate_date_of_birth_non_student(birth_date: date) -> date:
    return _validate_date_of_birth(
        birth_date,
        min_age=user_constants.NON_STUDENT_MIN_AGE,
        max_age=user_constants.NON_STUDENT_MAX_AGE,
        subject="User",
    )


def validate_phone_number(phone_number: str) -> str:
    phone_number = phone_number.strip()

    if not phone_number.startswith("+"):
        raise PydanticCustomError(
            "invalid_phone_number",
            "Phone number must start with '+'",
        )

    if phone_number.count("+") != 1:
        raise PydanticCustomError(
            "invalid_phone_number",
            "Phone number must contain only one '+'",
        )

    if any(
        not char.isdigit() and char != "+" and not char.isspace()
        for char in phone_number
    ):
        raise PydanticCustomError(
            "invalid_phone_number",
            "Phone number may contain only '+', digits, and spaces",
        )

    return "".join(phone_number.split())


def validate_email(email: str) -> str:
    email = email.strip().lower()

    if "@" not in email:
        raise PydanticCustomError(
            "invalid_email",
            "Email must contain '@'",
        )

    local_part, domain = email.rsplit("@", 1)

    if (
        not local_part
        or "." not in domain
        or domain.startswith(".")
        or domain.endswith(".")
    ):
        raise PydanticCustomError(
            "invalid_email",
            "Email must contain a valid domain",
        )

    return email


def validate_password(password: str) -> str:
    if not any(char.isupper() for char in password):
        raise PydanticCustomError(
            "password_no_uppercase",
            "Password must contain at least one uppercase letter",
        )

    if not any(char.isdigit() for char in password):
        raise PydanticCustomError(
            "password_no_digit",
            "Password must contain at least one digit",
        )

    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        raise PydanticCustomError(
            "password_no_special_character",
            "Password must contain at least one special character",
        )

    return password
