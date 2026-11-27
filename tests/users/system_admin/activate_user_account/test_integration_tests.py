import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.users.models.user import User
from school_management_system_lite.users.utils.enums import UserRole, UserStatus
from tests.factories import make_user
from tests.helpers import make_auth_header

UNKNOWN_USER_ID = 999_999

pytestmark = pytest.mark.usefixtures("test_redis_client", "test_resend_client")


class TestSuccess:
    async def test_activate_user_account_inactive_user_returns_204_and_activates(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
    ) -> None:
        target_user = await make_user(
            test_db_session, role=UserRole.TEACHER, status=UserStatus.INACTIVE
        )
        auth_header = await make_auth_header(test_db_session, system_admin)

        response = await integration_client.patch(
            f"/admin/users/{target_user.id}/account/activate", headers=auth_header
        )

        await test_db_session.refresh(target_user)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert target_user.status == UserStatus.ACTIVE


class TestAuth:
    async def test_activate_user_account_without_token_returns_401(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
    ) -> None:
        target_user = await make_user(
            test_db_session, role=UserRole.TEACHER, status=UserStatus.INACTIVE
        )

        response = await integration_client.patch(
            f"/admin/users/{target_user.id}/account/activate"
        )

        await test_db_session.refresh(target_user)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["error_code"] == "INVALID_ACCESS_TOKEN"
        assert target_user.status == UserStatus.INACTIVE

    @pytest.mark.parametrize(
        "caller_role",
        [UserRole.DIRECTOR, UserRole.TEACHER, UserRole.STUDENT],
        ids=["director", "teacher", "student"],
    )
    async def test_activate_user_account_non_admin_returns_403(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        caller_role: UserRole,
    ) -> None:
        caller = await make_user(test_db_session, role=caller_role)
        target_user = await make_user(
            test_db_session, role=UserRole.TEACHER, status=UserStatus.INACTIVE
        )
        auth_header = await make_auth_header(test_db_session, caller)

        response = await integration_client.patch(
            f"/admin/users/{target_user.id}/account/activate", headers=auth_header
        )

        await test_db_session.refresh(target_user)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json()["error_code"] == "ACCESS_DENIED"
        assert target_user.status == UserStatus.INACTIVE


class TestValidation:
    @pytest.mark.parametrize(
        "invalid_user_id",
        ["0", "2147483648", "abc"],
        ids=["zero", "above_maximum", "non_integer"],
    )
    async def test_activate_user_account_invalid_user_id_returns_422(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
        invalid_user_id: str,
    ) -> None:
        auth_header = await make_auth_header(test_db_session, system_admin)

        response = await integration_client.patch(
            f"/admin/users/{invalid_user_id}/account/activate", headers=auth_header
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


class TestEligibleUsers:
    async def test_activate_user_account_unknown_user_id_returns_404(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
    ) -> None:
        auth_header = await make_auth_header(test_db_session, system_admin)

        response = await integration_client.patch(
            f"/admin/users/{UNKNOWN_USER_ID}/account/activate", headers=auth_header
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["error_code"] == "USER_NOT_FOUND"


class TestEligibleStatuses:
    @pytest.mark.parametrize(
        ("initial_status", "expected_error_code"),
        [
            (UserStatus.ACTIVE, "USER_ALREADY_ACTIVE"),
            (UserStatus.PENDING_ACTIVATION, "USER_PENDING_ACTIVATION"),
            (UserStatus.GRADUATED, "USER_GRADUATED"),
        ],
        ids=["already_active", "pending_activation", "graduated"],
    )
    async def test_activate_user_account_ineligible_status_returns_409(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
        initial_status: UserStatus,
        expected_error_code: str,
    ) -> None:
        target_user = await make_user(
            test_db_session, role=UserRole.STUDENT, status=initial_status
        )
        auth_header = await make_auth_header(test_db_session, system_admin)

        response = await integration_client.patch(
            f"/admin/users/{target_user.id}/account/activate", headers=auth_header
        )

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.json()["error_code"] == expected_error_code
