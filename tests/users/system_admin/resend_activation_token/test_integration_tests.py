import fastapi
import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.users.models import User
from school_management_system_lite.users.utils.enums import UserRole, UserStatus
from tests.conftest import make_auth_header
from tests.factories import make_system_admin, make_teacher, make_user

ENDPOINT = "/admin/users/{}/resend-activation"


class TestSuccess:
    async def test_successfully_resend_activation_token(
        self,
        test_db_session: AsyncSession,
        client: AsyncClient,
        system_admin: User,
    ) -> None:
        user = await make_teacher(
            test_db_session,
            status=UserStatus.PENDING_ACTIVATION,
        )

        header = await make_auth_header(test_db_session, system_admin)

        response = await client.patch(
            ENDPOINT.format(user.id),
            headers=header,
        )

        assert response.status_code == status.HTTP_202_ACCEPTED


class TestAuth:
    async def test_unauthenticated_requests_raise_401(
        self,
        client: AsyncClient,
    ) -> None:
        response = await client.patch(
            ENDPOINT.format(999999),
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
        client: AsyncClient,
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

        response = await client.patch(
            ENDPOINT.format(999999),
            headers=header,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestEligibleUsers:
    async def test_resending_activation_token_for_system_admin_is_prevented(
        self,
        test_db_session: AsyncSession,
        client: AsyncClient,
        system_admin: User,
    ) -> None:
        header = await make_auth_header(
            test_db_session,
            system_admin,
        )

        response = await client.patch(
            ENDPOINT.format(system_admin.id),
            headers=header,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_system_admin_cannot_resend_activation_token_for_another_system_admin(
        self,
        test_db_session: AsyncSession,
        client: AsyncClient,
        system_admin: User,
    ) -> None:
        user = await make_system_admin(test_db_session)

        header = await make_auth_header(
            test_db_session,
            system_admin,
        )

        response = await client.patch(
            ENDPOINT.format(user.id),
            headers=header,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_raise_error_on_unknown_users(
        self,
        test_db_session: AsyncSession,
        client: AsyncClient,
        system_admin: User,
    ) -> None:
        header = await make_auth_header(
            test_db_session,
            system_admin,
        )

        response = await client.patch(
            ENDPOINT.format(999999),
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
        client: AsyncClient,
        system_admin: User,
        status: UserStatus,
    ) -> None:
        user = await make_teacher(
            test_db_session,
            status=status,
        )

        header = await make_auth_header(
            test_db_session,
            system_admin,
        )

        response = await client.patch(
            ENDPOINT.format(user.id),
            headers=header,
        )

        assert response.status_code == fastapi.status.HTTP_409_CONFLICT
