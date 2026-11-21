from fastapi import APIRouter, status

from school_management_system_lite.core.dependencies.auth import (
    authenticated_user,
    require_system_admin_and_staff,
)
from school_management_system_lite.core.dependencies.database import db_session_dep
from school_management_system_lite.core.dependencies.redis import redis_client_dep
from school_management_system_lite.users.schemas import shared as user_schemas_shared
from school_management_system_lite.users.services import shared as user_service_shared

router = APIRouter(tags=["Users Module - Shared"])


@router.get(
    "/users/me",
    response_model=user_schemas_shared.UserSelfResponseDetailed,
    status_code=status.HTTP_200_OK,
)
async def get_my_profile(
    db_session: db_session_dep,
    redis_client: redis_client_dep,
    authenticated_user: require_system_admin_and_staff,
):
    return await user_service_shared.get_my_profile(
        db_session, redis_client, authenticated_user.user_id
    )


@router.post("/users/me/email", status_code=status.HTTP_202_ACCEPTED)
async def request_email_change(
    db_session: db_session_dep,
    authenticated_user: authenticated_user,
    payload: user_schemas_shared.UpdateEmailMe,
):
    await user_service_shared.request_email_change(
        db_session, authenticated_user.user_id, payload
    )
