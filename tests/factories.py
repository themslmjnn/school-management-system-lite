import itertools
from datetime import UTC, date, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.auth.models.activation import UserActivation
from school_management_system_lite.auth.models.session import UserSession
from school_management_system_lite.core.config import get_settings
from school_management_system_lite.core.security import generate_token, hash_password
from school_management_system_lite.users.models import User
from school_management_system_lite.users.utils.enums import UserRole, UserStatus

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
        first_name=first_name or "Test-First-Name",
        last_name=last_name or "Test-Last-Name",
        middle_name=middle_name or "Test-Middle-Name",
        date_of_birth=date_of_birth
        if date_of_birth is not None
        else (date(2008, 1, 1) if role == UserRole.STUDENT else date(2000, 1, 1)),
        address=address or "Test address",
        phone_number=phone_number or f"+992{n:09d}",
        email=email or f"user_{n}@example.com",
        role=role,
        status=status,
        password_hash=hash_password(password) if password else None,
    )

    test_db_session.add(user)
    await test_db_session.flush()

    _, activation_token_hash = generate_token()

    if status == UserStatus.PENDING_ACTIVATION:
        new_activation = UserActivation(
            user_id=user.id,
            activation_token_hash=activation_token_hash,
            activation_token_expires_at=(
                datetime.now(UTC)
                + timedelta(hours=get_settings().ACTIVATION_TOKEN_EXPIRES_HOURS)
            ),
        )

        test_db_session.add(new_activation)

    test_db_session.add(UserSession(user_id=user.id))

    await test_db_session.flush()

    return user


async def make_system_admin(test_db_session: AsyncSession, **kwargs) -> User:
    return await make_user(
        test_db_session,
        role=UserRole.SYSTEM_ADMIN,
        **kwargs,
    )


async def make_director(test_db_session: AsyncSession, **kwargs) -> User:
    return await make_user(
        test_db_session,
        role=UserRole.DIRECTOR,
        **kwargs,
    )


async def make_teacher(test_db_session: AsyncSession, **kwargs) -> User:
    return await make_user(
        test_db_session,
        role=UserRole.TEACHER,
        **kwargs,
    )


async def make_student(test_db_session: AsyncSession, **kwargs) -> User:
    return await make_user(
        test_db_session,
        role=UserRole.STUDENT,
        **kwargs,
    )
