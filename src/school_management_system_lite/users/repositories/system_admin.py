from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.users.models import User


async def get_users(db_session: AsyncSession) -> Sequence[User]:
    stmt = select(User)

    result = await db_session.execute(stmt)

    return result.scalars().all()
