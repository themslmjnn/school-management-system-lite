from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.users.models.user import User


class UserRepositoryBase:
    @staticmethod
    async def get_by_email(db_session: AsyncSession, email: str) -> User | None:
        query = select(User).where(User.email == email)

        result = await db_session.execute(query)

        return result.scalar_one_or_none()
