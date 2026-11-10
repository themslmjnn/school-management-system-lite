from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.users.models.user import User
from school_management_system_lite.utils.enums import UserRole


class UserRepositoryAdmin:
    @staticmethod
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

    @staticmethod
    async def get_users(db_session: AsyncSession) -> Sequence[User]:
        stmt = select(User)

        result = await db_session.execute(stmt)

        return result.scalars().all()
