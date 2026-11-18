from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError
from pydantic_core import PydanticCustomError

from school_management_system_lite.core.config import get_settings
from school_management_system_lite.users.schemas.system_admin import CreateUserAdmin
from school_management_system_lite.users.utils import constants as user_constants
from school_management_system_lite.users.utils import validators
from school_management_system_lite.users.utils.enums import UserRole
from school_management_system_lite.users.utils.helpers import (
    calculate_age,
    school_today,
)
from school_management_system_lite.users.utils.validators import (
    validate_date_of_birth_non_student,
    validate_date_of_birth_student,
)

TODAY = date(2026, 3, 10)

NOT_IN_PAST = "date_of_birth_not_in_past"
TOO_YOUNG = "date_of_birth_too_young"
TOO_OLD = "date_of_birth_too_old"

# (birth_date, expected error code or None when accepted), today = 2026-03-10
STUDENT_CASES = [
    # Not in the past
    (date(2100, 1, 1), NOT_IN_PAST),
    (date(2026, 3, 11), NOT_IN_PAST),  # tomorrow
    (date(2026, 3, 10), NOT_IN_PAST),  # today
    # Too young (min 6)
    (date(2026, 3, 9), TOO_YOUNG),  # yesterday, age 0
    (date(2020, 4, 5), TOO_YOUNG),  # age 5, later month and earlier day
    (date(2020, 3, 11), TOO_YOUNG),  # age 5, turns 6 tomorrow
    # Accepted: minimum age and inside the range
    (date(2020, 3, 10), None),  # age 6 today
    (date(2020, 2, 20), None),  # age 6, earlier month and later day
    (date(2015, 6, 15), None),  # age 10
    (date(2007, 3, 11), None),  # age 18
    (date(2007, 3, 10), None),  # age 19
    # Accepted: maximum age
    (date(2004, 3, 11), None),  # age 21, turns 22 tomorrow
    # Too old (max 21)
    (date(2004, 3, 10), TOO_OLD),  # age 22 today
    (date(2004, 1, 1), TOO_OLD),
    (date(1955, 3, 10), TOO_OLD),
    (date(1900, 1, 1), TOO_OLD),
]

NON_STUDENT_CASES = [
    # Not in the past
    (date(2100, 1, 1), NOT_IN_PAST),
    (date(2026, 3, 11), NOT_IN_PAST),
    (date(2026, 3, 10), NOT_IN_PAST),
    # Too young (min 19)
    (date(2026, 3, 9), TOO_YOUNG),
    (date(2020, 3, 10), TOO_YOUNG),  # age 6
    (date(2007, 4, 5), TOO_YOUNG),  # age 18, later month and earlier day
    (date(2007, 3, 11), TOO_YOUNG),  # age 18, turns 19 tomorrow
    # Accepted: minimum age and inside the range
    (date(2007, 3, 10), None),  # age 19 today
    (date(2007, 2, 20), None),  # age 19, earlier month and later day
    (date(2004, 3, 10), None),  # age 22 (too old for a student, fine here)
    (date(1990, 1, 1), None),
    # Accepted: maximum age
    (date(1956, 3, 11), None),  # age 69
    (date(1956, 3, 10), None),  # age 70 today
    (date(1955, 3, 11), None),  # age 70, turns 71 tomorrow
    # Too old (max 70)
    (date(1955, 3, 10), TOO_OLD),  # age 71 today
    (date(1900, 1, 1), TOO_OLD),
]


def _check(validator, birth_date: date, expected_error: str | None, today: date):
    if expected_error is None:
        assert validator(birth_date, today=today) == birth_date
        return

    with pytest.raises(PydanticCustomError) as exc_info:
        validator(birth_date, today=today)

    assert exc_info.value.type == expected_error


@pytest.mark.parametrize(("birth_date", "expected_error"), STUDENT_CASES)
def test_validate_date_of_birth_student(birth_date, expected_error):
    _check(validate_date_of_birth_student, birth_date, expected_error, TODAY)


