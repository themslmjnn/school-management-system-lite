# validate_phone_number

**Module:** `users/utils/validators.py`
**Used by:** the `phone_number` field validator in the user schemas
(`CreateUserAdmin` and the profile-update schemas)

## Purpose

Validates a phone number submitted in international format and normalizes it to
a canonical form (`+` followed by digits, no spaces). The canonical form is what
is stored, so the unique constraint on `users.phone_number` compares like with
like regardless of how the number was typed.

## Signature

    validate_phone_number(phone_number: str) -> str

**Returns:** the normalized number, for example `+998901234567`.
**Raises:** `PydanticCustomError` with code `invalid_phone_number`, reported as a
422 error located at the field.

## Processing steps

1. Trim leading and trailing whitespace.
2. Check the format of the trimmed value: `+`, a non-zero digit, then digits,
   optionally separated by single spaces.
3. Remove the spaces and count the digits.
4. Check that the digit count is within the allowed range.
5. Return `+` followed by the digits.

## Validation rules

| Rule | Value |
|---|---|
| Prefix | Must start with `+` |
| Digit count | 8-15, `+` and spaces not counted (`PHONE_MIN_DIGITS`, `PHONE_MAX_DIGITS`) |
| First digit | 1-9 (country codes do not start with 0) |
| Allowed characters | ASCII digits 0-9, single spaces, one leading `+` |
| Spaces | Only between two digits; no consecutive, leading-after-plus, or trailing spaces |
| Any other symbol | Not allowed (hyphens, parentheses, dots, letters, non-ASCII digits) |

## Error code

| Code | Condition |
|---|---|
| `invalid_phone_number` | Any rule above is violated. |

## Examples

| Input | Result |
|---|---|
| `+998901234567` | Accepted |
| `+998 90 123 45 67` | Accepted, returned as `+998901234567` |
| `  +7 999 123 45 67 ` | Accepted, returned as `+79991234567` |
| `+12345678` / `+123456789012345` | Accepted (8 / 15 digits) |
| `998901234567` | Rejected, no `+` |
| `+1234567` / `+1234567890123456` | Rejected, 7 / 16 digits |
| `+0123456789` | Rejected, leading 0 |
| `+998  90 123 45 67` | Rejected, consecutive spaces |
| `+ 998901234567` | Rejected, space after `+` |
| `+998-90-123-45-67` | Rejected, hyphen |

## Design notes

- The format is checked on the original string, because removing spaces first
  would hide consecutive or misplaced spaces.
- The stored value is at most 16 characters, which fits the `String(20)` column.
- The schema keeps only `max_length=30` as an input-size guard. That is the
  longest valid input (`+`, 15 digits, 14 single spaces). Real validation is here.
- `[0-9]` is used instead of `\d`, so look-alike non-ASCII digits cannot bypass
  the unique constraint.

## Limitations

- The number is not checked against real country codes or national formats.
- Different notations of the same number (for example a local prefix vs. the
  international one) are treated as different numbers.