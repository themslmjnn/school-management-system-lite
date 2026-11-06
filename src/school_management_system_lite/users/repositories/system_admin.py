from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.users.models.user import User


class UserRepositoryAdmin:
    @staticmethod
    async def get_by_id(db_session: AsyncSession, user_id: int) -> User | None:
        query = select(User).where(User.id == user_id)

        result = await db_session.execute(query)

        return result.scalar_one_or_none()
