from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer

from school_management_system_lite.auth.repositories import (
    session as auth_session_repository,
)
from school_management_system_lite.auth.utils import exceptions as auth_exceptions
from school_management_system_lite.auth.utils import tokens as auth_tokens
from school_management_system_lite.core.dependencies.database import (
    db_session_dependency,
)
from school_management_system_lite.core.exceptions.exceptions import AccessDeniedError
from school_management_system_lite.users.repositories import (
    system_admin as user_repository_admin,
)
from school_management_system_lite.users.utils.enums import UserRole, UserStatus

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


@dataclass
class CurrentUser:
    user_id: int
    role: UserRole
    session_id: int


async def authenticate_user(
    request: Request,
    db_session: db_session_dependency,
    access_token: Annotated[str | None, Depends(oauth2_scheme)],
) -> CurrentUser:
    if access_token is None:
        raise auth_exceptions.InvalidAccessTokenError()

    try:
        payload = auth_tokens.decode_access_token(
            access_token=access_token, settings=request.app.state.settings
        )

        user_id = int(payload["sub"])
        role = UserRole(payload["role"])
        session_id = int(payload["session_id"])
        access_token_version = int(payload["atv"])

    except ValueError, TypeError, KeyError:
        raise auth_exceptions.InvalidAccessTokenError()

    user_session = await auth_session_repository.get_by_id(db_session, session_id)
    if user_session is None:
        raise auth_exceptions.InvalidAccessTokenError(
            detail="Session not found or has been revoked"
        )

    user = await user_repository_admin.get_by_id(db_session, user_id)
    if user is None:
        raise auth_exceptions.InvalidAccessTokenError()

    if user_session.access_token_version != access_token_version:
        raise auth_exceptions.InvalidAccessTokenError()

    if user.status == UserStatus.INACTIVE:
        raise auth_exceptions.UserInactiveError()

    current_user = CurrentUser(
        user_id=user_id,
        role=role,
        session_id=session_id,
    )

    return current_user


authenticated_user = Annotated[CurrentUser, Depends(authenticate_user)]


def require_roles(*roles: UserRole) -> Callable[..., CurrentUser]:
    def guard(current_user: authenticated_user) -> CurrentUser:
        if current_user.role not in roles:
            raise AccessDeniedError()

        return current_user

    return guard


require_system_admin = Annotated[
    CurrentUser, Depends(require_roles(UserRole.SYSTEM_ADMIN))
]
