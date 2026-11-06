from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.subjects.models import Subject


class SubjectRepository:
    @staticmethod
    async def get_by_id(db_session: AsyncSession, subject_id: int) -> Subject | None:
        query = select(Subject).where(Subject.id == subject_id)

        result = await db_session.execute(query)

        return result.scalar_one_or_none()
