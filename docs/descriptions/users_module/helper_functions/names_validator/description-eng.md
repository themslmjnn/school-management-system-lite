# validate_name

**Module:** `users/utils/validators.py`
**Used by:** `validate_first_name`, `validate_last_name`, `validate_middle_name`
(field validators in the user schemas)

## Purpose

Validates and normalizes a name part (first, last, or middle name) before it is
stored. Guarantees clean, single-line names in one consistent form, so that
search and uniqueness behave predictably.

## Signature

    validate_name(value: str, field: str) -> str

| Parameter | Description |
|---|---|
| `value` | Raw name string submitted by the client. |
| `field` | Field identifier (`first_name`, `last_name`, `middle_name`). Used to build the error code and a readable label in the message. |

**Returns:** the normalized name.
**Raises:** `PydanticCustomError`, reported as a 422 error located at the field.

## Processing steps

1. Collapse whitespace: trim the ends and replace any run of whitespace with a
   single space.
2. Normalize Unicode to NFC, so an accented letter has one canonical form.
3. Check the length.
4. Check characters and separator placement.
5. Check that no word mixes Latin and Cyrillic letters.
6. Return the normalized value. Letter casing is preserved.

## Validation rules

| Rule | Value |
|---|---|
| Length | 3-30 characters, measured after normalization |
| Allowed letters | English (A-Z, a-z), accented Latin (À-ÖØ-öø-ÿ), Russian (А-Я, а-я, Ё, ё) |
| Allowed separators | Space, hyphen (`-`), apostrophe (`'`) |
| Digits, other symbols | Not allowed |
| Separator placement | Only between two words (letter groups) |
| Repeated or adjacent separators | Not allowed |
| Script mixing | A single word must not contain both Latin and Cyrillic letters |

## Error codes

| Code | Condition |
|---|---|
| `invalid_<field>_length` | Normalized length is outside 3-30. |
| `invalid_<field>_characters` | Disallowed character or misplaced/repeated separator. |
| `invalid_<field>_mixed_scripts` | A word contains both Latin and Cyrillic letters. |

## Examples

| Input | Result |
|---|---|
| `Anna Mary`, `van de Sarr` | Accepted |
| `Jean-Luc`, `O'Brien`, `José`, `Иван` | Accepted |
| `Anna Иванова` | Accepted (each word uses one script) |
| `  van   de   Sarr  ` | Accepted, returned as `van de Sarr` |
| `Al`, 31-character name | Rejected, length |
| `Anna1` | Rejected, characters |
| `Anna--Mary`, `Anna - Mary` | Rejected, repeated separators |
| `-Anna`, `Anna-` | Rejected, separator at an edge |
| `Аnna` (Cyrillic А) | Rejected, mixed scripts |

## Design notes

- Casing is preserved (`McDonald` stays `McDonald`).
- Length is validated here instead of `Field(min_length=...)`, because Field
  constraints run before normalization. The schema keeps only a generous
  `max_length` as an input-size guard.
- Mixed-script words are rejected to prevent look-alike characters, which break
  search and comparison.

## Limitations

- Other scripts and Latin Extended-A letters (ł, ş, č, ğ) are not supported.
- The typographic apostrophe (`’`) is not accepted; only `'`.
- Mixing scripts across different words is allowed.