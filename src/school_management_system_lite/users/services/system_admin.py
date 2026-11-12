from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

import structlog
from redis.asyncio import Redis
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

import school_management_system_lite.emails.repository as email_repository
from school_management_system_lite.auth.models.activation import UserActivation
from school_management_system_lite.auth.models.password_reset import UserPasswordReset
from school_management_system_lite.auth.models.session import UserSession
from school_management_system_lite.auth.repositories import (
    password_reset as auth_password_reset_repository,
)
from school_management_system_lite.auth.repositories import (
    session as auth_session_repository,
)
from school_management_system_lite.core.config import Settings, get_settings
from school_management_system_lite.core.email.service import send_email_in_background
from school_management_system_lite.core.email.templates.account_activation import (
    build_account_activation_email,
)
from school_management_system_lite.core.email.templates.admin_account_activation import (
    send_admin_account_activation_email,
)
from school_management_system_lite.core.email.templates.admin_account_deactivation import (
    build_admin_account_deactivation_email,
)
from school_management_system_lite.core.email.templates.admin_password_reset import (
    build_admin_password_reset_email,
)
from school_management_system_lite.core.email.templates.admin_user_email_override import (
    build_admin_email_override_email,
)
from school_management_system_lite.core.email.templates.admin_user_identity_override import (
    send_admin_identity_override_email,
)
from school_management_system_lite.core.enums import OrderBy
from school_management_system_lite.core.redis.cache_keys import UsersCacheKeys
from school_management_system_lite.core.redis.wrappers import delete_cache
from school_management_system_lite.core.security import generate_token
from school_management_system_lite.emails.enums import EmailStatus, EmailType
from school_management_system_lite.emails.models import Email
from school_management_system_lite.users.models import User
from school_management_system_lite.users.repositories import (
    base as user_base_repository,
)
from school_management_system_lite.users.repositories import (
    system_admin as user_repository_admin,
)
from school_management_system_lite.users.schemas import (
    system_admin as user_schemas_admin,
)
from school_management_system_lite.users.utils import exceptions as user_exceptions
from school_management_system_lite.users.utils.constants import SYSTEM_ADMIN_ROLE
from school_management_system_lite.users.utils.enums import UserStatus
from school_management_system_lite.users.utils.helpers import ensure_utc

logger = structlog.get_logger(__name__)


async def register_user(
    db_session: AsyncSession,
    actor_id: int,
    payload: user_schemas_admin.CreateUserAdmin,
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

        user_exceptions.handle_phone_number_integrity_error(exc)
        user_exceptions.handle_email_integrity_error(exc)

        raise

    logger.info(
        "user_registered",
        user_id=user.id,
        email=user.email,
        role=user.role,
        created_by=actor_id,
    )

    return user


async def update_user_identity(
    db_session: AsyncSession,
    redis: Redis,
    actor_id: int,
    user_id: int,
    payload: user_schemas_admin.UpdateUserIdentityAdmin,
) -> None:
    user = await user_base_repository.get_by_id(
        db_session, user_id, excluded_roles=SYSTEM_ADMIN_ROLE
    )
    if user is None:
        raise user_exceptions.UserNotFoundError()

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

        user_exceptions.handle_phone_number_integrity_error(exc)

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


async def update_user_email(
    db_session: AsyncSession,
    redis: Redis,
    actor_id: int,
    user_id: int,
    payload: user_schemas_admin.UpdateUserEmailAdmin,
) -> None:
    user = await user_base_repository.get_by_id(
        db_session, user_id, excluded_roles=SYSTEM_ADMIN_ROLE
    )
    if user is None:
        raise user_exceptions.UserNotFoundError()

    try:
        if user.email == payload.email or payload.email is None:
            return

        user.email = payload.email

        user_session = await auth_session_repository.get_by_user_id(db_session, user_id)

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

        user_exceptions.handle_email_integrity_error(exc)

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


async def deactivate_user_account(
    db_session: AsyncSession, redis: Redis, actor_id: int, user_id: int
) -> None:
    user = await user_base_repository.get_by_id(
        db_session, user_id, excluded_roles=SYSTEM_ADMIN_ROLE
    )
    if user is None:
        raise user_exceptions.UserNotFoundError()

    if user.status == UserStatus.PENDING_ACTIVATION:
        logger.warning(
            "user_account_deactivation_failed",
            failure_reason="account_status_is_pending_activation",
            user_id=user_id,
            requested_by=actor_id,
        )

        raise user_exceptions.UserPendingActivationError()

    if user.status == UserStatus.INACTIVE:
        logger.warning(
            "user_account_deactivation_failed",
            failure_reason="user_account_is_already_inactive",
            user_id=user_id,
            requested_by=actor_id,
        )

        raise user_exceptions.UserAlreadyInactiveError()

    user.status = UserStatus.INACTIVE

    user_session = await auth_session_repository.get_by_user_id(db_session, user.id)

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
    )

    logger.info(
        "user_account_deactivated",
        user_id=user_id,
        actor_id=actor_id,
    )


