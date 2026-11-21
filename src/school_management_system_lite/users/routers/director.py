from typing import Annotated

from fastapi import APIRouter, Depends, status

from school_management_system_lite.core.dependencies.auth import require_director
from school_management_system_lite.core.dependencies.database import db_session_dep
from school_management_system_lite.core.enums import OrderBy
from school_management_system_lite.core.pagination import (
    PaginatedResponse,
    pagination_dependency,
)
from school_management_system_lite.users.schemas import (
    director as user_schemas_director,
)
from school_management_system_lite.users.services import (
    director as user_service_director,
)
from school_management_system_lite.users.utils.enums import UserSortField

router = APIRouter(tags=["Users Module - Director"])


@router.get(
    "/director/users/teachers",
    response_model=PaginatedResponse[user_schemas_director.UserResponseBaseDirector],
    status_code=status.HTTP_200_OK,
)
async def list_teachers(
    db_session: db_session_dep,
    _authenticated_user: require_director,
    pagination: pagination_dependency,
    filters: Annotated[user_schemas_director.UserFiltersDirector, Depends()],
    sort_by: UserSortField = UserSortField.CREATED_AT,
    order: OrderBy = OrderBy.DESC,
):
    return await user_service_director.list_teachers(
        db_session, pagination.skip, pagination.limit, filters, sort_by, order
    )
