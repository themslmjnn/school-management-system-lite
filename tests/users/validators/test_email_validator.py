import pytest
from pydantic_core import PydanticCustomError

from school_management_system_lite.users.utils import constants as user_constants
from school_management_system_lite.users.utils.validators import validate_email

_MAX = user_constants.EMAIL_MAX_LENGTH
# "@x.com" is 6 characters, so this builds an address of exactly _MAX characters
_MAX_LENGTH_EMAIL = "a" * (_MAX - 6) + "@x.com"
_TOO_LONG_EMAIL = "a" * (_MAX - 5) + "@x.com"

ACCEPTED_EMAILS = [
    # Basic forms
    ("a@x.com", "a@x.com"),
    ("a.b@x.com", "a.b@x.com"),
    ("a.b.c@x.com", "a.b.c@x.com"),
    ("anna_ivanova@my-school.edu", "anna_ivanova@my-school.edu"),
    ("user123@school.edu", "user123@school.edu"),
    # Underscore and digits are allowed anywhere in the name part
    ("_a@x.com", "_a@x.com"),
    ("a_@x.com", "a_@x.com"),
    ("__@x.com", "__@x.com"),
    ("1@x.com", "1@x.com"),
    ("1.2@x.com", "1.2@x.com"),
    # Lowercasing
    ("A@X.COM", "a@x.com"),
    ("Anna.Ivanova@School.EDU", "anna.ivanova@school.edu"),
    # Trimming
    ("  a@x.com  ", "a@x.com"),
    ("\ta@x.com\n", "a@x.com"),
    # Domain variations
    ("a@sub.domain.example.org", "a@sub.domain.example.org"),
    ("a@x-y.com", "a@x-y.com"),
    ("a@x--y.com", "a@x--y.com"),
    ("a@1x.com", "a@1x.com"),
    ("a@a.aa", "a@a.aa"),
    ("a@x.museum", "a@x.museum"),
    ("a@xn--80ak6aa92e.com", "a@xn--80ak6aa92e.com"),  # punycode label, normal TLD
    # Length boundary: exactly EMAIL_MAX_LENGTH characters
    (_MAX_LENGTH_EMAIL, _MAX_LENGTH_EMAIL),
    # Length is measured after trimming
    (_MAX_LENGTH_EMAIL + " ", _MAX_LENGTH_EMAIL),
    (" " * 100 + _MAX_LENGTH_EMAIL + " " * 100, _MAX_LENGTH_EMAIL),
]

REJECTED_EMAILS = [
    # Empty or incomplete
    "",
    "   ",
    "@",
    "a",
    "plainaddress",
    "a@",
    "@x.com",
    "a@x",
    "a@localhost",
    # Wrong number of @
    "a@@x.com",
    "a@b@x.com",
    "a@x.com@",
    "@a@x.com",
    # Whitespace inside
    "a b@x.com",
    "a@x .com",
    "a@x.c om",
    "a@x.com b",
    "a\n@x.com",
    "a\u00a0@x.com",  # non-breaking space inside
    # Misplaced dots in the name part
    "a..b@x.com",
    ".a@x.com",
    "a.@x.com",
    ".@x.com",
    # Invalid domain structure
    "a@x..com",
    "a@.x.com",
    "a@x.com.",
    "a@.com",
    "a@x.",
    # Hyphens in the domain
    "a@-x.com",
    "a@x-.com",
    "a@x.-com",
    # Invalid domain ending (TLD must be 2+ English letters only)
    "a@x.c",
    "a@x.c1",
    "a@x.123",
    "a@x.c-m",
    "a@x.xn--p1ai",
    "a@1.2.3.4",
    # Characters not allowed in the domain
    "a@_x.com",
    "a@x_y.com",
    "a@x.com/path",
    "a@[1.2.3.4]",
    # Characters not allowed in the name part
    "user+tag@x.com",
    "user-name@x.com",
    "a,b@x.com",
    "a!b@x.com",
    "a'b@x.com",
    "a:b@x.com",
    '"a"@x.com',
    "<a@x.com>",
    "mailto:a@x.com",
    "a@x.com,",
    # Non-English letters
    "анна@x.com",
    "a@школа.рф",
    "josé@x.com",
    "a@x.cöm",
    # Control and invisible characters
    "a\x00@x.com",
    "a\u200b@x.com",
    # Length: one over the limit
    _TOO_LONG_EMAIL,
    _TOO_LONG_EMAIL + " ",
]


@pytest.mark.parametrize(("raw", "expected"), ACCEPTED_EMAILS)
def test_validate_email_accepted(raw: str, expected: str):
    assert validate_email(raw) == expected


@pytest.mark.parametrize("raw", REJECTED_EMAILS)
def test_validate_email_rejected(raw: str):
    with pytest.raises(PydanticCustomError) as exc_info:
        validate_email(raw)

    assert exc_info.value.type == "invalid_email"
