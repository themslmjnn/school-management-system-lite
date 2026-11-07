from fastapi import APIRouter, status

from school_management_system_lite.core.dependencies import db_session_dependency
from school_management_system_lite.groups.schemas import (
    CreateGroup,
    GroupResponseDetailed,
)
from school_management_system_lite.groups.service import GroupService

router = APIRouter(
    prefix="/groups",
    tags=["Groups"],
)


@router.post(
    "", response_model=GroupResponseDetailed, status_code=status.HTTP_201_CREATED
)
async def create_group(db_session: db_session_dependency, payload: CreateGroup):
    return await GroupService.create_group(db_session, payload)
