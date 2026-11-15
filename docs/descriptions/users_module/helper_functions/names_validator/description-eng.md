# validate_name

**Module:** `users/utils/validators.py`
**Used by:** `validate_first_name`, `validate_last_name`, `validate_middle_name`

## Purpose

Validates and normalizes a name part (first, last, or middle name) so that
stored names are clean, single-line, and consistently capitalized.

## Signature

    validate_name(value: str, field: str) -> str

| Parameter | Description |
|---|---|
| `value` | Raw name submitted by the client. |
| `field` | `first_name`, `last_name` or `middle_name`. Used for the error code and message label. |

**Returns:** the normalized name.
**Raises:** `PydanticCustomError`, reported as a 422 error located at the field.

## Processing steps

1. Trim the ends and collapse any whitespace run into one space.
2. Check the total length.
3. Check the structure against the allowed pattern.
4. Capitalize each letter group (first letter upper case, the rest lower case).

## Validation rules

| Rule | Value |
|---|---|
| Length | 2-30 characters in total, spaces and separators included |
| Letters | English only (A-Z, a-z) |
| Words | 1 to 3, separated by exactly one space |
| Letters per group | At least 2, including the parts before and after a hyphen or apostrophe |
| Separators inside a word | At most one hyphen (`-`) or straight apostrophe (`'`) per word, only between two letter groups, no spaces around it |
| Digits, other symbols | Not allowed |

## Error codes

| Code | Condition |
|---|---|
| `invalid_<field>_length` | Normalized length is outside 2-30. |
| `invalid_<field>_characters` | Structure or characters violate the rules. |

The length check runs first, so an empty value, a single letter, or a value
over 30 characters reports the length error.

## Examples

| Input | Result |
|---|---|
| `umar`, `UMAR`, `UmAr` | Accepted, `Umar` |
| `  Umar   Ali  `, `Umar<TAB>Ali` | Accepted, `Umar Ali` |
| `Umar Ali Name` | Accepted |
| `umar-ali` | Accepted, `Umar-Ali` |
| `Umar'Ali` | Accepted |
| `Umar-Ali Smith-Jones` | Accepted (one separator per word) |
| `Um` | Accepted |
| `LessThanThirtyOneNames` | Accepted, `Lessthanthirtyonenames` |
| empty, spaces only, `U` | Rejected, length |
| 31+ characters | Rejected, length |
| `Umar Ali Name Extra` | Rejected, 4 words |
| `Umar - Ali`, `Umar -Ali`, `Umar- Ali`, `Umar ' Ali` | Rejected, spaces around a separator |
| `-Umarali`, `Umarali-`, `'Umarali`, `Umarali'` | Rejected, separator at an edge |
| `Umar--Ali`, `Umar''Ali` | Rejected, repeated separator |
| `U-mar-Ali`, `U'mar'Ali`, `U'mar-Ali` | Rejected, two separators in one word |
| `U'mar`, `Um-m`, `Um m`, `Umar A` | Rejected, a letter group under 2 letters |
| `O'Brien`, `D'Angelo` | Rejected, a letter group under 2 letters |
| `Umar’Ali`, `Umar—Ali` | Rejected, not a straight apostrophe or hyphen |
| `Умарали`, `Ùmäřáľ` | Rejected, non-English letters |
| `123Umarali`, `Umar123ali`, `Umarali123` | Rejected, digits |
| `Umar_Ali`, `~!@#$%Umarali` | Rejected, symbols |

## Design notes

- Length is validated here, not with `Field(min_length=...)`, because Field
  constraints run before normalization. The schema keeps only a generous
  `max_length` as an input-size guard.
- Forced capitalization keeps stored names consistent for search and display.
- The 30-character limit matches the `String(30)` column, so no value can
  overflow it.
- The "2 letters per group" rule is applied to each letter group, which keeps
  the pattern simple.

## Limitations

- Names with a one-letter prefix, such as `O'Brien` and `D'Angelo`, cannot be
  registered.
- Capitalization is forced: `McDonald` becomes `Mcdonald`, and `van de Sarr`
  becomes `Van De Sarr`.
- Single-letter words (`A`, `J`), accented and non-English letters, and the
  typographic apostrophe (`’`) are not accepted.
- Names of more than three words are not accepted.