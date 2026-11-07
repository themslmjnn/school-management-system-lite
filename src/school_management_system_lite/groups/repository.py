from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.groups.models import Group


class GroupRepository:
    @staticmethod
    async def get_by_id(db_session: AsyncSession, group_id: int) -> Group | None:
        query = select(Group).where(Group.id == group_id)

        result = await db_session.execute(query)

        return result.scalar_one_or_none()

    @staticmethod
    async def get_groups(db_session: AsyncSession) -> Sequence[Group]:
        query = select(Group)

        result = await db_session.execute(query)

        return result.scalars().all()
