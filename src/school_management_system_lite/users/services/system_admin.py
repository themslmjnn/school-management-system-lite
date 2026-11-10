from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.auth.models.activation import UserActivation
from school_management_system_lite.auth.models.session import UserSession
from school_management_system_lite.core.config import Settings, get_settings
from school_management_system_lite.core.email.service import send_email_in_background
from school_management_system_lite.core.email.templates.users import (
    build_account_activation_email,
    send_admin_identity_override_email,
)
from school_management_system_lite.core.security import generate_token
from school_management_system_lite.emails.enums import EmailType
from school_management_system_lite.emails.models import Email
from school_management_system_lite.users.models.user import User
from school_management_system_lite.users.repositories.system_admin import (
    UserRepositoryAdmin,
)
from school_management_system_lite.users.schemas.system_admin import (
    CreateUserAdmin,
    UpdateIdentityAdmin,
)
from school_management_system_lite.users.utils.exceptions import (
    UserAlreadyActive,
    UserAlreadyInactive,
    UserNotFoundError,
    handle_email_integrity_error,
    handle_phone_number_integrity_error,
)
from school_management_system_lite.utils.enums import UserStatus

logger = structlog.get_logger(__name__)


class UserServiceAdmin:
    @staticmethod
    async def register_user(
        db_session: AsyncSession,
        actor_id: int,
        payload: CreateUserAdmin,
    ) -> User:
        settings: Settings = get_settings()

        try:
            user = User(
                first_name=payload.first_name,
                last_name=payload.last_name,
                middle_name=payload.middle_name,
                date_of_birth=payload.date_of_birth,
                address=payload.address,
                phone_number=payload.phone_number,
                email=payload.email,
                role=payload.role,
                status=UserStatus.PENDING_ACTIVATION,
                created_by=actor_id,
            )

            db_session.add(user)
            await db_session.flush()

            raw_activation_token, activation_token_hash = generate_token()
            activation_token_expires_at = datetime.now(UTC) + timedelta(
                hours=settings.ACTIVATION_TOKEN_EXPIRES_HOURS
            )

            db_session.add(UserSession(user_id=user.id))
            db_session.add(
                UserActivation(
                    user_id=user.id,
                    activation_token_hash=activation_token_hash,
                    activation_token_expires_at=activation_token_expires_at,
                )
            )

            subject, html_body = build_account_activation_email(
                user.email, raw_activation_token
            )

            db_session.add(
                Email(
                    recipient_email=user.email,
                    subject=subject,
                    html_body=html_body,
                    email_type=EmailType.ACCOUNT_ACTIVATION,
                    triggered_by=actor_id,
                )
            )

            await db_session.commit()
            await db_session.refresh(user)

        except IntegrityError as exc:
            await db_session.rollback()

            logger.warning(
                "user_registration_failed",
                failure_reason="integrity_error",
                error=str(exc.orig),
                requested_by=actor_id,
            )

            handle_phone_number_integrity_error(exc)
            handle_email_integrity_error(exc)

            raise

        logger.info(
            "user_registered",
            user_id=user.id,
            email=user.email,
            role=user.role,
            created_by=actor_id,
        )

        return user

    @staticmethod
    async def update_identity(
        db_session: AsyncSession,
        actor_id: int,
        user_id: int,
        payload: UpdateIdentityAdmin,
    ) -> None:
        user = await UserRepositoryAdmin.get_by_id(db_session, user_id)
        if user is None:
            raise UserNotFoundError()

        try:
            for field, value in payload.model_dump(exclude_unset=True).items():
                setattr(user, field, value)

            await db_session.commit()

        except IntegrityError as exc:
            await db_session.rollback()

            logger.warning(
                "updating_identity_failed",
                failure_reason="integrity_error",
                error=str(exc.orig),
                user_id=user.id,
                requested_by=actor_id,
            )

            handle_phone_number_integrity_error(exc)

            raise

        send_email_in_background(
            send_admin_identity_override_email(user.email),
            email_type=EmailType.ADMIN_IDENTITY_OVERRIDE,
        )

        logger.info(
            "identity_updated",
            user_id=user.id,
            actor_id=actor_id,
            method="admin_update",
        )

    @staticmethod
    async def deactivate_user(db_session: AsyncSession, user_id: int) -> None:
        user = await UserRepositoryAdmin.get_by_id(db_session, user_id)
        if user is None:
            raise UserNotFoundError()

        if user.status == UserStatus.INACTIVE:
            raise UserAlreadyInactive()

        user.status = UserStatus.INACTIVE

        await db_session.commit()

    @staticmethod
    async def activate_user(db_session: AsyncSession, user_id: int) -> None:
        user = await UserRepositoryAdmin.get_by_id(db_session, user_id)
        if user is None:
            raise UserNotFoundError()

        if user.status == UserStatus.ACTIVE:
            raise UserAlreadyActive()

        user.status = UserStatus.ACTIVE

        await db_session.commit()

    @staticmethod
    async def get_users(db_session: AsyncSession) -> Sequence[User]:
        return await UserRepositoryAdmin.get_users(db_session)

    @staticmethod
    async def get_user(db_session: AsyncSession, user_id: int) -> User:
        user = await UserRepositoryAdmin.get_by_id(db_session, user_id)
        if user is None:
            raise UserNotFoundError()

        return user
