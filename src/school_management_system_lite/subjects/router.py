from typing import Annotated

from fastapi import APIRouter, Path, status

from school_management_system_lite.core.dependencies import db_session_dependency
from school_management_system_lite.subjects.schemas import (
    CreateSubject,
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
