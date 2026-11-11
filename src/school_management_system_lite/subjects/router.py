from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Path, status

from school_management_system_lite.core.dependencies.auth import db_session_dependency
from school_management_system_lite.subjects.schemas import (
    CreateSubject,
    SubjectResponseBase,
    SubjectResponseDetailed,
    UpdateSubject,
)
from school_management_system_lite.subjects.service import SubjectService

router = APIRouter(
    prefix="/subjects",
    tags=["Subjects"],
)


@router.post(
    "", response_model=SubjectResponseDetailed, status_code=status.HTTP_201_CREATED
)
async def create_subject(
    db_session: db_session_dependency,
    payload: CreateSubject,
):
    return await SubjectService.create_subject(db_session, payload)


@router.patch(
    "/{subject_id}",
    response_model=SubjectResponseDetailed,
    status_code=status.HTTP_200_OK,
)
async def update_subject(
    db_session: db_session_dependency,
    subject_id: Annotated[int, Path(ge=1)],
    payload: UpdateSubject,
):
    return await SubjectService.update_subject(db_session, subject_id, payload)


@router.patch("/{subject_id}/archive", status_code=status.HTTP_204_NO_CONTENT)
async def archive_subject(
    db_session: db_session_dependency,
    subject_id: Annotated[int, Path(ge=1)],
):
    await SubjectService.archive_subject(db_session, subject_id)


@router.patch("/{subject_id}/restore", status_code=status.HTTP_204_NO_CONTENT)
async def restore_subject(
    db_session: db_session_dependency,
    subject_id: Annotated[int, Path(ge=1)],
):
    await SubjectService.restore_subject(db_session, subject_id)


@router.get(
    "", response_model=Sequence[SubjectResponseBase], status_code=status.HTTP_200_OK
)
async def get_subjects(db_session: db_session_dependency):
    return await SubjectService.get_subjects(db_session)


@router.get(
    "/{subject_id}",
    response_model=SubjectResponseDetailed,
    status_code=status.HTTP_200_OK,
)
async def get_subject(
    db_session: db_session_dependency, subject_id: Annotated[int, Path(ge=1)]
):
    return await SubjectService.get_subject(db_session, subject_id)
