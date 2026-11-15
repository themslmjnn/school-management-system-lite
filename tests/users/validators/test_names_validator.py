import pytest
from pydantic_core import PydanticCustomError

from school_management_system_lite.users.utils.validators import validate_name

ACCEPTED_NAMES = [
    ("Umarali", "Umarali"),
    ("UMARALI", "Umarali"),
    ("umarali", "Umarali"),
    ("UmarAli", "Umarali"),
    ("Umar Ali", "Umar Ali"),
    ("Umar Ali Name", "Umar Ali Name"),
    ("  Umar   Ali  ", "Umar Ali"),
    ("Umar\tAli", "Umar Ali"),
    ("Umar-Ali", "Umar-Ali"),
    ("umar-ali", "Umar-Ali"),
    ("Umar'Ali", "Umar'Ali"),
    ("Um", "Um"),
    ("Umar-Ali Smith-Jones", "Umar-Ali Smith-Jones"),
    ("LessThanThirtyOneNames", "Lessthanthirtyonenames"),
]

REJECTED_NAMES = [
    "",
    "   ",
    "U",
    "Umar Ali Name Extra",
    "Umar - Ali",
    "Umar -Ali",
    "Umar- Ali",
    "-Umarali",
    "Umarali-",
    "'Umarali",
    "Umarali'",
    "Umar—Ali",
    "Umar--Ali",
    "U-mar-Ali",
    "U'mar",
    "U'mar'Ali",
    "U'mar-Ali",
    "Umar''Ali",
    "Umar ' Ali",
    "Umar’Ali",
    "Um m",
    "Um-m",
    "Umar A",
    "ThirtyOneLongNamesAreNotAccepted",
    "123Umarali",
    "Umar123ali",
    "Umarali123",
    "~!@#$%Umarali",
    "Umar%^&*()_+Ali",
    "Umarali{}[];/,.><",
    "Умарали",
    "Ùmäřáľ",
    "Umar_Ali",
]


@pytest.mark.parametrize(("raw", "expected"), ACCEPTED_NAMES)
def test_validate_name_accepted(raw: str, expected: str):
    assert validate_name(raw, "first_name") == expected


@pytest.mark.parametrize("raw", REJECTED_NAMES)
def test_validate_name_rejected(raw):
    with pytest.raises(PydanticCustomError):
        validate_name(raw, "first_name")
