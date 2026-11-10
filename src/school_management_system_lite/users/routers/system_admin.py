from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Path, status

from school_management_system_lite.core.dependencies import (
    db_session_dependency,
    require_system_admin,
)
from school_management_system_lite.users.schemas.system_admin import (
    CreateUserAdmin,
    UpdateEmailAdmin,
    UpdateIdentityAdmin,
    UserResponseBaseAdmin,
    UserResponseDetailedAdmin,
)
from school_management_system_lite.users.services.system_admin import UserServiceAdmin

router = APIRouter(
    tags=["Users - System Admin"],
)


@router.post(
    "/admin/users",
    response_model=UserResponseDetailedAdmin,
    status_code=status.HTTP_201_CREATED,
)
async def register_user(
    db_session: db_session_dependency,
    current_user: require_system_admin,
    payload: CreateUserAdmin,
):
    return await UserServiceAdmin.register_user(
        db_session, current_user.user_id, payload
    )


@router.patch(
    "/admin/users/{user_id}/identity",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def update_identity(
    db_session: db_session_dependency,
    current_user: require_system_admin,
    user_id: Annotated[int, Path(ge=1)],
    payload: UpdateIdentityAdmin,
):
    return await UserServiceAdmin.update_identity(
        db_session, current_user.user_id, user_id, payload
    )


@router.patch(
    "/admin/users/{user_id}/email",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def update_email(
    db_session: db_session_dependency,
    current_user: require_system_admin,
    user_id: Annotated[int, Path(ge=1)],
    payload: UpdateEmailAdmin,
):
    return await UserServiceAdmin.update_email(
        db_session, current_user.user_id, user_id, payload
    )


@router.patch(
    "/admin/users/{user_id}/deactivation", status_code=status.HTTP_204_NO_CONTENT
)
async def deactivate_user(
    db_session: db_session_dependency,
    user_id: Annotated[int, Path(ge=1)],
):
    await UserServiceAdmin.deactivate_user(db_session, user_id)


@router.patch(
    "/admin/users/{user_id}/activation", status_code=status.HTTP_204_NO_CONTENT
)
async def activate_user(
    db_session: db_session_dependency,
    user_id: Annotated[int, Path(ge=1)],
):
    await UserServiceAdmin.activate_user(db_session, user_id)


@router.get(
    "/admin/users",
    response_model=Sequence[UserResponseBaseAdmin],
    status_code=status.HTTP_200_OK,
)
async def get_users(db_session: db_session_dependency):
    return await UserServiceAdmin.get_users(db_session)


@router.get(
    "/admin/users/{user_id}",
    response_model=UserResponseDetailedAdmin,
    status_code=status.HTTP_200_OK,
)
async def get_user(db_session: db_session_dependency, user_id: int):
    return await UserServiceAdmin.get_user(db_session, user_id)
