from datetime import UTC, datetime, timedelta

import structlog
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.core.config import get_settings
from school_management_system_lite.core.email.templates.email_change_request import (
    build_email_change_email,
)
from school_management_system_lite.core.redis.cache_keys import UsersCacheKeys
from school_management_system_lite.core.redis.wrappers import get_cache, set_cache
from school_management_system_lite.core.security import generate_token
from school_management_system_lite.emails.enums import EmailType
from school_management_system_lite.emails.models import Email
from school_management_system_lite.users.models.email_changes import UserEmailChange
from school_management_system_lite.users.repositories import (
    base as user_base_repository,
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

    db_session.add(
        UserEmailChange(
            user_id=user.id,
            new_email=payload.new_email,
            email_change_token_hash=email_change_token_hash,
            email_change_token_expires_at=email_change_token_expires_at,
        )
    )

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
