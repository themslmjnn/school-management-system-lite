import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.core.enums import OrderBy
from school_management_system_lite.users.repositories import (
    system_admin as user_repository_admin,
)
from school_management_system_lite.users.schemas.system_admin import UserFiltersAdmin
from school_management_system_lite.users.utils.enums import UserRole, UserSortField
from tests.factories import make_user


class TestFilters:
    async def test_return_all_list_when_filters_are_none(
        self, test_db_session: AsyncSession
    ) -> None:
        director = await make_user(test_db_session, role=UserRole.DIRECTOR)
        teacher = await make_user(test_db_session, role=UserRole.TEACHER)
        student = await make_user(test_db_session, role=UserRole.STUDENT)

        staff, _ = await user_repository_admin.list_users(
            test_db_session, filters=UserFiltersAdmin()
        )

        ids = [item.id for item in staff]
        roles = [item.role for item in staff]

        assert [director.id, teacher.id, student.id] == ids
        assert [director.role, teacher.role, student.role] == roles

    @pytest.mark.parametrize(
        ("filter_field", "matching_values", "non_matching_value", "filter_value"),
        [
            (
                "first_name",
                ("Umarali", "Umar"),
                "Shavkat",
                "umar",
            ),
            (
                "last_name",
                ("Mirzoev", "Mirzoev"),
                "Misokov",
                "mirzo",
            ),
            (
                "phone_number",
                ("+992111111111", "+992111111222"),
                "+992222222222",
                "111",
            ),
            (
                "email",
                ("umarali@gmail.com", "umar@gmail.com"),
                "shavkat@gmail.com",
                "umar",
            ),
        ],
    )
    async def test_applies_filter(
        self,
        test_db_session: AsyncSession,
        filter_field: str,
        matching_values: tuple[str, str],
        non_matching_value: str,
        filter_value: str,
    ) -> None:
        director = await make_user(
            test_db_session,
            role=UserRole.DIRECTOR,
            **{filter_field: matching_values[0]},
        )
        teacher_one = await make_user(
            test_db_session,
            role=UserRole.TEACHER,
            **{filter_field: matching_values[1]},
        )
        teacher_two = await make_user(
            test_db_session,
            role=UserRole.TEACHER,
            **{filter_field: non_matching_value},
        )

        staff, total = await user_repository_admin.list_users(
            test_db_session,
            filters=UserFiltersAdmin(**{filter_field: filter_value}),
        )

        ids = [item.id for item in staff]

        assert total == 2
        assert [director.id, teacher_one.id] == ids
        assert teacher_two.id not in ids

    async def test_applies_multiple_filters(
        self, test_db_session: AsyncSession
    ) -> None:
        matching_user = await make_user(
            test_db_session,
            role=UserRole.DIRECTOR,
            first_name="Umarali",
            last_name="Mirzoev",
        )
        await make_user(
            test_db_session,
            role=UserRole.TEACHER,
            first_name="Shavkat",
            last_name="Mirzoev",
        )
        await make_user(
            test_db_session,
            role=UserRole.TEACHER,
            first_name="Umarali",
            last_name="Misokov",
        )

        staff, total = await user_repository_admin.list_users(
            test_db_session,
            filters=UserFiltersAdmin(
                first_name="umar",
                last_name="mirzo",
            ),
        )

        assert total == 1
        assert [item.id for item in staff] == [matching_user.id]


