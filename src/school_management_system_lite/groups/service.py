from collections.abc import Sequence

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.groups.exceptions import (
    GroupNotFound,
    handle_duplicate_group_integrity_error,
)
from school_management_system_lite.groups.models import Group
from school_management_system_lite.groups.repository import GroupRepository
from school_management_system_lite.groups.schemas import (
    CreateGroup,
    UpdateGroup,
)


class GroupService:
    @staticmethod
    async def create_group(db_session: AsyncSession, payload: CreateGroup) -> Group:
        try:
            new_group = Group(**payload.model_dump())

            db_session.add(new_group)
            await db_session.commit()
            await db_session.refresh(new_group)

        except IntegrityError as exc:
            await db_session.rollback()

            handle_duplicate_group_integrity_error(exc)

            raise

        return new_group

    @staticmethod
    async def update_group(
        db_session: AsyncSession, group_id: int, payload: UpdateGroup
    ) -> Group:
        group = await GroupRepository.get_by_id(db_session, group_id)
        if group is None:
            raise GroupNotFound()

        try:
            for field, value in payload.model_dump(exclude_unset=True).items():
                setattr(group, field, value)

            await db_session.commit()
            await db_session.refresh(group)

        except IntegrityError as exc:
            await db_session.rollback()

            handle_duplicate_group_integrity_error(exc)

            raise

        return group

    @staticmethod
    async def get_groups(db_session: AsyncSession) -> Sequence[Group]:
        return await GroupRepository.get_groups(db_session)

    @staticmethod
    async def get_group(db_session: AsyncSession, group_id: int) -> Group:
        group = await GroupRepository.get_by_id(db_session, group_id)
        if group is None:
            raise GroupNotFound()

        return group
