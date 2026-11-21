from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.users.models.email_changes import UserEmailChange


async def get_by_user_id(
    db_session: AsyncSession, user_id: int
) -> UserEmailChange | None:
    stmt = select(UserEmailChange).where(UserEmailChange.user_id == user_id)

    result = await db_session.execute(stmt)

    return result.scalar_one_or_none()
