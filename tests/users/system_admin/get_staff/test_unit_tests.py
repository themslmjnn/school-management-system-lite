from datetime import date
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.core.redis.cache_keys import UsersCacheKeys
from school_management_system_lite.users.schemas import (
    system_admin as user_schemas_admin,
)
from school_management_system_lite.users.services import (
    system_admin as user_service_admin,
)
from school_management_system_lite.users.utils.enums import UserRole
from school_management_system_lite.users.utils.exceptions import UserNotFoundError
from tests.factories import make_user


class TestSuccess:
    @pytest.mark.parametrize(
        ["role", "date_of_birth", "phone_number", "email"],
        [
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

        result = await user_service_admin.get_staff(
            test_db_session, test_redis_client, user.id
        )

        assert result.id == user.id
        assert result.first_name == user.first_name
        assert result.last_name == user.last_name
        assert result.middle_name == user.middle_name
        assert result.role == user.role
        assert result.status == user.status
        assert result.date_of_birth == user.date_of_birth
        assert result.phone_number == user.phone_number
        assert result.email == user.email
        assert result.created_at == user.created_at


class TestRolesScope:
    async def test_raises_error_when_trying_to_get_system_admin(
        self, test_db_session: AsyncSession, test_redis_client: Redis
    ) -> None:
        system_admin = await make_user(test_db_session, role=UserRole.SYSTEM_ADMIN)

        with pytest.raises(UserNotFoundError):
            await user_service_admin.get_staff(
                test_db_session, test_redis_client, system_admin.id
            )

    async def test_raises_error_on_unknown_users(
        self, test_db_session: AsyncSession, test_redis_client: Redis
    ) -> None:
        with pytest.raises(UserNotFoundError):
            await user_service_admin.get_staff(
                test_db_session, test_redis_client, 999999
            )


class TestCaching:
    async def test_cache_miss_gets_user_from_database_and_sets_cache(
        self,
        test_db_session: AsyncSession,
        test_redis_client: Redis | None,
        mock_users_get_cache_system_admin,
        mock_users_set_cache_system_admin,
    ) -> None:
        user = await make_user(
            test_db_session,
            role=UserRole.TEACHER,
        )

        response = await user_service_admin.get_staff(
            test_db_session,
            test_redis_client,
            user.id,
        )

        expected_key = UsersCacheKeys.detailed_response_key_admin(user.id)

        assert response.id == user.id

        mock_users_get_cache_system_admin.assert_awaited_once_with(
            test_redis_client,
            expected_key,
        )

        mock_users_set_cache_system_admin.assert_awaited_once_with(
            test_redis_client,
            expected_key,
            response.model_dump(mode="json"),
            900,
        )

    async def test_cache_hit_returns_cached_response_without_database_query(
        self,
        test_db_session: AsyncSession,
        test_redis_client: Redis | None,
        mock_users_get_cache_system_admin,
        mock_users_set_cache_system_admin,
        mocker,
    ) -> None:
        user = await make_user(
            test_db_session,
            role=UserRole.TEACHER,
        )

        cached_response = user_schemas_admin.UserResponseDetailedAdmin.model_validate(
            user
        )

        mock_users_get_cache_system_admin.return_value = cached_response.model_dump(
            mode="json"
        )

        mock_get_by_id = mocker.patch(
            "school_management_system_lite.users.services.system_admin.user_base_repository.get_by_id",
            new_callable=AsyncMock,
        )

        response = await user_service_admin.get_staff(
            test_db_session,
            test_redis_client,
            user.id,
        )

        expected_key = UsersCacheKeys.detailed_response_key_admin(user.id)

        assert response == cached_response

        mock_users_get_cache_system_admin.assert_awaited_once_with(
            test_redis_client,
            expected_key,
        )

        mock_get_by_id.assert_not_awaited()
        mock_users_set_cache_system_admin.assert_not_awaited()

    async def test_cache_hit_with_invalid_data_raises_validation_error(
        self,
        test_db_session: AsyncSession,
        test_redis_client: Redis | None,
        mock_users_get_cache_system_admin,
        mock_users_set_cache_system_admin,
        mocker,
    ) -> None:
        user = await make_user(
            test_db_session,
            role=UserRole.TEACHER,
        )

        mock_users_get_cache_system_admin.return_value = {
            "id": user.id,
            "first_name": None,
        }

        mock_get_by_id = mocker.patch(
            "school_management_system_lite.users.services.system_admin.user_base_repository.get_by_id",
            new_callable=AsyncMock,
        )

        with pytest.raises(ValidationError):
            await user_service_admin.get_staff(
                test_db_session,
                test_redis_client,
                user.id,
            )

        mock_get_by_id.assert_not_awaited()
        mock_users_set_cache_system_admin.assert_not_awaited()
