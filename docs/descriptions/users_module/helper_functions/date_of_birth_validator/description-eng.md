# validate_date_of_birth

**Module:** `users/utils/validators.py`
**Functions:** `validate_date_of_birth_student`, `validate_date_of_birth_non_student`
(both delegate to the private `_validate_date_of_birth`)
**Used by:** the `date_of_birth` field validator on `CreateUserAdmin` and any
profile-update schema that accepts a birth date.

## Purpose

Checks that a submitted date of birth is a real past date and that the resulting
age falls within the allowed range for the user's category (student or
non-student). Age is calculated against the current date in the school's
timezone.

## Signatures

    validate_date_of_birth_student(birth_date: date, today: date | None = None) -> date
    validate_date_of_birth_non_student(birth_date: date, today: date | None = None) -> date

| Parameter | Description |
|---|---|
| `birth_date` | Date of birth submitted by the client. |
| `today` | Optional reference date. Production code omits it, so the school's current date is used. Tests pass a fixed date instead of mocking the clock. |

**Returns:** `birth_date` unchanged.
**Raises:** `PydanticCustomError`, reported as a 422 error located at `date_of_birth`.

## Age limits

| Category | Roles | Minimum age | Maximum age | Constants |
|---|---|---|---|---|
| Student | `STUDENT` | 6 | 21 | `STUDENT_MIN_AGE`, `STUDENT_MAX_AGE` |
| Non-student | `TEACHER`, `DIRECTOR` | 19 | 70 | `NON_STUDENT_MIN_AGE`, `NON_STUDENT_MAX_AGE` |

Limits are inclusive: a person who is exactly 6 (student) or exactly 70
(non-student) is accepted. The ranges overlap at 19-21, so the role alone decides
which range applies.

## Processing steps

1. Determine "today" once: the `today` argument if given, otherwise the current
   date in `SCHOOL_TIMEZONE` (`school_today()`).
2. Reject the value if `birth_date >= today`.
3. Calculate the age in whole years: the year difference, minus one if the
   birthday has not yet occurred this year.
4. Reject the value if the age is below the minimum or above the maximum.
5. Return `birth_date`.

"Today" is computed once and reused, so the checks cannot disagree around midnight.

## Error codes

| Code | Message | Condition |
|---|---|---|
| `date_of_birth_not_in_past` | Date of birth must be in the past | `birth_date` is today or in the future. |
| `date_of_birth_too_young` | `<Student/User>` must be at least N years old | Age is below the minimum. |
| `date_of_birth_too_old` | `<Student/User>` must be N years old or younger | Age is above the maximum. |

## Role selection

The schema field validator picks the function by role. `role` is declared before
`date_of_birth` in `CreateUserAdmin`, so it is already validated when the birth
date is checked. If `role` itself is invalid, the birth-date check is skipped and
only the role error is reported.

## Configuration

| Setting | Purpose |
|---|---|
| `SCHOOL_TIMEZONE` | IANA timezone name (for example `Asia/Tashkent`). Validated at startup, so a typo stops the app from starting. Requires the `tzdata` package on Windows. |

## Examples (today = 2026-03-10)

| Birth date | Student | Non-student |
|---|---|---|
| `2026-03-10` | Rejected, not in past | Rejected, not in past |
| `2020-03-10` (age 6) | Accepted | Rejected, too young |
| `2020-03-11` (age 5) | Rejected, too young | Rejected, too young |
| `2004-03-11` (age 21) | Accepted | Accepted |
| `2004-03-10` (age 22) | Rejected, too old | Accepted |
| `1955-03-11` (age 70) | Rejected, too old | Accepted |
| `1955-03-10` (age 71) | Rejected, too old | Rejected, too old |

## Design notes

- Dates of birth have no time component. Only the reference "today" depends on a
  timezone, and it uses the school's local date, not UTC, so the result matches
  what school staff see.
- The error is raised from a field validator, so the client can attach it to the
  `date_of_birth` field.
- Age limits are constants in `user_constants`, not literals in the logic.

## Limitations

- Age is calculated for the registration date only; it is not rechecked later
  (for example when a student passes the maximum age).
- A single school timezone is supported.