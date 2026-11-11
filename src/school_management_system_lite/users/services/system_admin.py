from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

import structlog
from redis.asyncio import Redis
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.auth.models.activation import UserActivation
from school_management_system_lite.auth.models.session import UserSession
from school_management_system_lite.auth.repositories.session import (
    UserSessionRepository,
)
from school_management_system_lite.core.config import Settings, get_settings
from school_management_system_lite.core.email.service import send_email_in_background
from school_management_system_lite.core.email.templates.users import (
    build_account_activation_email,
    build_admin_account_deactivation_email,
    build_admin_email_override_email,
    send_admin_identity_override_email,
)
from school_management_system_lite.core.redis.cache_keys import UsersCacheKeys
from school_management_system_lite.core.redis.wrappers import delete_cache
from school_management_system_lite.core.security import generate_token
from school_management_system_lite.emails.enums import EmailType
from school_management_system_lite.emails.models import Email
from school_management_system_lite.users.models.user import User
from school_management_system_lite.users.repositories.system_admin import (
    UserRepositoryAdmin,
)
from school_management_system_lite.users.schemas.system_admin import (
    CreateUserAdmin,
    UpdateUserEmailAdmin,
    UpdateUserIdentityAdmin,
)
from school_management_system_lite.users.utils.constants import SYSTEM_ADMIN_ROLE
from school_management_system_lite.users.utils.exceptions import (
    UserAlreadyInactiveError,
    UserNotFoundError,
    UserStatusPendingActivationError,
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
    async def update_user_identity(
        db_session: AsyncSession,
        redis: Redis,
        actor_id: int,
        user_id: int,
        payload: UpdateUserIdentityAdmin,
    ) -> None:
        user = await UserRepositoryAdmin.get_by_id(
            db_session, user_id, excluded_roles=SYSTEM_ADMIN_ROLE
        )
        if user is None:
            raise UserNotFoundError()

        payload = payload.model_dump(exclude_unset=True, exclude_none=True)
        if payload is None:
            return

        try:
            is_new_value = False

            for field, value in payload.items():
                if getattr(user, field) != value:
                    setattr(user, field, value)

                    is_new_value = True

            if not is_new_value:
                return

            await db_session.commit()
            await db_session.refresh(user)

        except IntegrityError as exc:
            await db_session.rollback()

            logger.warning(
                "updating_user_identity_failed",
                failure_reason="integrity_error",
                error=str(exc.orig),
                user_id=user_id,
                requested_by=actor_id,
            )

            handle_phone_number_integrity_error(exc)

            raise

        await delete_cache(
            redis,
            UsersCacheKeys.detailed_response_key_admin(user_id),
            UsersCacheKeys.detailed_response_key_staff(user_id),
            UsersCacheKeys.detailed_response_key_self(user_id),
        )

        send_email_in_background(
            send_admin_identity_override_email(user.email),
            email_type=EmailType.ADMIN_USER_IDENTITY_OVERRIDE,
        )

        logger.info(
            "user_identity_updated",
            user_id=user_id,
            actor_id=actor_id,
            method="admin_update",
        )

    @staticmethod
    async def update_user_email(
        db_session: AsyncSession,
        redis: Redis,
        actor_id: int,
        user_id: int,
        payload: UpdateUserEmailAdmin,
    ) -> None:
        user = await UserRepositoryAdmin.get_by_id(
            db_session, user_id, excluded_roles=SYSTEM_ADMIN_ROLE
        )
        if user is None:
            raise UserNotFoundError()

        try:
            if user.email == payload.email or payload.email is None:
                return

            user.email = payload.email

            user_session = await UserSessionRepository.get_by_user_id(
                db_session, user_id
            )

            user_session.access_token_version += 1
            user_session.refresh_token_hash = None
            user_session.refresh_token_expires_at = None

            subject, html_body = build_admin_email_override_email(
                user.email,
            )

            db_session.add(
                Email(
                    recipient_email=user.email,
                    subject=subject,
                    html_body=html_body,
                    email_type=EmailType.ADMIN_USER_EMAIL_OVERRIDE,
                    triggered_by=actor_id,
                )
            )

            await db_session.commit()

        except IntegrityError as exc:
            await db_session.rollback()

            logger.warning(
                "updating_user_email_failed",
                failure_reason="integrity_error",
                error=str(exc.orig),
                user_id=user_id,
                requested_by=actor_id,
            )

            handle_email_integrity_error(exc)

            raise

        await delete_cache(
            redis,
            UsersCacheKeys.detailed_response_key_admin(user_id),
            UsersCacheKeys.detailed_response_key_staff(user_id),
            UsersCacheKeys.detailed_response_key_self(user_id),
        )

        logger.info(
            "user_email_updated",
            user_id=user_id,
            actor_id=actor_id,
            method="admin_update",
        )

    @staticmethod
    async def deactivate_user_account(
        db_session: AsyncSession, redis: Redis, actor_id: int, user_id: int
    ) -> None:
        user = await UserRepositoryAdmin.get_by_id(
            db_session, user_id, excluded_roles=SYSTEM_ADMIN_ROLE
        )
        if user is None:
            raise UserNotFoundError()

        if user.status == UserStatus.PENDING_ACTIVATION:
            logger.warning(
                "user_account_deactivation_failed",
                failure_reason="account_status_is_pending_activation",
                user_id=user_id,
                requested_by=actor_id,
            )

            raise UserStatusPendingActivationError()

        if user.status == UserStatus.INACTIVE:
            logger.warning(
                "user_account_deactivation_failed",
                failure_reason="user_account_is_already_inactive",
                user_id=user_id,
                requested_by=actor_id,
            )

            raise UserAlreadyInactiveError()

        user.status = UserStatus.INACTIVE

        user_session = await UserSessionRepository.get_by_user_id(db_session, user.id)

        user_session.access_token_version += 1
        user_session.refresh_token_hash = None
        user_session.refresh_token_expires_at = None

        subject, html_body = build_admin_account_deactivation_email()

        db_session.add(
            Email(
                recipient_email=user.email,
                subject=subject,
                html_body=html_body,
                email_type=EmailType.ADMIN_ACCOUNT_DEACTIVATION,
                triggered_by=actor_id,
            )
        )

        await db_session.commit()

        await delete_cache(
            redis,
            UsersCacheKeys.detailed_response_key_admin(user_id),
            UsersCacheKeys.detailed_response_key_staff(user_id),
            UsersCacheKeys.detailed_response_key_self(user_id),
        )

        logger.info(
            "user_account_deactivated",
            user_id=user_id,
            actor_id=actor_id,
        )

    @staticmethod
    async def activate_user(db_session: AsyncSession, user_id: int) -> None:
        user = await UserRepositoryAdmin.get_by_id(db_session, user_id)
        if user is None:
            raise UserNotFoundError()

        if user.status == UserStatus.ACTIVE:
            raise UserAlreadyInactiveError()

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
