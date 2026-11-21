from datetime import date

import pytest
from pydantic import ValidationError
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.core.redis.cache_keys import UsersCacheKeys
from school_management_system_lite.users.schemas import (
    shared as user_schemas_shared,
)
from school_management_system_lite.users.services import (
    shared as user_service_shared,
)
from school_management_system_lite.users.utils.enums import UserRole
from school_management_system_lite.users.utils.exceptions import UserNotFoundError
from tests.factories import make_user


class TestSuccess:
    @pytest.mark.parametrize(
        ["role", "date_of_birth", "phone_number", "email"],
        [
            (
                UserRole.SYSTEM_ADMIN,
                date(1995, 5, 1),
                "+992777777777",
                "valid_admin_email@gmail.com",
            ),
            (
                UserRole.DIRECTOR,
                date(1990, 5, 1),
                "+992999999999",
                "valid_director_email@gmail.com",
            ),
            (
                UserRole.TEACHER,
                date(2000, 5, 1),
                "+992888888888",
                "valid_teacher_email@gmail.com",
            ),
        ],
    )
    async def test_correct_shape(
        self,
        test_db_session: AsyncSession,
        test_redis_client: Redis | None,
        role: UserRole,
        date_of_birth: date,
        phone_number: str,
        email: str,
    ) -> None:
        user = await make_user(
            test_db_session,
            role=role,
            date_of_birth=date_of_birth,
            phone_number=phone_number,
            email=email,
        )

        result = await user_service_shared.get_my_profile(
            test_db_session, test_redis_client, user.id
        )

        assert result.id == user.id
        assert result.first_name == user.first_name
        assert result.last_name == user.last_name
        assert result.middle_name == user.middle_name
        assert result.date_of_birth == user.date_of_birth
        assert result.phone_number == user.phone_number
        assert result.email == user.email
        assert result.created_at == user.created_at


class TestRolesScope:
    async def test_raises_error_when_trying_to_get_student(
        self, test_db_session: AsyncSession, test_redis_client: Redis
    ) -> None:
        student = await make_user(test_db_session, role=UserRole.STUDENT)

        with pytest.raises(UserNotFoundError):
            await user_service_shared.get_my_profile(
                test_db_session, test_redis_client, student.id
            )

    async def test_raises_error_on_unknown_users(
        self, test_db_session: AsyncSession, test_redis_client: Redis
    ) -> None:
        with pytest.raises(UserNotFoundError):
            await user_service_shared.get_my_profile(
                test_db_session, test_redis_client, 999999
            )


class TestCaching:
    async def test_cache_miss_gets_user_from_database_and_sets_cache(
        self,
        test_db_session: AsyncSession,
        test_redis_client: Redis | None,
        mock_users_get_cache_shared,
        mock_users_set_cache_shared,
    ) -> None:
        user = await make_user(
            test_db_session,
            role=UserRole.TEACHER,
        )

        response = await user_service_shared.get_my_profile(
            test_db_session,
            test_redis_client,
            user.id,
        )

        expected_key = UsersCacheKeys.detailed_response_key_self(user.id)

        assert response.id == user.id

        mock_users_get_cache_shared.assert_awaited_once_with(
            test_redis_client,
            expected_key,
        )

        mock_users_set_cache_shared.assert_awaited_once_with(
            test_redis_client,
            expected_key,
            response.model_dump(mode="json"),
            900,
        )

    async def test_cache_hit_returns_cached_response_without_database_query(
        self,
        test_db_session: AsyncSession,
        test_redis_client: Redis | None,
        mock_users_get_cache_shared,
        mock_users_set_cache_shared,
        mock_user_base_repository_get_user_by_id_shared,
    ) -> None:
        user = await make_user(
            test_db_session,
            role=UserRole.TEACHER,
        )

        cached_response = user_schemas_shared.UserSelfResponseDetailed.model_validate(
            user
        )

        mock_users_get_cache_shared.return_value = cached_response.model_dump(
            mode="json"
        )

        response = await user_service_shared.get_my_profile(
            test_db_session,
            test_redis_client,
            user.id,
        )

        expected_key = UsersCacheKeys.detailed_response_key_self(user.id)

        assert response == cached_response

        mock_users_get_cache_shared.assert_awaited_once_with(
            test_redis_client,
            expected_key,
        )

        mock_user_base_repository_get_user_by_id_shared.assert_not_awaited()
        mock_users_set_cache_shared.assert_not_awaited()

    async def test_cache_hit_with_invalid_data_raises_validation_error(
        self,
        test_db_session: AsyncSession,
        test_redis_client: Redis | None,
        mock_users_get_cache_shared,
        mock_users_set_cache_shared,
        mock_user_base_repository_get_user_by_id_shared,
    ) -> None:
        user = await make_user(
            test_db_session,
            role=UserRole.TEACHER,
        )

        mock_users_get_cache_shared.return_value = {
            "id": user.id,
            "first_name": None,
        }

        with pytest.raises(ValidationError):
            await user_service_shared.get_my_profile(
                test_db_session,
                test_redis_client,
                user.id,
            )

        mock_user_base_repository_get_user_by_id_shared.assert_not_awaited()
        mock_users_set_cache_shared.assert_not_awaited()
