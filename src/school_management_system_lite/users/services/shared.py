from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.core.redis.cache_keys import UsersCacheKeys
from school_management_system_lite.core.redis.wrappers import get_cache, set_cache
from school_management_system_lite.users.repositories import (
    base as user_base_repository,
)
from school_management_system_lite.users.schemas import shared as user_schemas_shared
from school_management_system_lite.users.utils import exceptions as user_exceptions
from school_management_system_lite.users.utils.constants import STUDENT_ROLE


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
