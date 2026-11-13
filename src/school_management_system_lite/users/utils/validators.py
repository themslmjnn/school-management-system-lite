import re
import unicodedata
from datetime import date

from pydantic_core import PydanticCustomError

from school_management_system_lite.users.utils import constants as user_constants
from school_management_system_lite.users.utils.helpers import (
    calculate_age,
    school_today,
)

_LATIN = "A-Za-zÀ-ÖØ-öø-ÿ"
_CYRILLIC = "А-Яа-яЁё"
_NAME_PATTERN = re.compile(rf"[{_LATIN}{_CYRILLIC}]+(?:[ '\-][{_LATIN}{_CYRILLIC}]+)*")
_LATIN_RE = re.compile(rf"[{_LATIN}]")
_CYRILLIC_RE = re.compile(rf"[{_CYRILLIC}]")
_SEPARATORS_RE = re.compile(r"[ '\-]")


def validate_name(value: str, field: str) -> str:
    value = unicodedata.normalize("NFC", " ".join(value.split()))
    label = field.replace("_", " ").capitalize()

    if not (
        user_constants.NAME_MIN_LENGTH <= len(value) <= user_constants.NAME_MAX_LENGTH
    ):
        raise PydanticCustomError(
            f"invalid_{field}_length",
            f"{label} must be between {user_constants.NAME_MIN_LENGTH} and "
            f"{user_constants.NAME_MAX_LENGTH} characters",
        )

    if not _NAME_PATTERN.fullmatch(value):
        raise PydanticCustomError(
            f"invalid_{field}_characters",
            f"{label} can only contain English, accented Latin, or Russian "
            "letters, spaces, hyphens, and apostrophes. Hyphens and apostrophes "
            "must be placed between letters and cannot repeat",
        )

    for word in _SEPARATORS_RE.split(value):
        if _LATIN_RE.search(word) and _CYRILLIC_RE.search(word):
            raise PydanticCustomError(
                f"invalid_{field}_mixed_scripts",
                f"{label} cannot mix Latin and Cyrillic letters within one word",
            )

    return value


def validate_first_name(firstname: str) -> str:
    return validate_name(firstname, "first_name")


def validate_last_name(lastname: str) -> str:
    return validate_name(lastname, "last_name")


def validate_middle_name(middlename: str) -> str:
    return validate_name(middlename, "middle_name")


def _validate_date_of_birth(
    birth_date: date,
    *,
    min_age: int,
    max_age: int,
    subject: str,
    today: date | None = None,
) -> date:
    today = today or school_today()

    if birth_date >= today:
        raise PydanticCustomError(
            "date_of_birth_not_in_past", "Date of birth must be in the past"
        )

    age = calculate_age(birth_date, today)

    if age < min_age:
        raise PydanticCustomError(
            "date_of_birth_too_young",
            f"{subject} must be at least {min_age} years old",
        )

    if age > max_age:
        raise PydanticCustomError(
            "date_of_birth_too_old",
            f"{subject} must be {max_age} years old or younger",
        )

    return birth_date


def validate_date_of_birth_student(birth_date: date, today: date | None = None) -> date:
    return _validate_date_of_birth(
        birth_date,
        min_age=user_constants.STUDENT_MIN_AGE,
        max_age=user_constants.STUDENT_MAX_AGE,
        subject="Student",
        today=today,
    )


def validate_date_of_birth_non_student(
    birth_date: date, today: date | None = None
) -> date:
    return _validate_date_of_birth(
        birth_date,
        min_age=user_constants.NON_STUDENT_MIN_AGE,
        max_age=user_constants.NON_STUDENT_MAX_AGE,
        subject="User",
        today=today,
    )


_PHONE_FORMAT_PATTERN = re.compile(r"\+[1-9][0-9]*(?: [0-9]+)*")


def validate_phone_number(phone_number: str) -> str:
    phone_number = phone_number.strip()
    digits = phone_number[1:].replace(" ", "")

    if not _PHONE_FORMAT_PATTERN.fullmatch(phone_number) or not (
        user_constants.PHONE_MIN_DIGITS
        <= len(digits)
        <= user_constants.PHONE_MAX_DIGITS
    ):
        raise PydanticCustomError(
            "invalid_phone_number",
            "Phone number must start with '+' followed by "
            f"{user_constants.PHONE_MIN_DIGITS}-{user_constants.PHONE_MAX_DIGITS} "
            "digits. Single spaces are allowed between digits",
        )

    return "+" + digits


_DOMAIN_LABEL = r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?"
_EMAIL_PATTERN = re.compile(
    rf"[a-z0-9_]+(?:\.[a-z0-9_]+)*@(?:{_DOMAIN_LABEL}\.)+[a-z]{{2,}}"
)


def validate_email(email: str) -> str:
    email = email.strip().lower()

    if len(email) > user_constants.EMAIL_MAX_LENGTH:
        raise PydanticCustomError(
            "invalid_email",
            f"Email must be at most {user_constants.EMAIL_MAX_LENGTH} characters",
        )

    if not _EMAIL_PATTERN.fullmatch(email):
        raise PydanticCustomError(
            "invalid_email",
            "Email must have exactly one '@'. Before it, only English letters, "
            "digits, '_' and '.' are allowed (no leading, trailing or consecutive "
            "dots). After it, a domain such as 'school.edu' is required",
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
