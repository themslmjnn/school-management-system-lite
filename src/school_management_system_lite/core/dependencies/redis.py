from typing import Annotated

from fastapi import Depends, Request
from redis.asyncio import Redis


def get_redis_client(request: Request) -> Redis | None:
    return request.app.state.redis_client


redis_client_dep = Annotated[Redis | None, Depends(get_redis_client)]
