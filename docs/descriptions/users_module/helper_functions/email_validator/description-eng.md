# validate_email

**Module:** `users/utils/validators.py`
**Used by:** the `email` field validator in the user schemas
(`CreateUserAdmin` and the email-update schema)

## Purpose

Validates an email address and normalizes it to lowercase with surrounding
whitespace removed. The normalized value is what is stored, so the unique
constraint on `users.email` treats `Anna@School.com` and `anna@school.com` as
the same address.

## Signature

    validate_email(email: str) -> str

**Returns:** the normalized email.
**Raises:** `PydanticCustomError` with code `invalid_email`, reported as a 422
error located at the field.

## Processing steps

1. Trim whitespace and convert to lowercase.
2. Check the length of the normalized value.
3. Check the whole value against the allowed pattern.
4. Return the normalized value.

## Validation rules

| Rule | Value |
|---|---|
| Maximum length | 50 characters, measured after normalization (`EMAIL_MAX_LENGTH`, matches the `String(50)` column) |
| `@` sign | Exactly one |
| Name part (before `@`) | English letters, digits, `_` and `.`; must not start or end with `.`; no consecutive dots |
| Domain part (after `@`) | Labels of English letters, digits and hyphens separated by dots; a label must not start or end with a hyphen |
| Domain ending | At least one dot; the last label is 2 or more English letters |
| Other symbols | Not allowed (`+`, `-` in the name part, spaces, non-English letters) |

## Error code

| Code | Condition |
|---|---|
| `invalid_email` | The email is too long or violates any format rule above. |

## Examples

| Input | Result |
|---|---|
| `anna_ivanova@my-school.edu` | Accepted |
| `a.b@x.com` | Accepted |
| `A@X.COM` | Accepted, returned as `a@x.com` |
| `  a@x.com  ` | Accepted, returned as `a@x.com` |
| `a@@x.com` | Rejected, two `@` |
| `a..b@x.com`, `.a@x.com`, `a.@x.com` | Rejected, misplaced dots |
| `a@x..com`, `a@-x.com`, `a@x.com.` | Rejected, invalid domain |
| `a@x`, `a@x.c` | Rejected, no valid domain ending |
| `user+tag@x.com`, `user-name@x.com` | Rejected, symbol not allowed in the name part |
| `анна@x.com` | Rejected, non-English letters |
| 51-character email | Rejected, length |

## Design notes

- The input is lowercased before matching, so the pattern only lists lowercase
  letters and the stored value is canonical.
- The length is checked after trimming, so stray whitespace cannot cause a
  false rejection. The schema keeps a generous `max_length` as an input-size
  guard.
- The rules are deliberately stricter than the email standard (RFC 5322) in the
  name part. Hyphens are allowed only in the domain.
- The address is also used to deliver the activation link, so the format check
  prevents accounts that can never be activated because of a malformed address.
- The check proves only that the format is valid, not that the mailbox exists.

## Limitations

- Addresses with `+` or `-` in the name part, quoted names, IP-address domains
  and internationalized (non-English) addresses are rejected.
- Domain endings containing digits or hyphens (for example punycode) are rejected.
- Mailbox existence is not verified.