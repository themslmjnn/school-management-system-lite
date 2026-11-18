import pytest
from pydantic_core import PydanticCustomError

from school_management_system_lite.users.utils import constants as user_constants
from school_management_system_lite.users.utils.validators import validate_address

_MIN = user_constants.ADDRESS_MIN_LENGTH
_MAX = user_constants.ADDRESS_MAX_LENGTH

LENGTH = "invalid_address_length"
CHARACTERS = "invalid_address_characters"

_BASE = "Main Street 12, Tashkent"  # 24 characters, valid for any MIN up to 24

ACCEPTED_ADDRESSES = [
    # Plain and realistic addresses
    (_BASE, _BASE),
    ("Tashkent, Chilanzar 7, apt. 12/3", "Tashkent, Chilanzar 7, apt. 12/3"),
    ("12 Main St., Apt #4-B", "12 Main St., Apt #4-B"),
    ("P.O. Box 123 (north)", "P.O. Box 123 (north)"),
    # Any script is allowed
    ("Ташкент, ул. Навои, д. 5", "Ташкент, ул. Навои, д. 5"),
    ("Rue de l'Église 3, Zürich", "Rue de l'Église 3, Zürich"),
    ("东京都 新宿区 1-1 丁目 2-3", "东京都 新宿区 1-1 丁目 2-3"),
    # Casing is preserved
    ("main STREET 12, tashkent", "main STREET 12, tashkent"),
    # Whitespace is collapsed and trimmed
    ("  Main   Street   12,   Tashkent  ", _BASE),
    ("Main\tStreet\n12, Tashkent", _BASE),
    ("Main\r\nStreet 12, Tashkent", _BASE),
    ("Main\u00a0Street 12, Tashkent", _BASE),  # non-breaking space
    ("Main\u2003Street 12, Tashkent", _BASE),  # em space
    # Control characters that count as whitespace are collapsed, not rejected
    ("Main\x1cStreet 12, Tashkent", _BASE),
    ("Main\x85Street 12, Tashkent", _BASE),
    # Invisible characters outside the "Cc" category are not rejected (current behavior)
    ("Main\u200bStreet 12, Tashkent", "Main\u200bStreet 12, Tashkent"),
    # Length boundaries
    ("a" * _MIN, "a" * _MIN),
    ("a" * _MAX, "a" * _MAX),
    # Length is measured after normalization
    ("  " + "a" * _MAX + "  ", "a" * _MAX),
    ("a" * _MAX + "\n\t ", "a" * _MAX),
    ("a" * _MIN + " " * 500, "a" * _MIN),
]

EMPTY_ADDRESSES = [
    "",
    " ",
    "     ",
    "\t",
    "\n",
    "\r\n",
    " \t \n ",
    "\u00a0",
    "\u2003",
    "\x85",
    "\x1c",
]

CONTROL_CHARACTER_ADDRESSES = [
    _BASE + "\x00",
    "\x00" + _BASE,
    "Main\x00Street 12, Tashkent",
    _BASE + "\x07",  # bell
    _BASE + "\x1b",  # escape
    _BASE + "\x7f",  # delete
    _BASE + "\x9f",  # C1 control
    "Main\x00\x00Street 12, Tashkent",
    "\x00" * _MIN,
]


@pytest.mark.parametrize(("raw", "expected"), ACCEPTED_ADDRESSES)
def test_validate_address_accepted(raw: str, expected: str):
    assert validate_address(raw) == expected


@pytest.mark.parametrize("raw", EMPTY_ADDRESSES)
def test_validate_address_empty_or_whitespace_returns_none(raw: str):
    assert validate_address(raw) is None


@pytest.mark.parametrize("raw", CONTROL_CHARACTER_ADDRESSES)
def test_validate_address_rejects_control_characters(raw: str):
    with pytest.raises(PydanticCustomError) as exc_info:
        validate_address(raw)

    assert exc_info.value.type == CHARACTERS


@pytest.mark.skipif(_MIN < 2, reason="needs a minimum length of at least 2")
def test_validate_address_below_min_length_rejected():
    with pytest.raises(PydanticCustomError) as exc_info:
        validate_address("a" * (_MIN - 1))

    assert exc_info.value.type == LENGTH
    assert exc_info.value.message() == (f"Address must be at least {_MIN} characters")


@pytest.mark.skipif(_MIN < 2, reason="needs a minimum length of at least 2")
def test_validate_address_min_length_counts_collapsed_text():
    # Looks long, but collapses to fewer than _MIN characters
    padded = "a" + " " * 50 + "\t" * 50

    assert len(padded) > _MIN

    with pytest.raises(PydanticCustomError) as exc_info:
        validate_address(padded)

    assert exc_info.value.type == LENGTH


def test_validate_address_above_max_length_rejected():
    with pytest.raises(PydanticCustomError) as exc_info:
        validate_address("a" * (_MAX + 1))

    assert exc_info.value.type == LENGTH
    assert exc_info.value.message() == (f"Address must be at most {_MAX} characters")


def test_validate_address_max_length_counts_collapsed_text():
    # Internal whitespace runs collapse to one space, so this fits exactly
    address = "a" * (_MAX // 2) + " " * 40 + "b" * (_MAX - _MAX // 2 - 1)

    assert len(address) > _MAX
    assert len(" ".join(address.split())) == _MAX

    assert validate_address(address) == " ".join(address.split())


def test_validate_address_collapsed_spaces_can_push_over_max():
    # Exactly _MAX characters, but the single spaces between letters stay
    # single spaces, so adding one more word makes it too long
    address = ("a " * _MAX)[: _MAX + 1].strip() + "bb"

    with pytest.raises(PydanticCustomError) as exc_info:
        validate_address(address)

    assert exc_info.value.type == LENGTH


@pytest.mark.skipif(_MIN < 2, reason="needs a minimum length of at least 2")
def test_validate_address_length_error_wins_over_control_character_error():
    # Pins the order of the checks: length first, then characters
    with pytest.raises(PydanticCustomError) as exc_info:
        validate_address("\x00" * (_MIN - 1))

    assert exc_info.value.type == LENGTH


def test_validate_address_control_character_inside_max_length_address():
    with pytest.raises(PydanticCustomError) as exc_info:
        validate_address("a" * (_MAX - 1) + "\x00")

    assert exc_info.value.type == CHARACTERS


def test_validate_address_is_idempotent():
    once = validate_address("  12   Main \n Street,   Tashkent  ")

    assert once == "12 Main Street, Tashkent"
    assert validate_address(once) == once
