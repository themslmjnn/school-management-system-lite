import fastapi
import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.users.models.users import User
from school_management_system_lite.users.utils.enums import UserRole, UserStatus
from tests.conftest import make_auth_header
from tests.factories import make_user


class TestSuccess:
    async def test_successful_user_account_deactivation(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
        mock_users_delete_cache_system_admin,
    ) -> None:
        user = await make_user(test_db_session, role=UserRole.TEACHER)

        header = await make_auth_header(test_db_session, system_admin)

        response = await integration_client.patch(
            f"/admin/users/{user.id}/account/deactivate", headers=header
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT


class TestAuth:
    async def test_unauthenticated_requests_raise_401(
        self, integration_client: AsyncClient
    ) -> None:
        response = await integration_client.patch(
            "/admin/users/9999999/account/deactivate"
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize(
        "role", [UserRole.DIRECTOR, UserRole.TEACHER, UserRole.STUDENT]
    )
    async def test_raises_403_on_non_admins(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        role: UserRole,
    ) -> None:
        user = await make_user(test_db_session, role=role)

        header = await make_auth_header(test_db_session, user)

        response = await integration_client.patch(
            "/admin/users/9999999/account/deactivate",
            headers=header,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestEligibleUsers:
    async def test_deactivating_system_admin_account_is_prevented(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
    ) -> None:
        header = await make_auth_header(test_db_session, system_admin)

        response = await integration_client.patch(
            f"/admin/users/{system_admin.id}/account/deactivate",
            headers=header,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_system_admin_cannot_deactivate_another_system_admin_account(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
    ) -> None:
        user = await make_user(test_db_session, role=UserRole.SYSTEM_ADMIN)

        header = await make_auth_header(test_db_session, system_admin)

        response = await integration_client.patch(
            f"/admin/users/{user.id}/account/deactivate",
            headers=header,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_raise_error_on_unknown_users(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
    ) -> None:
        header = await make_auth_header(test_db_session, system_admin)

        response = await integration_client.patch(
            "/admin/users/999999/account/deactivate",
            headers=header,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestEligibleStatuses:
    async def test_raise_error_on_inactive_accounts(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
    ) -> None:
        user = await make_user(
            test_db_session, role=UserRole.TEACHER, status=UserStatus.INACTIVE
        )

        header = await make_auth_header(test_db_session, system_admin)

        response = await integration_client.patch(
            f"/admin/users/{user.id}/account/deactivate",
            headers=header,
        )

        assert response.status_code == status.HTTP_409_CONFLICT

    async def test_raise_error_on_pending_activation_accounts_accounts(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
    ) -> None:
        user = await make_user(
            test_db_session, role=UserRole.TEACHER, status=UserStatus.PENDING_ACTIVATION
        )

        header = await make_auth_header(test_db_session, system_admin)

        response = await integration_client.patch(
            f"/admin/users/{user.id}/account/deactivate",
            headers=header,
        )

        assert response.status_code == status.HTTP_409_CONFLICT

    @pytest.mark.parametrize(
        "status",
        [
            UserStatus.ACTIVE,
            UserStatus.EXPELLED,
            UserStatus.GRADUATED,
            UserStatus.WITHDRAWN,
        ],
    )
    async def test_allow_deactivating_non_inactive_and_pending_activation_accounts(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
        status: UserStatus,
    ) -> None:
        user = await make_user(test_db_session, role=UserRole.TEACHER, status=status)

        header = await make_auth_header(test_db_session, system_admin)

        response = await integration_client.patch(
            f"/admin/users/{user.id}/account/deactivate",
            headers=header,
        )

        assert response.status_code == fastapi.status.HTTP_204_NO_CONTENT