@pytest.mark.parametrize(("birth_date", "expected_error"), NON_STUDENT_CASES)
def test_validate_date_of_birth_non_student(birth_date, expected_error):
    _check(validate_date_of_birth_non_student, birth_date, expected_error, TODAY)


# --- Boundaries built from the constants (follow them if they change) ---
@pytest.mark.parametrize(
    ("validator", "min_age", "max_age"),
    [
        (
            validate_date_of_birth_student,
            user_constants.STUDENT_MIN_AGE,
            user_constants.STUDENT_MAX_AGE,
        ),
        (
            validate_date_of_birth_non_student,
            user_constants.NON_STUDENT_MIN_AGE,
            user_constants.NON_STUDENT_MAX_AGE,
        ),
    ],
)
def test_age_limits_are_inclusive(validator, min_age, max_age):
    one_day = timedelta(days=1)

    turned_min_today = date(TODAY.year - min_age, TODAY.month, TODAY.day)

    assert validator(turned_min_today, today=TODAY) == turned_min_today

    with pytest.raises(PydanticCustomError) as young:
        validator(turned_min_today + one_day, today=TODAY)

    assert young.value.type == TOO_YOUNG

    last_day_of_max_age = (
        date(TODAY.year - max_age - 1, TODAY.month, TODAY.day) + one_day
    )

    assert validator(last_day_of_max_age, today=TODAY) == last_day_of_max_age

    with pytest.raises(PydanticCustomError) as old:
        validator(last_day_of_max_age - one_day, today=TODAY)

    assert old.value.type == TOO_OLD


# --- Leap-day birthdays: the birthday counts as March 1 in non-leap years ---
def test_leap_day_birthday_turns_older_on_march_1_in_non_leap_year():
    born = date(2004, 2, 29)

    # Day before: still 21 (student maximum)
    assert validate_date_of_birth_student(born, today=date(2026, 2, 28)) == born

    # March 1: already 22
    with pytest.raises(PydanticCustomError) as exc_info:
        validate_date_of_birth_student(born, today=date(2026, 3, 1))

    assert exc_info.value.type == TOO_OLD


def test_leap_day_birthday_minimum_age():
    born = date(2020, 2, 29)

    with pytest.raises(PydanticCustomError) as exc_info:
        validate_date_of_birth_student(born, today=date(2026, 2, 28))  # age 5

    assert exc_info.value.type == TOO_YOUNG
    assert validate_date_of_birth_student(born, today=date(2026, 3, 1)) == born  # age 6


# --- Error messages ---
def test_student_error_messages():
    with pytest.raises(PydanticCustomError) as young:
        validate_date_of_birth_student(date(2020, 3, 11), today=TODAY)

    with pytest.raises(PydanticCustomError) as old:
        validate_date_of_birth_student(date(2004, 3, 10), today=TODAY)

    with pytest.raises(PydanticCustomError) as future:
        validate_date_of_birth_student(TODAY, today=TODAY)

    assert young.value.message() == (
        f"Student must be at least {user_constants.STUDENT_MIN_AGE} years old"
    )
    assert old.value.message() == (
        f"Student must be {user_constants.STUDENT_MAX_AGE} years old or younger"
    )
    assert future.value.message() == "Date of birth must be in the past"


def test_non_student_error_messages():
    with pytest.raises(PydanticCustomError) as young:
        validate_date_of_birth_non_student(date(2007, 3, 11), today=TODAY)

    with pytest.raises(PydanticCustomError) as old:
        validate_date_of_birth_non_student(date(1955, 3, 10), today=TODAY)

    assert young.value.message() == (
        f"Staff must be at least {user_constants.NON_STUDENT_MIN_AGE} years old"
    )
    assert old.value.message() == (
        f"Staff must be {user_constants.NON_STUDENT_MAX_AGE} years old or younger"
    )


