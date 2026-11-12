from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.core.enums import OrderBy
from school_management_system_lite.users.models import User
from school_management_system_lite.users.schemas.system_admin import (
    UserBaseFilters,
    UserFiltersAdmin,
)
from school_management_system_lite.users.utils.enums import UserRole, UserSortField


async def get_by_id(
    db_session: AsyncSession,
    user_id: int,
    excluded_roles: frozenset[UserRole] | None = None,
    allowed_roles: frozenset | None = None,
) -> User | None:
    stmt = select(User).where(User.id == user_id)

    if excluded_roles:
        stmt = stmt.where(User.role.not_in(excluded_roles))

    if allowed_roles:
        stmt = stmt.where(User.role.in_(allowed_roles))

    result = await db_session.execute(stmt)

    return result.scalar_one_or_none()


async def get_by_email(db_session: AsyncSession, email: str) -> User | None:
    stmt = select(User).where(User.email == email)

    result = await db_session.execute(stmt)

    return result.scalar_one_or_none()


def apply_base_filters(
    base_query: Select, filters: UserBaseFilters | UserFiltersAdmin
) -> Select:
    if filters is None:
        return base_query

    if filters.first_name:
        base_query = base_query.filter(User.first_name.ilike(f"%{filters.first_name}%"))

    if filters.last_name:
        base_query = base_query.filter(User.last_name.ilike(f"%{filters.last_name}%"))

    if filters.phone_number:
        base_query = base_query.filter(
            User.phone_number.ilike(f"%{filters.phone_number}%")
        )

    return base_query


def apply_sorting(base_query: Select, sort_by: str, order: str) -> Select:
    if sort_by not in UserSortField:
        sort_by = UserSortField.CREATED_AT

    sort_column = getattr(User, sort_by)

    if order == OrderBy.DESC:
        return base_query.order_by(sort_column.desc())

    return base_query.order_by(sort_column.asc())


async def paginate(
    db_session: AsyncSession,
    stmt: Select,
    skip: int,
    limit: int,
) -> tuple[list[User], int]:

    count_result = await db_session.execute(
        select(func.count()).select_from(stmt.subquery())
    )

    total = count_result.scalar_one()

    result = await db_session.execute(stmt.offset(skip).limit(limit))

    return result.scalars().all(), total


async def get_users(
    db_session: AsyncSession,
    *,
    excluded_roles: frozenset[UserRole] | None = None,
    allowed_roles: frozenset[UserRole] | None = None,
    filters: UserBaseFilters | UserFiltersAdmin,
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

    stmt = apply_base_filters(stmt, filters)
    stmt = apply_sorting(stmt, sort_by, order)

    return await paginate(db_session, stmt, skip, limit)
