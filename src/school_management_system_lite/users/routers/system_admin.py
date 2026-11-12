from typing import Annotated

from fastapi import APIRouter, Depends, Path, status

from school_management_system_lite.core.dependencies.auth import require_system_admin
from school_management_system_lite.core.dependencies.database import (
    db_session_dependency,
)
from school_management_system_lite.core.dependencies.redis import redis_dependency
from school_management_system_lite.core.enums import OrderBy
from school_management_system_lite.core.pagination import (
    PaginatedResponse,
    pagination_dependency,
)
from school_management_system_lite.users.schemas import (
    system_admin as user_schemas_admin,
)
from school_management_system_lite.users.services import (
    system_admin as user_service_admin,
)
from school_management_system_lite.users.utils.enums import UserSortField

router = APIRouter(
    tags=["Users - System Admin"],
)


@router.post(
    "/admin/users",
    response_model=user_schemas_admin.UserResponseDetailedAdmin,
    status_code=status.HTTP_201_CREATED,
)
async def register_user(
    db_session: db_session_dependency,
    authenticated_user: require_system_admin,
    payload: user_schemas_admin.CreateUserAdmin,
):
    return await user_service_admin.register_user(
        db_session, authenticated_user.user_id, payload
    )


@router.patch(
    "/admin/users/{user_id}/identity",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def update_user_identity(
    db_session: db_session_dependency,
    redis: redis_dependency,
    authenticated_user: require_system_admin,
    user_id: Annotated[int, Path(ge=1)],
    payload: user_schemas_admin.UpdateUserIdentityAdmin,
):
    return await user_service_admin.update_user_identity(
        db_session, redis, authenticated_user.user_id, user_id, payload
    )


@router.patch(
    "/admin/users/{user_id}/email",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def update_user_email(
    db_session: db_session_dependency,
    redis: redis_dependency,
    authenticated_user: require_system_admin,
    user_id: Annotated[int, Path(ge=1)],
    payload: user_schemas_admin.UpdateUserEmailAdmin,
):
    return await user_service_admin.update_user_email(
        db_session, redis, authenticated_user.user_id, user_id, payload
    )


@router.patch(
    "/admin/users/{user_id}/deactivation", status_code=status.HTTP_204_NO_CONTENT
)
async def deactivate_user_account(
    db_session: db_session_dependency,
    redis: redis_dependency,
    authenticated_user: require_system_admin,
    user_id: Annotated[int, Path(ge=1)],
):
    await user_service_admin.deactivate_user_account(
        db_session, redis, authenticated_user.user_id, user_id
    )


@router.patch(
    "/admin/users/{user_id}/activation", status_code=status.HTTP_204_NO_CONTENT
)
async def activate_user_account(
    db_session: db_session_dependency,
    redis: redis_dependency,
    authenticated_user: require_system_admin,
    user_id: Annotated[int, Path(ge=1)],
):
    await user_service_admin.activate_user_account(
        db_session, redis, authenticated_user.user_id, user_id
    )


@router.patch(
    "/admin/users/{user_id}/password-reset", status_code=status.HTTP_202_ACCEPTED
)
async def request_password_reset(
    db_session: db_session_dependency,
    authenticated_user: require_system_admin,
    user_id: Annotated[int, Path(ge=1)],
):
    await user_service_admin.request_password_reset(
        db_session, authenticated_user.user_id, user_id
    )


@router.patch(
    "/admin/users/{user_id}/resend-activation", status_code=status.HTTP_202_ACCEPTED
)
async def resend_activation_token(
    db_session: db_session_dependency,
    authenticated_user: require_system_admin,
    user_id: Annotated[int, Path(ge=1)],
):
    await user_service_admin.resend_activation_token(
        db_session, authenticated_user.user_id, user_id
    )


@router.get(
    "/admin/users/staff",
    response_model=PaginatedResponse[user_schemas_admin.UserResponseBaseAdmin],
    status_code=status.HTTP_200_OK,
)
async def get_staff(
    db_session: db_session_dependency,
    _authenticated_user: require_system_admin,
    pagination: pagination_dependency,
    filters: Annotated[user_schemas_admin.UserFiltersAdmin, Depends()],
    sort_by: UserSortField = UserSortField.CREATED_AT,
    order: OrderBy = OrderBy.DESC,
):
    return await user_service_admin.get_staff(
        db_session, pagination.skip, pagination.limit, filters, sort_by, order
    )


@router.get(
    "/admin/users/staff/{user_id}",
    response_model=user_schemas_admin.UserResponseDetailedAdmin,
    status_code=status.HTTP_200_OK,
)
async def get_single_staff(
    db_session: db_session_dependency,
    redis_client: redis_dependency,
    _authenticated_user: require_system_admin,
    user_id: int,
):
    return await user_service_admin.get_single_staff(db_session, redis_client, user_id)