# --- Default "today" comes from school_today() ---
def test_default_today_uses_school_today(monkeypatch):
    monkeypatch.setattr(validators, "school_today", lambda: TODAY)

    assert validate_date_of_birth_student(date(2020, 3, 10)) == date(2020, 3, 10)

    with pytest.raises(PydanticCustomError) as exc_info:
        validate_date_of_birth_student(date(2020, 3, 11))

    assert exc_info.value.type == TOO_YOUNG

    with pytest.raises(PydanticCustomError) as future:
        validate_date_of_birth_non_student(TODAY)

    assert future.value.type == NOT_IN_PAST


def test_school_today_returns_date_in_school_timezone():
    tz = ZoneInfo(get_settings().SCHOOL_TIMEZONE)

    before = datetime.now(tz).date()
    result = school_today()
    after = datetime.now(tz).date()

    assert type(result) is date  # a date, not a datetime
    assert before <= result <= after


@pytest.mark.parametrize(
    ("birth_date", "today", "expected"),
    [
        (date(2000, 3, 10), date(2026, 3, 10), 26),  # birthday today
        (date(2000, 3, 11), date(2026, 3, 10), 25),  # birthday tomorrow
        (date(2000, 3, 9), date(2026, 3, 10), 26),  # birthday yesterday
        (date(2000, 2, 20), date(2026, 3, 10), 26),  # later month passed, day larger
        (date(2000, 4, 5), date(2026, 3, 10), 25),  # month not reached, day smaller
        (date(2000, 12, 31), date(2026, 1, 1), 25),
        (date(2026, 3, 10), date(2026, 3, 10), 0),
    ],
)
def test_calculate_age(birth_date, today, expected):
    assert calculate_age(birth_date, today) == expected


# --- Wiring: proves the role-based check is attached to CreateUserAdmin.date_of_birth ---
def _years_ago(years: int) -> date:
    """A birth date exactly `years` ago in the school's calendar (day capped at 28)."""

    today = school_today()

    return date(today.year - years, today.month, min(today.day, 28))


_BASE_PAYLOAD = {
    "first_name": "Umar",
    "last_name": "Ali",
    "phone_number": "+998901234567",
    "email": "umar.ali@school.com",
}


@pytest.mark.parametrize(
    ("role", "years"),
    [
        (UserRole.STUDENT, 10),
        (UserRole.STUDENT, 20),  # inside the 19-21 overlap
        (UserRole.TEACHER, 30),
        (UserRole.TEACHER, 20),  # inside the 19-21 overlap
        (UserRole.DIRECTOR, 45),
    ],
)
def test_create_user_accepts_valid_age_for_role(role, years):
    payload = CreateUserAdmin(
        **_BASE_PAYLOAD, role=role, date_of_birth=_years_ago(years)
    )

    assert payload.date_of_birth == _years_ago(years)


@pytest.mark.parametrize(
    ("role", "years", "error_type"),
    [
        (UserRole.STUDENT, 3, TOO_YOUNG),
        (UserRole.STUDENT, 40, TOO_OLD),  # too old for a student, fine for staff
        (UserRole.TEACHER, 10, TOO_YOUNG),  # fine for a student, too young for staff
        (UserRole.DIRECTOR, 90, TOO_OLD),
        (UserRole.STUDENT, -1, NOT_IN_PAST),  # a year in the future
        (UserRole.TEACHER, -1, NOT_IN_PAST),
    ],
)
def test_create_user_rejects_invalid_age_at_field_location(role, years, error_type):
    with pytest.raises(ValidationError) as exc_info:
        CreateUserAdmin(**_BASE_PAYLOAD, role=role, date_of_birth=_years_ago(years))

    errors = exc_info.value.errors()

    assert len(errors) == 1
    assert errors[0]["loc"] == ("date_of_birth",)
    assert errors[0]["type"] == error_type


def test_create_user_invalid_role_reports_only_the_role_error():
    with pytest.raises(ValidationError) as exc_info:
        CreateUserAdmin(**_BASE_PAYLOAD, role="parent", date_of_birth=_years_ago(30))

    errors = exc_info.value.errors()

    assert len(errors) == 1
    assert errors[0]["loc"] == ("role",)
