from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.core.enums import OrderBy
from school_management_system_lite.users.schemas.system_admin import UserFiltersAdmin
from school_management_system_lite.users.services import (
    system_admin as user_service_admin,
)
from school_management_system_lite.users.utils.enums import UserRole, UserSortField
from tests.factories import make_user


async def test_correct_paginated_shape(test_db_session: AsyncSession) -> None:
    await make_user(test_db_session, role=UserRole.SYSTEM_ADMIN)
    await make_user(test_db_session, role=UserRole.DIRECTOR)
    await make_user(test_db_session, role=UserRole.TEACHER)
    await make_user(test_db_session, role=UserRole.STUDENT)

    staff_paginated_response = await user_service_admin.list_staff(
        test_db_session,
        skip=0,
        limit=10,
        filters=UserFiltersAdmin(),
        sort_by=UserSortField.CREATED_AT,
        order=OrderBy.DESC,
    )

    assert staff_paginated_response.items is not None
    assert staff_paginated_response.total == 2
    assert staff_paginated_response.skip == 0
    assert staff_paginated_response.limit == 10
    assert staff_paginated_response.has_more is False


async def test_has_more_is_true_when_list_exceeds_limit(
    test_db_session: AsyncSession,
) -> None:
    await make_user(test_db_session, role=UserRole.SYSTEM_ADMIN)
    await make_user(test_db_session, role=UserRole.DIRECTOR)
    await make_user(test_db_session, role=UserRole.DIRECTOR)
    await make_user(test_db_session, role=UserRole.TEACHER)
    await make_user(test_db_session, role=UserRole.STUDENT)

    staff_paginated_response = await user_service_admin.list_staff(
        test_db_session,
        skip=0,
        limit=2,
        filters=UserFiltersAdmin(),
        sort_by=UserSortField.CREATED_AT,
        order=OrderBy.DESC,
    )

    assert staff_paginated_response.items is not None
    assert staff_paginated_response.total == 3
    assert staff_paginated_response.skip == 0
    assert staff_paginated_response.limit == 2
    assert staff_paginated_response.has_more is True


async def test_system_admin_and_students_are_not_included_in_the_list(
    test_db_session: AsyncSession,
) -> None:
    system_admin = await make_user(test_db_session, role=UserRole.SYSTEM_ADMIN)
    director = await make_user(test_db_session, role=UserRole.DIRECTOR)
    teacher = await make_user(test_db_session, role=UserRole.TEACHER)
    student = await make_user(test_db_session, role=UserRole.STUDENT)

    staff_paginated_response = await user_service_admin.list_staff(
        test_db_session,
        skip=0,
        limit=10,
        filters=UserFiltersAdmin(),
        sort_by=UserSortField.CREATED_AT,
        order=OrderBy.DESC,
    )

    ids = [item.id for item in staff_paginated_response.items]
    roles = [item.role for item in staff_paginated_response.items]

    assert system_admin.id not in ids
    assert system_admin.role not in roles
    assert director.id in ids
    assert director.role in roles
    assert teacher.id in ids
    assert teacher.role in roles
    assert student.id not in ids
    assert student.role not in roles
