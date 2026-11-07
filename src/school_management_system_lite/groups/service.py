from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.groups.exceptions import (
    handle_duplicate_group_integrity_error,
)
from school_management_system_lite.groups.models import Group
from school_management_system_lite.groups.schemas import CreateGroup


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
