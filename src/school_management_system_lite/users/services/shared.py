from datetime import UTC, datetime, timedelta

import structlog
from httpx import AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.auth.repositories import (
    session as auth_session_repository,
)
from school_management_system_lite.core.config import get_settings
from school_management_system_lite.core.email.service import send_email_in_background
from school_management_system_lite.core.email.templates.email_change_request import (
    build_email_change_email,
)
from school_management_system_lite.core.email.templates.password_changed_notification import (
    send_password_changed_notification,
)
from school_management_system_lite.core.redis.cache_keys import UsersCacheKeys
from school_management_system_lite.core.redis.wrappers import (
    get_cache,
    set_cache,
)
from school_management_system_lite.core.security import (
    generate_token,
    hash_password,
    verify_password,
)
from school_management_system_lite.emails.enums import EmailType
from school_management_system_lite.emails.models import Email
from school_management_system_lite.users.models.email_changes import UserEmailChange
from school_management_system_lite.users.repositories import (
    base as user_base_repository,
)
from school_management_system_lite.users.repositories import (
    email_change as email_change_repository,
)
from school_management_system_lite.users.schemas import shared as user_schemas_shared
from school_management_system_lite.users.utils import exceptions as user_exceptions
from school_management_system_lite.users.utils.constants import STUDENT_ROLE

logger = structlog.get_logger(__name__)


async def get_my_profile(
    db_session: AsyncSession,
    redis_client: Redis | None,
    user_id: int,
) -> user_schemas_shared.UserSelfResponseDetailed:
    cache_key = UsersCacheKeys.detailed_response_key_self(user_id)

    cached_value = await get_cache(redis_client, cache_key)
    if cached_value is not None:
        return user_schemas_shared.UserSelfResponseDetailed.model_validate(cached_value)

    user = await user_base_repository.get_by_id(
        db_session, user_id, excluded_roles=STUDENT_ROLE
    )
    if user is None:
        raise user_exceptions.UserNotFoundError()

    response = user_schemas_shared.UserSelfResponseDetailed.model_validate(user)

    await set_cache(redis_client, cache_key, response.model_dump(mode="json"), 900)

    return response


async def request_email_change(
    db_session: AsyncSession,
    user_id: int,
    payload: user_schemas_shared.UpdateEmailMe,
) -> None:
    user = await user_base_repository.get_by_id(db_session, user_id)
    if user is None:
        raise user_exceptions.UserNotFoundError()

    if user.email == payload.new_email or payload.new_email is None:
        return

    if (
        await user_base_repository.get_by_email(db_session, payload.new_email)
        is not None
    ):
        logger.warning(
            "email_change_request_denied",
            denial_reason="email_is_already_taken",
            user_id=user_id,
        )

        raise user_exceptions.EmailAlreadyTakenError()

    raw_email_change_token, email_change_token_hash = generate_token()
    email_change_token_expires_at = datetime.now(UTC) + timedelta(
        minutes=get_settings().EMAIL_CHANGE_TOKEN_EXPIRES_MINUTES
    )

    email_change = await email_change_repository.get_by_user_id(db_session, user_id)
    if email_change is None:
        db_session.add(
            UserEmailChange(
                user_id=user.id,
                new_email=payload.new_email,
                email_change_token_hash=email_change_token_hash,
                email_change_token_expires_at=email_change_token_expires_at,
            )
        )
    else:
        email_change.new_email = payload.new_email
        email_change.email_change_token_hash = email_change_token_hash
        email_change.email_change_token_expires_at = email_change_token_expires_at

    subject, html_body = build_email_change_email(
        payload.new_email, raw_email_change_token
    )

    db_session.add(
        Email(
            recipient_email=payload.new_email,
            subject=subject,
            html_body=html_body,
            email_type=EmailType.EMAIL_CHANGE_REQUEST,
        )
    )

    await db_session.commit()

    logger.info("email_change_requested_successfully", user_id=user_id)


async def update_my_password(
    db_session: AsyncSession,
    resend_client: AsyncClient | None,
    user_id: int,
    payload: user_schemas_shared.UpdateMyPassword,
) -> None:
    user = await user_base_repository.get_by_id(db_session, user_id)
    if user is None:
        raise user_exceptions.UserNotFoundError()

    if user.password_hash is None:
        raise user_exceptions.InvalidPasswordError()

    is_current_password_valid = await verify_password(
        payload.current_password, user.password_hash
    )

    if not is_current_password_valid:
        logger.warning(
            "password_change_denied",
            denial_reason="incorrect_current_password",
            user_id=user_id,
            method="self_service",
        )

        raise user_exceptions.IncorrectCurrentPasswordError()

    if payload.current_password == payload.new_password:
        raise user_exceptions.SamePasswordError()

    new_password_hash = await hash_password(payload.new_password)

    user.password_hash = new_password_hash

    user_session = await auth_session_repository.get_by_user_id(db_session, user_id)

    user_session.access_token_version += 1
    user_session.refresh_token_hash = None
    user_session.refresh_token_expires_at = None

    user_email = user.email

    await db_session.commit()

    send_email_in_background(
        send_password_changed_notification(resend_client, user_email),
        email_type=EmailType.PASSWORD_CHANGED_NOTIFICATION,
    )

    logger.info(
        "password_changed",
        user_id=user_id,
        method="self_service",
    )
