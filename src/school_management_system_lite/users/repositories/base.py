from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.users.models import User
from school_management_system_lite.users.utils.enums import UserRole


async def get_by_id(
    db_session: AsyncSession,
    user_id: int,
    excluded_roles: frozenset[UserRole] | None = None,
    allowed_roles: frozenset | None = None,
) -> User | None:
    stmt = select(User).where(User.id == user_id)

    if excluded_roles:
        stmt = stmt.where(User.role.not_in(excluded_roles))

    if allowed_roles:
        stmt = stmt.where(User.role.in_(allowed_roles))

    result = await db_session.execute(stmt)

    return result.scalar_one_or_none()


async def get_by_email(db_session: AsyncSession, email: str) -> User | None:
    stmt = select(User).where(User.email == email)

    result = await db_session.execute(stmt)

    return result.scalar_one_or_none()