async def activate_user_account(
    db_session: AsyncSession, redis: Redis, actor_id: int, user_id: int
) -> None:
    user = await user_base_repository.get_by_id(
        db_session, user_id, excluded_roles=SYSTEM_ADMIN_ROLE
    )
    if user is None:
        raise user_exceptions.UserNotFoundError()

    if user.status == UserStatus.ACTIVE:
        logger.warning(
            "user_account_activation_failed",
            failure_reason="user_is_already_active",
            user_id=user_id,
            requested_by=actor_id,
        )

        raise user_exceptions.UserAlreadyActiveError()

    if user.status == UserStatus.PENDING_ACTIVATION:
        logger.warning(
            "user_account_activation_failed",
            failure_reason="user_status_is_pending_activation",
            user_id=user_id,
            requested_by=actor_id,
        )

        raise user_exceptions.UserPendingActivationError()

    user.status = UserStatus.ACTIVE

    await db_session.commit()

    await delete_cache(
        redis,
        UsersCacheKeys.detailed_response_key_admin(user_id),
        UsersCacheKeys.detailed_response_key_staff(user_id),
    )

    send_email_in_background(
        send_admin_account_activation_email(to_email=user.email),
        email_type=EmailType.ADMIN_ACCOUNT_ACTIVATION,
    )

    logger.info(
        "user_account_activated",
        user_id=user_id,
        actor_id=actor_id,
    )


async def request_password_reset(
    db_session: AsyncSession,
    actor_id: int,
    user_id: int,
) -> None:
    settings = get_settings()

    user = await user_base_repository.get_by_id(
        db_session, user_id, excluded_roles=SYSTEM_ADMIN_ROLE
    )
    if user is None:
        raise user_exceptions.UserNotFoundError()

    if user.status == UserStatus.PENDING_ACTIVATION:
        logger.warning(
            "password_reset_request_denied",
            denial_reason="cannot_create_request_for_pending_activation_users",
            user_id=user_id,
            requested_by=actor_id,
        )

        raise user_exceptions.UserPendingActivationError(
            detail="Can not create password reset request for pending activation users"
        )

    password_reset = await auth_password_reset_repository.get_by_user_id(
        db_session,
        user_id,
    )

    email = await email_repository.get_by_recipient_email(
        db_session,
        user.email,
        email_type=frozenset(
            {
                EmailType.ADMIN_PASSWORD_RESET,
                EmailType.FORGOT_PASSWORD_REQUEST,
            }
        ),
        status=EmailStatus.PENDING,
        order_by=OrderBy.DESC,
    )

    has_pending_password_reset_token = (
        password_reset is not None
        and password_reset.password_reset_token_hash is not None
        and password_reset.password_reset_token_expires_at is not None
        and ensure_utc(password_reset.password_reset_token_expires_at)
        > datetime.now(UTC)
    )

    has_pending_password_reset_email = len(email) != 0

    if has_pending_password_reset_token or has_pending_password_reset_email:
        logger.warning(
            "password_reset_request_denied",
            denial_reason="user_already_has_pending_requests",
            user_id=user_id,
            requested_by=actor_id,
        )

        raise user_exceptions.PasswordResetAlreadyRequestedError()

    if password_reset is not None:
        await db_session.delete(password_reset)
        await db_session.flush()

    raw_password_reset_token, password_reset_token_hash = generate_token()

    password_reset_token_expires_at = datetime.now(UTC) + timedelta(
        minutes=settings.PASSWORD_RESET_TOKEN_EXPIRES_MINUTES
    )

    subject, html_body = build_admin_password_reset_email(raw_password_reset_token)

    db_session.add(
        UserPasswordReset(
            user_id=user.id,
            password_reset_token_hash=password_reset_token_hash,
            password_reset_token_expires_at=password_reset_token_expires_at,
        )
    )

    db_session.add(
        Email(
            recipient_email=user.email,
            subject=subject,
            html_body=html_body,
            email_type=EmailType.ADMIN_PASSWORD_RESET,
            triggered_by=actor_id,
        )
    )

    await db_session.commit()

    logger.info(
        "password_reset_requested",
        user_id=user_id,
        actor_id=actor_id,
    )


async def get_users(db_session: AsyncSession) -> Sequence[User]:
    return await user_repository_admin.get_users(db_session)


async def get_user(db_session: AsyncSession, user_id: int) -> User:
    user = await user_base_repository.get_by_id(db_session, user_id)
    if user is None:
        raise user_exceptions.UserNotFoundError()

    return user
