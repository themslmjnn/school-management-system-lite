from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.core.enums import OrderBy
from school_management_system_lite.core.pagination import PaginatedResponse
from school_management_system_lite.users.repositories import (
    base as user_base_repository,
)
from school_management_system_lite.users.schemas import (
    director as user_schemas_director,
)
from school_management_system_lite.users.utils.constants import TEACHER_ROLE
from school_management_system_lite.users.utils.enums import UserSortField


async def list_teachers(
    db_session: AsyncSession,
    skip: int,
    limit: int,
    filters: user_schemas_director.UserFiltersDirector,
    sort_by: UserSortField,
    order: OrderBy,
) -> PaginatedResponse:
    staff, total = await user_base_repository.list_users(
        db_session,
        allowed_roles=TEACHER_ROLE,
        skip=skip,
        limit=limit,
        filters=filters,
        sort_by=sort_by,
        order=order,
    )

    return PaginatedResponse(
        items=staff,
        total=total,
        skip=skip,
        limit=limit,
        has_more=skip + limit < total,
    )
