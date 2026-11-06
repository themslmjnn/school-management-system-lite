from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.subjects.exceptions import (
    SubjectAlreadyArchivedError,
    SubjectNotArchivedError,
    SubjectNotFoundError,
    handle_subject_code_integrity_error,
)
from school_management_system_lite.subjects.models import Subject
from school_management_system_lite.subjects.repository import SubjectRepository
from school_management_system_lite.subjects.schemas import CreateSubject, UpdateSubject


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

    @staticmethod
    async def update_subject(
        db_session: AsyncSession, subject_id: int, payload: UpdateSubject
    ) -> Subject:
        subject = await SubjectRepository.get_by_id(db_session, subject_id)
        if subject is None:
            raise SubjectNotFoundError()

        try:
            for field, value in payload.model_dump(exclude_unset=True).items():
                setattr(subject, field, value)

            await db_session.commit()
            await db_session.refresh(subject)

        except IntegrityError as exc:
            await db_session.rollback()

            handle_subject_code_integrity_error(exc)

            raise

        return subject

    @staticmethod
    async def archive_subject(db_session: AsyncSession, subject_id: int) -> None:
        subject = await SubjectRepository.get_by_id(db_session, subject_id)
        if subject is None:
            raise SubjectNotFoundError()

        if subject.is_archived:
            raise SubjectAlreadyArchivedError()

        subject.is_archived = True
        subject.archived_at = datetime.now(UTC)

        await db_session.commit()

    @staticmethod
    async def restore_subject(db_session: AsyncSession, subject_id: int) -> None:
        subject = await SubjectRepository.get_by_id(db_session, subject_id)
        if subject is None:
            raise SubjectNotFoundError()

        if not subject.is_archived:
            raise SubjectNotArchivedError()

        subject.is_archived = False
        subject.archived_at = None

        await db_session.commit()
