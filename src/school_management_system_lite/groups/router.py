from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Path, status

from school_management_system_lite.core.dependencies import db_session_dependency
from school_management_system_lite.groups.schemas import (
    CreateGroup,
    GroupResponseBase,
    GroupResponseDetailed,
    UpdateGroup,
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


@router.patch(
    "/{group_id}", response_model=GroupResponseDetailed, status_code=status.HTTP_200_OK
)
async def update_group(
    db_session: db_session_dependency,
    group_id: Annotated[int, Path(ge=1)],
    payload: UpdateGroup,
):
    return await GroupService.update_group(db_session, group_id, payload)


@router.get(
    "", response_model=Sequence[GroupResponseBase], status_code=status.HTTP_200_OK
)
async def get_groups(db_session: db_session_dependency):
    return await GroupService.get_groups(db_session)


@router.get(
    "/{group_id}",
    response_model=GroupResponseDetailed,
    status_code=status.HTTP_200_OK,
)
async def get_group(
    db_session: db_session_dependency, group_id: Annotated[int, Path(ge=1)]
):
    return await GroupService.get_group(db_session, group_id)
