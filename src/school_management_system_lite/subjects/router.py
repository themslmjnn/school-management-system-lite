from fastapi import APIRouter, status

from school_management_system_lite.core.dependencies import db_session_dependency
from school_management_system_lite.subjects.schemas import (
    CreateSubject,
    SubjectResponseDetailed,
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
