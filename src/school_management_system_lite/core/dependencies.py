from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from school_management_system_lite.auth.repositories.session import (
    UserSessionRepository,
)
from school_management_system_lite.auth.tokens import decode_access_token
from school_management_system_lite.core.exceptions import AppException
from school_management_system_lite.users.models.user import User
from school_management_system_lite.users.repositories.system_admin import (
    UserRepositoryAdmin,
)
from school_management_system_lite.utils.enums import UserRole, UserStatus
from school_management_system_lite.utils.exceptions import (
    AccessDeniedError,
    AccountExpelledError,
    AccountGraduatedError,
    AccountInactiveError,
    AccountNotActivatedError,
    AccountWithdrawnError,
    InvalidAccessTokenError,
    InvalidCredentialsError,
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    session_factory: async_sessionmaker[AsyncSession] = (
        request.app.state.session_factory
    )

    async with session_factory() as db_session:
        yield db_session


db_session_dependency = Annotated[AsyncSession, Depends(get_db_session)]


@dataclass
class CurrentUser:
    user_id: int
    role: UserRole
    session_id: int


async def get_current_user(
    request: Request,
    db_session: db_session_dependency,
    access_token: Annotated[str | None, Depends(oauth2_scheme)],
) -> CurrentUser:
    if access_token is None:
        raise InvalidAccessTokenError()

    try:
        payload = decode_access_token(
            access_token=access_token, settings=request.app.state.settings
        )

        user_id = int(payload["sub"])
        role = UserRole(payload["role"])
        access_token_version = int(payload["atv"])
        session_id = int(payload["session_id"])

    except ValueError, TypeError, KeyError:
        raise InvalidAccessTokenError()

    user_session = await UserSessionRepository.get_by_id(db_session, session_id)
    if user_session is None:
        raise InvalidAccessTokenError(detail="Session not found or has been revoked")

    user = await UserRepositoryAdmin.get_by_id(db_session, user_id)
    if user is None:
        raise InvalidAccessTokenError()

    if user_session.access_token_version != access_token_version:
        raise InvalidAccessTokenError()

    verify_status(user)

    current_user = CurrentUser(
        user_id=user_id,
        role=role,
        session_id=session_id,
    )

    return current_user


current_user_dependency = Annotated[CurrentUser, Depends(get_current_user)]


STATUS_EXCEPTION_MAP: dict[UserStatus, type[AppException]] = {
    UserStatus.PENDING_ACTIVATION: AccountNotActivatedError,
    UserStatus.INACTIVE: AccountInactiveError,
    UserStatus.GRADUATED: AccountGraduatedError,
    UserStatus.EXPELLED: AccountExpelledError,
    UserStatus.WITHDRAWN: AccountWithdrawnError,
}


def verify_status(user: User) -> None:
    if user.status == UserStatus.ACTIVE:
        return

    raise STATUS_EXCEPTION_MAP.get(
        user.status,
        InvalidCredentialsError,
    )()


def require_roles(*roles: UserRole) -> Callable[..., CurrentUser]:
    def guard(current_user: current_user_dependency) -> CurrentUser:
        if current_user.role not in roles:
            raise AccessDeniedError()

        return current_user

    return guard


require_system_admin = Annotated[
    CurrentUser, Depends(require_roles(UserRole.SYSTEM_ADMIN))
]
