import itertools

import pytest
from fastapi import status
from httpx import AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.core.enums import OrderBy
from school_management_system_lite.core.redis.cache_keys import UsersCacheKeys
from school_management_system_lite.emails import repository as email_repository
from school_management_system_lite.users.models.user import User
from school_management_system_lite.users.utils.enums import UserRole
from tests.conftest import make_auth_header
from tests.factories import make_user

pytestmark = pytest.mark.usefixtures("test_redis_client")

NEW_EMAIL = "updated_email@gmail.com"
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


class TestSuccess:
    async def test_update_email_as_system_admin_returns_204_and_saves_email(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
    ) -> None:
        target_user = await make_user(test_db_session, role=UserRole.TEACHER)
        admin_headers = await make_auth_header(test_db_session, system_admin)

        response = await integration_client.patch(
            f"/admin/users/{target_user.id}/email",
            headers=admin_headers,
            json={"email": NEW_EMAIL},
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        await test_db_session.refresh(target_user)

        assert target_user.email == NEW_EMAIL

    async def test_update_email_as_system_admin_records_admin_on_queued_emails(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
    ) -> None:
        target_user = await make_user(test_db_session, role=UserRole.TEACHER)
        old_email = target_user.email
        admin_headers = await make_auth_header(test_db_session, system_admin)

        response = await integration_client.patch(
            f"/admin/users/{target_user.id}/email",
            headers=admin_headers,
            json={"email": NEW_EMAIL},
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        old_address_emails = await email_repository.get_by_recipient_email(
            test_db_session, old_email, order_by=OrderBy.DESC
        )
        new_address_emails = await email_repository.get_by_recipient_email(
            test_db_session, NEW_EMAIL, order_by=OrderBy.DESC
        )
        triggered_by_ids = [
            queued_email.triggered_by
            for queued_email in [*old_address_emails, *new_address_emails]
        ]

        assert triggered_by_ids == [system_admin.id, system_admin.id]

    async def test_update_email_with_redis_available_deletes_user_cache_keys(
        self,
        test_db_session: AsyncSession,
        test_redis_client: Redis | None,
        integration_client: AsyncClient,
        system_admin: User,
    ) -> None:
        if test_redis_client is None:
            pytest.skip("Redis is not available")

        target_user = await make_user(test_db_session, role=UserRole.TEACHER)
        admin_headers = await make_auth_header(test_db_session, system_admin)
        cache_keys = (
            UsersCacheKeys.detailed_response_key_admin(target_user.id),
            UsersCacheKeys.detailed_response_key_self(target_user.id),
        )

        for cache_key in cache_keys:
            await test_redis_client.set(cache_key, "cached-response")

        response = await integration_client.patch(
            f"/admin/users/{target_user.id}/email",
            headers=admin_headers,
            json={"email": NEW_EMAIL},
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert await test_redis_client.exists(*cache_keys) == 0

    async def test_update_email_with_target_old_access_token_returns_401(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
    ) -> None:
        target_user = await make_user(test_db_session, role=UserRole.TEACHER)
        admin_headers = await make_auth_header(test_db_session, system_admin)
        old_target_headers = await make_auth_header(test_db_session, target_user)

        response_before_update = await integration_client.get(
            "/users/me", headers=old_target_headers
        )

        assert response_before_update.status_code == status.HTTP_200_OK

        update_response = await integration_client.patch(
            f"/admin/users/{target_user.id}/email",
            headers=admin_headers,
            json={"email": NEW_EMAIL},
        )

        assert update_response.status_code == status.HTTP_204_NO_CONTENT

        response_after_update = await integration_client.get(
            "/users/me", headers=old_target_headers
        )

        assert response_after_update.status_code == status.HTTP_401_UNAUTHORIZED


class TestAuth:
    async def test_update_email_without_token_returns_401(
        self, integration_client: AsyncClient
    ) -> None:
        response = await integration_client.patch(
            f"/admin/users/{UNKNOWN_USER_ID}/email",
            json={"email": NEW_EMAIL},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize(
        "caller_role",
        NON_ADMIN_ROLES,
        ids=[role.name.lower() for role in NON_ADMIN_ROLES],
    )
    async def test_update_email_as_non_admin_returns_403(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        caller_role: UserRole,
    ) -> None:
        caller = await make_user(test_db_session, role=caller_role)
        caller_headers = await make_auth_header(test_db_session, caller)

        response = await integration_client.patch(
            f"/admin/users/{UNKNOWN_USER_ID}/email",
            headers=caller_headers,
            json={"email": NEW_EMAIL},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestEligibleUsers:
    async def test_update_email_for_system_admin_returns_404(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
    ) -> None:
        other_admin = await make_user(test_db_session, role=UserRole.SYSTEM_ADMIN)
        admin_headers = await make_auth_header(test_db_session, system_admin)

        response = await integration_client.patch(
            f"/admin/users/{other_admin.id}/email",
            headers=admin_headers,
            json={"email": NEW_EMAIL},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_update_email_for_unknown_user_returns_404(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
    ) -> None:
        admin_headers = await make_auth_header(test_db_session, system_admin)

        response = await integration_client.patch(
            f"/admin/users/{UNKNOWN_USER_ID}/email",
            headers=admin_headers,
            json={"email": NEW_EMAIL},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestDBConstraints:
    @pytest.mark.parametrize(
        ["existing_role", "target_role"], EXISTING_AND_TARGET_ROLE_PAIRS
    )
    async def test_update_email_with_taken_email_returns_409(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
        existing_role: UserRole,
        target_role: UserRole,
    ) -> None:
        existing_user = await make_user(test_db_session, role=existing_role)
        target_user = await make_user(test_db_session, role=target_role)
        admin_headers = await make_auth_header(test_db_session, system_admin)

        await test_db_session.commit()

        original_email = target_user.email

        response = await integration_client.patch(
            f"/admin/users/{target_user.id}/email",
            headers=admin_headers,
            json={"email": existing_user.email},
        )

        assert response.status_code == status.HTTP_409_CONFLICT

        await test_db_session.refresh(target_user)

        assert target_user.email == original_email
