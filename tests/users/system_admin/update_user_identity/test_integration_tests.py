import itertools

import pytest
from fastapi import status
from httpx import AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.core.redis.cache_keys import UsersCacheKeys
from school_management_system_lite.main import app
from school_management_system_lite.users.models.users import User
from school_management_system_lite.users.utils.enums import UserRole, UserStatus
from tests.conftest import make_auth_header
from tests.factories import make_user

pytestmark = pytest.mark.usefixtures("test_redis_client", "test_resend_client")

UNKNOWN_USER_ID = 999999

NON_ADMIN_ROLES = (UserRole.DIRECTOR, UserRole.TEACHER, UserRole.STUDENT)

EXISTING_AND_TARGET_ROLE_PAIRS = [
    pytest.param(
        existing_role,
        target_role,
        id=f"{existing_role.name.lower()}_exists-{target_role.name.lower()}_updated",
    )
    for existing_role, target_role in itertools.product(NON_ADMIN_ROLES, repeat=2)
]


def identity_url(user_id: int) -> str:
    return f"/admin/users/{user_id}/identity"


class TestSuccess:
    async def test_update_identity_with_all_fields_returns_204_and_saves_data(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
        teacher: User,
    ) -> None:
        payload = {
            "first_name": "Updated-Firstname",
            "last_name": "Updated-Lastname",
            "middle_name": "Updated-Middlename",
            "address": "Updated user address",
            "phone_number": "+992111222333",
        }
        headers = await make_auth_header(test_db_session, system_admin)

        response = await integration_client.patch(
            identity_url(teacher.id), headers=headers, json=payload
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        await test_db_session.refresh(teacher)

        for field, expected_value in payload.items():
            assert getattr(teacher, field) == expected_value

    async def test_update_identity_with_null_optional_fields_clears_them(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
        teacher: User,
    ) -> None:
        headers = await make_auth_header(test_db_session, system_admin)

        response = await integration_client.patch(
            identity_url(teacher.id),
            headers=headers,
            json={"middle_name": None, "address": None},
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        await test_db_session.refresh(teacher)

        assert teacher.middle_name is None
        assert teacher.address is None

    async def test_update_identity_without_redis_returns_204_and_saves_data(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
        teacher: User,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(app.state, "redis_client", None)
        headers = await make_auth_header(test_db_session, system_admin)

        response = await integration_client.patch(
            identity_url(teacher.id),
            headers=headers,
            json={"first_name": "Updated-Firstname"},
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        await test_db_session.refresh(teacher)

        assert teacher.first_name == "Updated-Firstname"


class TestAuth:
    async def test_update_identity_without_token_returns_401(
        self, integration_client: AsyncClient
    ) -> None:
        response = await integration_client.patch(
            identity_url(UNKNOWN_USER_ID),
            json={"first_name": "Updated-Firstname"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize(
        "caller_role",
        NON_ADMIN_ROLES,
        ids=lambda caller_role: caller_role.name.lower(),
    )
    async def test_update_identity_by_non_admin_returns_403(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        caller_role: UserRole,
    ) -> None:
        caller = await make_user(test_db_session, role=caller_role)
        headers = await make_auth_header(test_db_session, caller)

        response = await integration_client.patch(
            identity_url(UNKNOWN_USER_ID),
            headers=headers,
            json={"first_name": "Updated-Firstname"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestEligibleUsers:
    @pytest.mark.parametrize(
        "target_role",
        NON_ADMIN_ROLES,
        ids=lambda target_role: target_role.name.lower(),
    )
    async def test_update_identity_of_non_admin_role_returns_204(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
        target_role: UserRole,
    ) -> None:
        target_user = await make_user(test_db_session, role=target_role)
        headers = await make_auth_header(test_db_session, system_admin)

        response = await integration_client.patch(
            identity_url(target_user.id),
            headers=headers,
            json={"first_name": "Updated-Firstname"},
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        await test_db_session.refresh(target_user)

        assert target_user.first_name == "Updated-Firstname"

    @pytest.mark.parametrize(
        "target_status",
        list(UserStatus),
        ids=lambda target_status: target_status.name.lower(),
    )
    async def test_update_identity_of_user_in_any_status_returns_204(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
        target_status: UserStatus,
    ) -> None:
        target_user = await make_user(test_db_session, status=target_status)
        headers = await make_auth_header(test_db_session, system_admin)

        response = await integration_client.patch(
            identity_url(target_user.id),
            headers=headers,
            json={"first_name": "Updated-Firstname"},
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        await test_db_session.refresh(target_user)

        assert target_user.first_name == "Updated-Firstname"

    async def test_update_identity_of_unknown_user_returns_404(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
    ) -> None:
        headers = await make_auth_header(test_db_session, system_admin)

        response = await integration_client.patch(
            identity_url(UNKNOWN_USER_ID),
            headers=headers,
            json={"first_name": "Updated-Firstname"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["error_code"] == "USER_NOT_FOUND"

    async def test_update_identity_of_own_admin_account_returns_404(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
    ) -> None:
        original_first_name = system_admin.first_name
        headers = await make_auth_header(test_db_session, system_admin)

        response = await integration_client.patch(
            identity_url(system_admin.id),
            headers=headers,
            json={"first_name": "Updated-Firstname"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["error_code"] == "USER_NOT_FOUND"

        await test_db_session.refresh(system_admin)

        assert system_admin.first_name == original_first_name

    async def test_update_identity_of_another_admin_returns_404(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
    ) -> None:
        other_admin = await make_user(test_db_session, role=UserRole.SYSTEM_ADMIN)
        original_first_name = other_admin.first_name
        headers = await make_auth_header(test_db_session, system_admin)

        response = await integration_client.patch(
            identity_url(other_admin.id),
            headers=headers,
            json={"first_name": "Updated-Firstname"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["error_code"] == "USER_NOT_FOUND"

        await test_db_session.refresh(other_admin)

        assert other_admin.first_name == original_first_name


class TestPathValidation:
    @pytest.mark.parametrize(
        "user_id",
        [0, 2_147_483_648],
        ids=["below_minimum", "above_int32_maximum"],
    )
    async def test_update_identity_with_out_of_range_user_id_returns_422(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
        user_id: int,
    ) -> None:
        headers = await make_auth_header(test_db_session, system_admin)

        response = await integration_client.patch(
            identity_url(user_id),
            headers=headers,
            json={"first_name": "Updated-Firstname"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        assert response.json()["detail"][0]["loc"] == ["path", "user_id"]


class TestDBConstraints:
    @pytest.mark.parametrize(
        ["existing_role", "target_role"], EXISTING_AND_TARGET_ROLE_PAIRS
    )
    async def test_update_identity_with_taken_phone_returns_409(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
        existing_role: UserRole,
        target_role: UserRole,
    ) -> None:
        existing_user = await make_user(test_db_session, role=existing_role)
        target_user = await make_user(test_db_session, role=target_role)
        headers = await make_auth_header(test_db_session, system_admin)

        await test_db_session.commit()

        original_first_name = target_user.first_name
        original_phone_number = target_user.phone_number

        response = await integration_client.patch(
            identity_url(target_user.id),
            headers=headers,
            json={
                "first_name": "Updated-Firstname",
                "phone_number": existing_user.phone_number,
            },
        )

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.json()["error_code"] == "PHONE_NUMBER_ALREADY_TAKEN"

        await test_db_session.refresh(target_user)

        assert target_user.first_name == original_first_name
        assert target_user.phone_number == original_phone_number

    # Redis
    async def test_update_identity_with_new_value_removes_cached_user_keys(
        self,
        test_db_session: AsyncSession,
        test_redis_client: Redis | None,
        integration_client: AsyncClient,
        system_admin: User,
        teacher: User,
    ) -> None:
        if test_redis_client is None:
            pytest.skip("Redis is not available")

        cache_keys = (
            UsersCacheKeys.detailed_response_key_admin(teacher.id),
            UsersCacheKeys.detailed_response_key_staff(teacher.id),
            UsersCacheKeys.detailed_response_key_self(teacher.id),
        )

        for cache_key in cache_keys:
            await test_redis_client.set(cache_key, "cached")

        headers = await make_auth_header(test_db_session, system_admin)

        response = await integration_client.patch(
            identity_url(teacher.id),
            headers=headers,
            json={"first_name": "Updated-Firstname"},
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        assert await test_redis_client.exists(*cache_keys) == 0
