# validate_address

**Module:** `users/utils/validators.py`
**Used by:** the `address` field validator in the user schemas
(`CreateUserAdmin` and the profile-update schema)

## Purpose

Normalizes the optional address so that only clean, single-line text is stored.
Empty or whitespace-only input is treated as "no address".

## Signature

    validate_address(cls, address: str) -> str | None

**Returns:** the normalized address.
**Raises:** `PydanticCustomError`, reported as a 422 error located at `address`.

## Processing steps

1. Collapse whitespace: trim the ends and replace any run of whitespace
   (spaces, tabs, line breaks) with a single space.
2. If nothing remains, return `None`.
3. Check the length of the normalized value.
4. Reject the value if it contains control characters.
5. Return the normalized value.

## Validation rules

| Rule | Value |
|---|---|
| Presence | Optional |
| Maximum length | 150 characters, measured after normalization (`ADDRESS_MAX_LENGTH`, matches the `String(150)` column) |
| Whitespace | Collapsed to single spaces; the result is one line |
| Empty or whitespace-only | Stored as `NULL`, never as an empty string |
| Control characters | Not allowed (for example `\x00`) |
| Other characters | Not restricted: letters of any script, digits, and punctuation such as `,` `/` `#` are allowed |

## Error codes

| Code | Condition |
|---|---|
| `invalid_address_length` | Normalized length exceeds 150. |
| `invalid_address_characters` | Contains a control character. |

## Examples

| Input | Result |
|---|---|
| `"   "` | `None` |
| `"  12  Main \n St  "` | Accepted, returned as `12 Main St` |
| `"Tashkent, Chilanzar 7, apt. 12/3"` | Accepted |
| 150-character address | Accepted |
| 151-character address | Rejected, length |
| `"Main St\x00"` | Rejected, control character |

## Design notes

- Length is validated here, not with `Field(max_length=150)`, because a Field
  constraint runs before normalization and would count padding. The schema keeps
  a generous `max_length` (200) only as an input-size guard.
- Empty strings become `None`, so the column holds either a real address or
  `NULL`.
- Control characters are rejected because PostgreSQL cannot store `\x00` in text
  columns; without this check such input causes a 500 error.
- The character set is deliberately not restricted, because real addresses
  contain many symbols and scripts.

## Limitations

- There is no check that the address is real.
- Line breaks inside an address are not preserved.