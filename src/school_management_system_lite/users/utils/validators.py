import re
import unicodedata
from datetime import date

from pydantic_core import PydanticCustomError

from school_management_system_lite.users.utils import constants as user_constants
from school_management_system_lite.users.utils.helpers import (
    calculate_age,
    school_today,
)

_WORD = r"[A-Za-z]{2,}(?:[-'][A-Za-z]{2,})?"
_NAME_PATTERN = re.compile(rf"{_WORD}(?: {_WORD}){{0,2}}")
_LETTER_GROUP = re.compile(r"[A-Za-z]+")


def validate_name(value: str, field: str) -> str:
    value = " ".join(value.split())
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
            f"{label} can contain at most three words of English letters "
            "(at least 2 letters each). A word may contain one hyphen or "
            "apostrophe between letters",
        )

    return _LETTER_GROUP.sub(lambda m: m.group().capitalize(), value)


def validate_first_name(firstname: str) -> str:
    return validate_name(firstname, "first_name")


def validate_last_name(lastname: str) -> str:
    return validate_name(lastname, "last_name")


def validate_middle_name(middlename: str) -> str:
    return validate_name(middlename, "middle_name")


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
        subject="Staff",
        today=today,
    )


def validate_address(address: str) -> str | None:
    address = " ".join(address.split())
    if not address:
        return None

    if len(address) < user_constants.ADDRESS_MIN_LENGTH:
        raise PydanticCustomError(
            "invalid_address_length",
            f"Address must be at least {user_constants.ADDRESS_MIN_LENGTH} characters",
        )

    if len(address) > user_constants.ADDRESS_MAX_LENGTH:
        raise PydanticCustomError(
            "invalid_address_length",
            f"Address must be at most {user_constants.ADDRESS_MAX_LENGTH} characters",
        )

    if any(unicodedata.category(char) == "Cc" for char in address):
        raise PydanticCustomError(
            "invalid_address_characters",
            "Address must not contain control characters",
        )

    return address


def validate_password(password: str) -> str:
    if len(password.encode()) > user_constants.PASSWORD_MAX_BYTES:
        raise PydanticCustomError(
            "password_too_long",
            f"Password must be at most {user_constants.PASSWORD_MAX_BYTES} bytes. "
            "Non-English characters take more than one byte",
        )

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
