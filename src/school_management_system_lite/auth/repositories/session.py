from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.auth.models.session import UserSession


class UserSessionRepository:
    @staticmethod
    async def get_by_user_id(db_session: AsyncSession, user_id: int) -> UserSession:
        query = select(UserSession).where(UserSession.user_id == user_id)

        result = await db_session.execute(query)

        return result.scalar_one()

    @staticmethod
    async def get_by_id(db_session: AsyncSession, session_id: int) -> UserSession:
        query = select(UserSession).where(UserSession.id == session_id)

        result = await db_session.execute(query)

        return result.scalar_one()
