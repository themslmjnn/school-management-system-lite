import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.core.enums import OrderBy
from school_management_system_lite.emails import repository as email_repository
from school_management_system_lite.users.models.user import User
from school_management_system_lite.users.utils.enums import UserRole, UserStatus
from tests.conftest import make_auth_header
from tests.factories import make_user

pytestmark = pytest.mark.usefixtures("test_redis_client")

UNKNOWN_USER_ID = 999999


def _deactivate_url(user_id: int) -> str:
    return f"/admin/users/{user_id}/account/deactivate"


class TestSuccess:
    @pytest.mark.parametrize(
        "role",
        [UserRole.DIRECTOR, UserRole.TEACHER, UserRole.STUDENT],
        ids=["director", "teacher", "student"],
    )
    async def test_deactivate_route_eligible_user_returns_204_and_persists_changes(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
        role: UserRole,
    ) -> None:
        target_user = await make_user(test_db_session, role=role)
        admin_auth_header = await make_auth_header(test_db_session, system_admin)

        response = await integration_client.patch(
            _deactivate_url(target_user.id), headers=admin_auth_header
        )

        await test_db_session.refresh(target_user)

        queued_emails = await email_repository.get_by_recipient_email(
            test_db_session, target_user.email, order_by=OrderBy.DESC
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert target_user.status == UserStatus.INACTIVE
        assert len(queued_emails) == 1
        assert queued_emails[0].recipient_email == target_user.email
        assert queued_emails[0].triggered_by == system_admin.id

    async def test_deactivate_route_old_token_of_deactivated_user_returns_401(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
        teacher: User,
    ) -> None:
        admin_auth_header = await make_auth_header(test_db_session, system_admin)
        target_auth_header = await make_auth_header(test_db_session, teacher)

        deactivation_response = await integration_client.patch(
            _deactivate_url(teacher.id), headers=admin_auth_header
        )

        assert deactivation_response.status_code == status.HTTP_204_NO_CONTENT

        profile_response = await integration_client.get(
            "/users/me", headers=target_auth_header
        )

        assert profile_response.status_code == status.HTTP_401_UNAUTHORIZED
        assert profile_response.json()["error_code"] == "INVALID_ACCESS_TOKEN"


class TestAuth:
    async def test_deactivate_route_missing_token_returns_401(
        self, integration_client: AsyncClient
    ) -> None:
        response = await integration_client.patch(_deactivate_url(UNKNOWN_USER_ID))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["error_code"] == "INVALID_ACCESS_TOKEN"

    @pytest.mark.parametrize(
        "role",
        [UserRole.DIRECTOR, UserRole.TEACHER, UserRole.STUDENT],
        ids=["director", "teacher", "student"],
    )
    async def test_deactivate_route_non_admin_caller_returns_403(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        role: UserRole,
    ) -> None:
        caller = await make_user(test_db_session, role=role)
        target_user = await make_user(test_db_session, role=UserRole.TEACHER)
        caller_auth_header = await make_auth_header(test_db_session, caller)

        response = await integration_client.patch(
            _deactivate_url(target_user.id), headers=caller_auth_header
        )

        await test_db_session.refresh(target_user)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json()["error_code"] == "ACCESS_DENIED"
        assert target_user.status == UserStatus.ACTIVE


class TestPathValidation:
    @pytest.mark.parametrize(
        "invalid_user_id",
        [0, 2147483648],
        ids=["below-minimum", "above-maximum"],
    )
    async def test_deactivate_route_out_of_range_user_id_returns_422(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
        invalid_user_id: int,
    ) -> None:
        admin_auth_header = await make_auth_header(test_db_session, system_admin)

        response = await integration_client.patch(
            _deactivate_url(invalid_user_id), headers=admin_auth_header
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


class TestEligibleUsers:
    async def test_deactivate_route_own_admin_account_returns_404(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
    ) -> None:
        admin_auth_header = await make_auth_header(test_db_session, system_admin)

        response = await integration_client.patch(
            _deactivate_url(system_admin.id), headers=admin_auth_header
        )

        await test_db_session.refresh(system_admin)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["error_code"] == "USER_NOT_FOUND"
        assert system_admin.status == UserStatus.ACTIVE

    async def test_deactivate_route_unknown_user_returns_404(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
    ) -> None:
        admin_auth_header = await make_auth_header(test_db_session, system_admin)

        response = await integration_client.patch(
            _deactivate_url(UNKNOWN_USER_ID), headers=admin_auth_header
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["error_code"] == "USER_NOT_FOUND"


class TestEligibleStatuses:
    @pytest.mark.parametrize(
        ("target_status", "expected_error_code"),
        [
            pytest.param(UserStatus.INACTIVE, "USER_ALREADY_INACTIVE", id="inactive"),
            pytest.param(
                UserStatus.PENDING_ACTIVATION,
                "USER_PENDING_ACTIVATION",
                id="pending-activation",
            ),
        ],
    )
    async def test_deactivate_route_ineligible_status_returns_409(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
        target_status: UserStatus,
        expected_error_code: str,
    ) -> None:
        target_user = await make_user(
            test_db_session, role=UserRole.TEACHER, status=target_status
        )
        admin_auth_header = await make_auth_header(test_db_session, system_admin)

        response = await integration_client.patch(
            _deactivate_url(target_user.id), headers=admin_auth_header
        )

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.json()["error_code"] == expected_error_code
