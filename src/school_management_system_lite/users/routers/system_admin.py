from typing import Annotated

from fastapi import APIRouter, Path, status

from school_management_system_lite.core.dependencies import db_session_dependency
from school_management_system_lite.users.schemas.system_admin import (
    CreateUserAdmin,
    UpdateUserAdmin,
    UserResponseDetailedAdmin,
)
from school_management_system_lite.users.services.system_admin import UserServiceAdmin

router = APIRouter(
    prefix="/admin/users",
    tags=["Users - System Admin"],
)


@router.post(
    "", response_model=UserResponseDetailedAdmin, status_code=status.HTTP_201_CREATED
)
async def register_user(
    db_session: db_session_dependency,
    payload: CreateUserAdmin,
):
    return await UserServiceAdmin.register_user(db_session, payload)


@router.patch(
    "/{user_id}",
    response_model=UserResponseDetailedAdmin,
    status_code=status.HTTP_200_OK,
)
async def update_user(
    db_session: db_session_dependency,
    user_id: Annotated[int, Path(ge=1)],
    payload: UpdateUserAdmin,
):
    return await UserServiceAdmin.update_user(db_session, user_id, payload)


@router.patch("/{user_id}/deactivation", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_user(
    db_session: db_session_dependency,
    user_id: Annotated[int, Path(ge=1)],
):
    await UserServiceAdmin.deactivate_user(db_session, user_id)


@router.patch("/{user_id}/activation", status_code=status.HTTP_204_NO_CONTENT)
async def activate_user(
    db_session: db_session_dependency,
    user_id: Annotated[int, Path(ge=1)],
):
    await UserServiceAdmin.activate_user(db_session, user_id)
