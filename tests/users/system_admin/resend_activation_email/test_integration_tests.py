import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.emails import repository as email_repository
from school_management_system_lite.emails.enums import EmailStatus, EmailType
from school_management_system_lite.users.models.user import User
from school_management_system_lite.users.utils.enums import UserRole, UserStatus
from tests.factories import make_user
from tests.helpers import make_auth_header

UNKNOWN_USER_ID = 999999
MAX_USER_ID = 2_147_483_647


class TestSuccess:
    async def test_resend_activation_email_as_system_admin_returns_202_and_queues_email(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
    ) -> None:
        target_user = await make_user(
            test_db_session,
            role=UserRole.TEACHER,
            status=UserStatus.PENDING_ACTIVATION,
        )
        auth_header = await make_auth_header(test_db_session, system_admin)

        response = await integration_client.post(
            f"/admin/users/{target_user.id}/activation-email",
            headers=auth_header,
        )

        assert response.status_code == status.HTTP_202_ACCEPTED

        queued_emails = await email_repository.get_by_recipient_email(
            test_db_session,
            target_user.email,
            email_type=frozenset({EmailType.ACCOUNT_ACTIVATION}),
            status=EmailStatus.PENDING,
        )

        assert len(queued_emails) == 1
        assert queued_emails[0].recipient_email == target_user.email
        assert queued_emails[0].triggered_by == system_admin.id


class TestAuth:
    async def test_resend_activation_email_without_token_returns_401(
        self,
        integration_client: AsyncClient,
    ) -> None:
        response = await integration_client.post(
            f"/admin/users/{UNKNOWN_USER_ID}/activation-email",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize(
        "role",
        [UserRole.DIRECTOR, UserRole.TEACHER, UserRole.STUDENT],
        ids=["director", "teacher", "student"],
    )
    async def test_resend_activation_email_as_non_admin_returns_403(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        role: UserRole,
    ) -> None:
        non_admin_user = await make_user(test_db_session, role=role)
        auth_header = await make_auth_header(test_db_session, non_admin_user)

        response = await integration_client.post(
            f"/admin/users/{UNKNOWN_USER_ID}/activation-email",
            headers=auth_header,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestValidation:
    @pytest.mark.parametrize(
        "invalid_user_id",
        [0, MAX_USER_ID + 1],
        ids=["below_minimum", "above_maximum"],
    )
    async def test_resend_activation_email_with_out_of_range_user_id_returns_422(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
        invalid_user_id: int,
    ) -> None:
        auth_header = await make_auth_header(test_db_session, system_admin)

        response = await integration_client.post(
            f"/admin/users/{invalid_user_id}/activation-email",
            headers=auth_header,
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


class TestEligibleUsers:
    @pytest.mark.parametrize(
        "unknown_user_id",
        [UNKNOWN_USER_ID, MAX_USER_ID],
        ids=["unused_id", "largest_valid_id"],
    )
    async def test_resend_activation_email_for_unknown_user_returns_404(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
        unknown_user_id: int,
    ) -> None:
        auth_header = await make_auth_header(test_db_session, system_admin)

        response = await integration_client.post(
            f"/admin/users/{unknown_user_id}/activation-email",
            headers=auth_header,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["error_code"] == "USER_NOT_FOUND"


class TestEligibleStatuses:
    async def test_resend_activation_email_for_active_user_returns_409(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
    ) -> None:
        target_user = await make_user(
            test_db_session,
            role=UserRole.TEACHER,
            status=UserStatus.ACTIVE,
        )
        auth_header = await make_auth_header(test_db_session, system_admin)

        response = await integration_client.post(
            f"/admin/users/{target_user.id}/activation-email",
            headers=auth_header,
        )

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.json()["error_code"] == "RESEND_ACTIVATION_EMAIL_DENIED"
