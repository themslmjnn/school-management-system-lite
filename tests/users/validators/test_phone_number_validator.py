import pytest
from pydantic_core import PydanticCustomError

from school_management_system_lite.users.utils.validators import validate_phone_number

ACCEPTED_PHONES = [
    # Plain numbers
    ("+998901234567", "+998901234567"),
    ("+79991234567", "+79991234567"),
    # Single spaces between digits are removed
    ("+998 90 123 45 67", "+998901234567"),
    ("+7 999 123 45 67", "+79991234567"),
    ("+1 2345678", "+12345678"),
    ("+1 2 3 4 5 6 7 8", "+12345678"),
    # Surrounding whitespace is trimmed
    ("  +7 999 123 45 67 ", "+79991234567"),
    ("\t+998901234567\n", "+998901234567"),
    # Digit-count boundaries: 8 and 15 digits
    ("+12345678", "+12345678"),
    ("+123456789012345", "+123456789012345"),
    # Longest valid input: 15 digits and 14 single spaces (30 characters)
    ("+1 2 3 4 5 6 7 8 9 0 1 2 3 4 5", "+123456789012345"),
]

REJECTED_PHONES = [
    # Empty or missing parts
    "",
    "   ",
    "+",
    "+ ",
    # No plus sign / wrong plus placement
    "998901234567",
    "++998901234567",
    "+998+901234567",
    "998+901234567",
    "tel:+998901234567",
    # Digit count out of range
    "+1234567",  # 7 digits
    "+1 234 567",  # 7 digits with spaces
    "+1234567890123456",  # 16 digits
    "+1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6",  # 16 digits with spaces
    # Leading zero after the plus
    "+0123456789",
    "+0",
    # Misplaced or consecutive spaces
    "+998  90 123 45 67",
    "+ 998901234567",
    "+998 90  123 45 67",
    # Whitespace other than a single space inside the number
    "+998\t90123456",
    "+998\n90123456",
    "+998\u00a090123456",  # non-breaking space
    # Other symbols
    "+998-90-123-45-67",
    "+998.90.123.45.67",
    "+998(90)1234567",
    "(+998)901234567",
    "+998901234567a",
    "+998a901234567",
    "+998_901234567",
    "+998,901234567",
    # Non-ASCII digits
    "+99890123456\u0663",  # Arabic-Indic digit
    "+\uff11\uff12\uff13\uff14\uff15\uff16\uff17\uff18",  # fullwidth digits
    "+99890123456\u00b2",  # superscript two
]


@pytest.mark.parametrize(("raw", "expected"), ACCEPTED_PHONES)
def test_validate_phone_number_accepted(raw: str, expected: str):
    assert validate_phone_number(raw) == expected


@pytest.mark.parametrize("raw", REJECTED_PHONES)
def test_validate_phone_number_rejected(raw: str):
    with pytest.raises(PydanticCustomError) as exc_info:
        validate_phone_number(raw)

    assert exc_info.value.type == "invalid_phone_number"
