from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.subjects.exceptions import (
    handle_subject_code_integrity_error,
)
from school_management_system_lite.subjects.models import Subject
from school_management_system_lite.subjects.schemas import CreateSubject


class SubjectService:
    @staticmethod
    async def create_subject(
        db_session: AsyncSession, payload: CreateSubject
    ) -> Subject:
        try:
            new_subject = Subject(
                name=payload.name,
                code=payload.code,
                description=payload.description,
            )

            db_session.add(new_subject)
            await db_session.commit()
            await db_session.refresh(new_subject)

        except IntegrityError as exc:
            await db_session.rollback()

            handle_subject_code_integrity_error(exc)

            raise

        return new_subject