class TestSorting:
    async def test_unknown_sort_by_value_falls_back_to_default(
        self, test_db_session: AsyncSession
    ) -> None:
        await make_user(test_db_session, role=UserRole.DIRECTOR)
        await make_user(test_db_session, role=UserRole.TEACHER)
        await make_user(test_db_session, role=UserRole.STUDENT)

        unknown_value_result, _ = await user_repository_admin.list_users(
            test_db_session,
            filters=UserFiltersAdmin(),
            sort_by="unknown",
        )

        default_value_result, _ = await user_repository_admin.list_users(
            test_db_session,
            filters=UserFiltersAdmin(),
            sort_by=UserSortField.CREATED_AT,
        )

        assert unknown_value_result == default_value_result

    async def test_applies_created_at_sort_by_value(
        self, test_db_session: AsyncSession
    ) -> None:
        director = await make_user(test_db_session, role=UserRole.DIRECTOR)
        teacher = await make_user(test_db_session, role=UserRole.TEACHER)
        student = await make_user(test_db_session, role=UserRole.STUDENT)

        staff, _ = await user_repository_admin.list_users(
            test_db_session,
            filters=UserFiltersAdmin(),
            sort_by=UserSortField.CREATED_AT,
        )

        ids = [item.id for item in staff]

        assert [director.id, teacher.id, student.id] == ids

    async def test_applies_first_name_sort_by_value(
        self, test_db_session: AsyncSession
    ) -> None:
        director = await make_user(
            test_db_session, role=UserRole.DIRECTOR, first_name="Shavkat"
        )
        teacher = await make_user(
            test_db_session, role=UserRole.TEACHER, first_name="Behruz"
        )
        student = await make_user(
            test_db_session, role=UserRole.STUDENT, first_name="Aziz"
        )

        staff, _ = await user_repository_admin.list_users(
            test_db_session,
            filters=UserFiltersAdmin(),
            sort_by=UserSortField.FIRST_NAME,
        )

        ids = [item.id for item in staff]

        assert [director.id, teacher.id, student.id] == ids

    async def test_applies_last_name_sort_by_value(
        self, test_db_session: AsyncSession
    ) -> None:
        director = await make_user(
            test_db_session, role=UserRole.DIRECTOR, last_name="Mirzoev"
        )
        teacher = await make_user(
            test_db_session, role=UserRole.TEACHER, last_name="Aliev"
        )
        student = await make_user(
            test_db_session, role=UserRole.STUDENT, last_name="Idrisov"
        )

        staff, _ = await user_repository_admin.list_users(
            test_db_session, filters=UserFiltersAdmin(), sort_by=UserSortField.LAST_NAME
        )

        ids = [item.id for item in staff]

        assert [director.id, student.id, teacher.id] == ids

    async def test_applies_ascending_order_by_value(
        self, test_db_session: AsyncSession
    ) -> None:
        director = await make_user(
            test_db_session, role=UserRole.DIRECTOR, last_name="Mirzoev"
        )
        teacher = await make_user(
            test_db_session, role=UserRole.TEACHER, last_name="Aliev"
        )
        student = await make_user(
            test_db_session, role=UserRole.STUDENT, last_name="Idrisov"
        )

        staff, _ = await user_repository_admin.list_users(
            test_db_session,
            filters=UserFiltersAdmin(),
            sort_by=UserSortField.LAST_NAME,
            order=OrderBy.ASC,
        )

        ids = [item.id for item in staff]

        assert [teacher.id, student.id, director.id] == ids


class TestRolesScope:
    async def test_excludes_system_admin_from_list(
        self, test_db_session: AsyncSession
    ) -> None:
        await make_user(test_db_session, role=UserRole.DIRECTOR)
        await make_user(test_db_session, role=UserRole.TEACHER)
        system_admin = await make_user(test_db_session, role=UserRole.SYSTEM_ADMIN)

        staff, total = await user_repository_admin.list_users(
            test_db_session,
            filters=UserFiltersAdmin(),
        )

        ids = [item.id for item in staff]
        roles = [item.role for item in staff]

        assert system_admin.id not in ids
        assert system_admin.role not in roles
        assert total == 2

    async def test_applies_excluded_roles_parameter(
        self, test_db_session: AsyncSession
    ) -> None:
        await make_user(test_db_session, role=UserRole.DIRECTOR, last_name="Mirzoev")
        await make_user(test_db_session, role=UserRole.TEACHER, last_name="Aliev")
        student = await make_user(
            test_db_session, role=UserRole.STUDENT, last_name="Idrisov"
        )

        staff, total = await user_repository_admin.list_users(
            test_db_session,
            filters=UserFiltersAdmin(),
            excluded_roles=frozenset({UserRole.STUDENT}),
        )

        ids = [item.id for item in staff]

        assert student.id not in ids
        assert total == 2

    async def test_applies_allowed_roles_parameter(
        self, test_db_session: AsyncSession
    ) -> None:
        director = await make_user(test_db_session, role=UserRole.DIRECTOR)
        teacher = await make_user(test_db_session, role=UserRole.TEACHER)
        student_one = await make_user(test_db_session, role=UserRole.STUDENT)
        student_two = await make_user(test_db_session, role=UserRole.STUDENT)

        staff, total = await user_repository_admin.list_users(
            test_db_session,
            filters=UserFiltersAdmin(),
            allowed_roles=frozenset({UserRole.STUDENT}),
        )

        ids = [item.id for item in staff]

        assert student_one.id in ids
        assert student_two.id in ids
        assert director.id not in ids
        assert teacher.id not in ids
        assert total == 2


class TestPagination:
    async def test_applies_skip_and_limit(self, test_db_session: AsyncSession) -> None:
        await make_user(test_db_session, role=UserRole.DIRECTOR)
        teacher = await make_user(test_db_session, role=UserRole.TEACHER)
        await make_user(test_db_session, role=UserRole.STUDENT)

        staff, total = await user_repository_admin.list_users(
            test_db_session,
            filters=UserFiltersAdmin(),
            skip=1,
            limit=1,
            sort_by=UserSortField.CREATED_AT,
            order=OrderBy.ASC,
        )

        assert total == 3
        assert [item.id for item in staff] == [teacher.id]
