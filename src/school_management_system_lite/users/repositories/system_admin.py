from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.core.enums import OrderBy
from school_management_system_lite.users.models import User
from school_management_system_lite.users.repositories.base import (
    apply_base_filters,
    apply_sorting,
    paginate,
)
from school_management_system_lite.users.schemas.system_admin import UserFiltersAdmin
from school_management_system_lite.users.utils.enums import UserRole, UserSortField


def apply_admin_filters(base_query: Select, filters: UserFiltersAdmin) -> Select:
    if filters is None:
        return base_query

    base_query = apply_base_filters(base_query, filters)

    if filters.email:
        base_query = base_query.filter(User.email.ilike(f"%{filters.email}%"))

    return base_query


async def get_users_admin(
    db_session: AsyncSession,
    *,
    excluded_roles: frozenset[UserRole] | None = None,
    allowed_roles: frozenset[UserRole] | None = None,
    filters: UserFiltersAdmin,
    sort_by: str = UserSortField.CREATED_AT,
    order: str = OrderBy.DESC,
    skip: int = 0,
    limit: int = 10,
) -> tuple[list[User], int]:
    stmt = select(User)

    if excluded_roles:
        stmt = stmt.filter(User.role.not_in(excluded_roles))

    if allowed_roles:
        stmt = stmt.filter(User.role.in_(allowed_roles))

    stmt = apply_admin_filters(stmt, filters)
    stmt = apply_sorting(stmt, sort_by, order)

    return await paginate(db_session, stmt, skip, limit)
