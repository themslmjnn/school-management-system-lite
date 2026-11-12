from typing import Annotated

from fastapi import Depends, Query
from pydantic import BaseModel


class PaginatedResponse[T](BaseModel):
    items: list[T]
    total: int
    skip: int
    limit: int
    has_more: bool


class PaginationParams(BaseModel):
    skip: int = Query(ge=0, default=0)
    limit: int = Query(ge=1, le=100, default=10)


pagination_dependency = Annotated[PaginationParams, Depends(PaginationParams)]
