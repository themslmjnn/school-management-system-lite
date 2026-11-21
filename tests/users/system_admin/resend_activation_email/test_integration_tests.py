import fastapi
import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.users.models import User
from school_management_system_lite.users.utils.enums import UserRole, UserStatus
from tests.conftest import make_auth_header
from tests.factories import make_user


class TestSuccess:
    async def test_successfully_resend_activation_email(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
    ) -> None:
        user = await make_user(
            test_db_session,
            role=UserRole.TEACHER,
            status=UserStatus.PENDING_ACTIVATION,
        )

        header = await make_auth_header(test_db_session, system_admin)

        response = await integration_client.post(
            f"/admin/users/{user.id}/activation-email",
            headers=header,
        )

        assert response.status_code == status.HTTP_202_ACCEPTED


class TestAuth:
    async def test_unauthenticated_requests_raise_401(
        self,
        integration_client: AsyncClient,
    ) -> None:
        response = await integration_client.post(
            "/admin/users/999999/activation-email",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize(
        "role",
        [
            UserRole.DIRECTOR,
            UserRole.TEACHER,
            UserRole.STUDENT,
        ],
    )
    async def test_raises_403_on_non_admins(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        role: UserRole,
    ) -> None:
        user = await make_user(
            test_db_session,
            role=role,
        )

        header = await make_auth_header(
            test_db_session,
            user,
        )

        response = await integration_client.post(
            "/admin/users/999999/activation-email",
            headers=header,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestEligibleUsers:
    async def test_resending_activation_email_for_system_admin_is_prevented(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
    ) -> None:
        header = await make_auth_header(
            test_db_session,
            system_admin,
        )

        response = await integration_client.post(
            f"/admin/users/{system_admin.id}/activation-email",
            headers=header,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_system_admin_cannot_resend_activation_email_for_another_system_admin(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
    ) -> None:
        user = await make_user(test_db_session, role=UserRole.SYSTEM_ADMIN)

        header = await make_auth_header(
            test_db_session,
            system_admin,
        )

        response = await integration_client.post(
            f"/admin/users/{user.id}/activation-email",
            headers=header,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_raise_error_on_unknown_users(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
    ) -> None:
        header = await make_auth_header(
            test_db_session,
            system_admin,
        )

        response = await integration_client.post(
            "/admin/users/999999/activation-email",
            headers=header,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestEligibleStatuses:
    @pytest.mark.parametrize(
        "status",
        [
            UserStatus.ACTIVE,
            UserStatus.INACTIVE,
            UserStatus.EXPELLED,
            UserStatus.GRADUATED,
            UserStatus.WITHDRAWN,
        ],
    )
    async def test_raise_error_for_non_pending_activation_accounts(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
        status: UserStatus,
    ) -> None:
        user = await make_user(
            test_db_session,
            role=UserRole.TEACHER,
            status=status,
        )

        header = await make_auth_header(
            test_db_session,
            system_admin,
        )

        response = await integration_client.post(
            f"/admin/users/{user.id}/activation-email",
            headers=header,
        )

        assert response.status_code == fastapi.status.HTTP_409_CONFLICT
