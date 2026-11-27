import itertools
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.auth.models.activation import UserActivation
from school_management_system_lite.auth.models.session import UserSession
from school_management_system_lite.core.config import get_settings
from school_management_system_lite.core.security import generate_token, hash_password
from school_management_system_lite.users.models.user import User
from school_management_system_lite.users.schemas.system_admin import CreateUserAdmin
from school_management_system_lite.users.utils.enums import UserRole, UserStatus
from school_management_system_lite.users.utils.helpers import school_today

_counter = itertools.count(1)


def _next() -> int:
    return next(_counter)


async def make_user(
    test_db_session: AsyncSession,
    *,
    role: UserRole = UserRole.STUDENT,
    status: UserStatus = UserStatus.ACTIVE,
    first_name: str | None = None,
    last_name: str | None = None,
    middle_name: str | None = None,
    date_of_birth: date | None = None,
    address: str | None = None,
    email: str | None = None,
    phone_number: str | None = None,
    password: str | None = "TestPassword_123!",
) -> User:
    n = _next()

    user = User(
        first_name=first_name or "Test-Firstname",
        last_name=last_name or "Test-Lastname",
        middle_name=middle_name or "Test-Middlename",
        date_of_birth=date_of_birth
        if date_of_birth is not None
        else (date(2008, 1, 1) if role == UserRole.STUDENT else date(2000, 1, 1)),
        address=address or "Test user address",
        phone_number=phone_number or f"+992{n:09d}",
        email=email or f"user_{n}@example.com",
        role=role,
        status=status,
        password_hash=await hash_password(password)
        if password and status != UserStatus.PENDING_ACTIVATION
        else None,
    )

    test_db_session.add(user)
    await test_db_session.flush()

    _, activation_token_hash = generate_token()

    if status == UserStatus.PENDING_ACTIVATION:
        activation = UserActivation(
            user_id=user.id,
            activation_token_hash=activation_token_hash,
            activation_token_expires_at=(
                datetime.now(UTC)
                + timedelta(hours=get_settings().ACTIVATION_TOKEN_EXPIRES_HOURS)
            ),
        )

        test_db_session.add(activation)

    test_db_session.add(UserSession(user_id=user.id))

    await test_db_session.flush()

    return user


def make_create_user_payload(
    *, role: UserRole = UserRole.STUDENT, **overrides: Any
) -> CreateUserAdmin:
    """Build a valid, validated CreateUserAdmin payload for the given role.

    The birth date is derived from today's school date, so the payload
    never becomes invalid as time passes. Any field can be overridden.
    """

    n = _next()

    age = 15 if role == UserRole.STUDENT else 35

    fields: dict[str, Any] = {
        "first_name": "Test-Firstname",
        "last_name": "Test-Lastname",
        "middle_name": "Test-Middlename",
        "date_of_birth": date(school_today().year - age, 6, 15),
        "address": "Test payload address",
        "phone_number": f"+992{n:09d}",
        "email": f"new_user_{n}@example.com",
        "role": role,
    }

    fields.update(overrides)

    return CreateUserAdmin.model_validate(fields)
