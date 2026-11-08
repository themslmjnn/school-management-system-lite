from redis.asyncio import Redis

from school_management_system_lite.core.config import Settings

SOCKET_CONNECT_TIMEOUT_SECONDS = 2
SOCKET_TIMEOUT_SECONDS = 2


def build_redis(settings: Settings) -> Redis:
    return Redis.from_url(
        url=settings.REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=SOCKET_CONNECT_TIMEOUT_SECONDS,
        socket_timeout=SOCKET_TIMEOUT_SECONDS,
    )
