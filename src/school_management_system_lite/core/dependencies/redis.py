from typing import Annotated

from fastapi import Depends, Request
from redis.asyncio import Redis


def get_redis(request: Request) -> Redis | None:
    return request.app.state.redis_client


redis_dependency = Annotated[Redis, Depends(get_redis)]
