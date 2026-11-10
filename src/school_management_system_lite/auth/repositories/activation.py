from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.auth.models.activation import UserActivation


class UserActivationRepository:
    @staticmethod
    async def get_by_user_id(
        db_session: AsyncSession, user_id: int
    ) -> UserActivation | None:
        stmt = select(UserActivation).where(UserActivation.user_id == user_id)

        result = await db_session.execute(stmt)

        return result.scalar_one_or_none()
