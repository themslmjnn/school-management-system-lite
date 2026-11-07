from datetime import UTC, datetime, timedelta

import structlog
from fastapi import Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.auth.cookies import set_refresh_token_cookie
from school_management_system_lite.auth.repositories.session import (
    UserSessionRepository,
)
from school_management_system_lite.auth.schemas import LoginResponse
from school_management_system_lite.auth.tokens import (
    create_access_token,
    create_refresh_token,
)
from school_management_system_lite.core.config import Settings
from school_management_system_lite.core.security import verify_password
from school_management_system_lite.users.repositories.base import UserRepositoryBase
from school_management_system_lite.utils.enums import UserStatus
from school_management_system_lite.utils.exceptions import (
    AccountNotActivatedError,
    InvalidCredentialsError,
)

logger = structlog.get_logger(__name__)


class AuthService:
    @staticmethod
    async def login(
        request: Request,
        response: Response,
        db_session: AsyncSession,
        form_data: OAuth2PasswordRequestForm,
        ip_address: str | None,
        user_agent: str | None,
    ) -> LoginResponse:
        settings: Settings = request.app.state.settings

        user = await UserRepositoryBase.get_by_email(
            db_session, email=form_data.username
        )
        if user is None:
            logger.warning(
                "login_failed",
                failure_reason="user_not_found",
                email=form_data.username,
            )

            raise InvalidCredentialsError()

        if not verify_password(form_data.password, user.password_hash):
            logger.warning(
                "login_failed",
                failure_reason="incorrect_password",
                user_id=user.id,
            )

            raise InvalidCredentialsError()

        if user.status == UserStatus.PENDING_ACTIVATION:
            logger.warning(
                "login_failed",
                failure_reason="account_not_activated",
                user_id=user.id,
            )

            raise AccountNotActivatedError()

        if user.status != UserStatus.ACTIVE:
            logger.warning(
                "login_failed",
                failure_reason=f"account_{user.status}",
                user_id=user.id,
            )

            raise InvalidCredentialsError()

        user_session = await UserSessionRepository.get_by_user_id(db_session, user.id)

        raw_refresh_token, refresh_token_hash = create_refresh_token(
            user_id=user.id, session_id=user_session.id, settings=settings
        )

        user_session.refresh_token_hash = refresh_token_hash
        user_session.refresh_token_expires_at = datetime.now(UTC) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRES_DAYS
        )
        user_session.ip_address = ip_address
        user_session.user_agent = user_agent

        access_token = create_access_token(
            user_id=user.id,
            role=user.role,
            access_token_version=user_session.access_token_version,
            session_id=user_session.id,
            settings=settings,
        )

        await db_session.commit()

        logger.info(
            "user_logged_in",
            user_id=user.id,
            role=user.role,
            session_id=user_session.id,
        )

        set_refresh_token_cookie(response, raw_refresh_token, settings)

        return LoginResponse(access_token=access_token, token_type="bearer")
