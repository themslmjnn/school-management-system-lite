from datetime import UTC, datetime, timedelta

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.auth.models.password_reset import UserPasswordReset
from school_management_system_lite.core.config import get_settings
from school_management_system_lite.core.security import generate_token
from school_management_system_lite.emails.enums import EmailStatus, EmailType
from school_management_system_lite.emails.models import Email
from school_management_system_lite.users.models import User
from school_management_system_lite.users.utils.enums import UserRole, UserStatus
from tests.conftest import make_auth_header
from tests.factories import make_system_admin, make_teacher, make_user

ENDPOINT = "/admin/users/{}/password-reset"


class TestSuccess:
    async def test_successfully_request_password_reset(
        self,
        test_db_session: AsyncSession,
        client: AsyncClient,
        system_admin: User,
    ) -> None:
        user = await make_teacher(test_db_session)

        header = await make_auth_header(test_db_session, system_admin)

        response = await client.patch(
            f"/admin/users/{user.id}/password-reset",
            headers=header,
        )

        assert response.status_code == status.HTTP_202_ACCEPTED


class TestAuth:
    async def test_unauthenticated_requests_raise_401(
        self, client: AsyncClient
    ) -> None:
        response = await client.patch("/admin/users/999999/password-reset")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize(
        "role",
        [UserRole.DIRECTOR, UserRole.TEACHER, UserRole.STUDENT],
    )
    async def test_raises_403_on_non_admins(
        self,
        test_db_session: AsyncSession,
        client: AsyncClient,
        role: UserRole,
    ) -> None:
        user = await make_user(test_db_session, role=role)

        header = await make_auth_header(test_db_session, user)

        response = await client.patch(
            "/admin/users/999999/password-reset",
            headers=header,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestEligibleUsers:
    async def test_requesting_password_reset_for_system_admin_account_is_prevented(
        self,
        test_db_session: AsyncSession,
        client: AsyncClient,
        system_admin: User,
    ) -> None:
        header = await make_auth_header(test_db_session, system_admin)

        response = await client.patch(
            f"/admin/users/{system_admin.id}/password-reset",
            headers=header,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_system_admin_cannot_request_password_reset_for_another_system_admin(
        self,
        test_db_session: AsyncSession,
        client: AsyncClient,
        system_admin: User,
    ) -> None:
        user = await make_system_admin(test_db_session)

        header = await make_auth_header(test_db_session, system_admin)

        response = await client.patch(
            f"/admin/users/{user.id}/password-reset",
            headers=header,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_raise_error_on_unknown_users(
        self,
        test_db_session: AsyncSession,
        client: AsyncClient,
        system_admin: User,
    ) -> None:
        header = await make_auth_header(test_db_session, system_admin)

        response = await client.patch(
            "/admin/users/999999/password-reset",
            headers=header,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestEligibleStatuses:
    async def test_raise_error_on_pending_activation_accounts(
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
            f"/admin/users/{user.id}/password-reset",
            headers=header,
        )

        assert response.status_code == status.HTTP_409_CONFLICT


class TestPendingRequests:
    async def test_raise_error_on_duplicate_password_reset_request(
        self,
        test_db_session: AsyncSession,
        client: AsyncClient,
        system_admin: User,
    ) -> None:
        user = await make_teacher(test_db_session)

        _, password_reset_token_hash = generate_token()

        password_reset_token_expires_at = datetime.now(UTC) + timedelta(
            minutes=get_settings().PASSWORD_RESET_TOKEN_EXPIRES_MINUTES
        )

        test_db_session.add(
            UserPasswordReset(
                user_id=user.id,
                password_reset_token_hash=password_reset_token_hash,
                password_reset_token_expires_at=password_reset_token_expires_at,
            )
        )
        await test_db_session.flush()

        header = await make_auth_header(test_db_session, system_admin)

        response = await client.patch(
            f"/admin/users/{user.id}/password-reset",
            headers=header,
        )

        assert response.status_code == status.HTTP_409_CONFLICT

    async def test_raise_error_on_pending_password_reset_email(
        self,
        test_db_session: AsyncSession,
        client: AsyncClient,
        system_admin: User,
    ) -> None:
        user = await make_teacher(test_db_session)

        test_db_session.add(
            Email(
                recipient_email=user.email,
                subject="Password reset",
                html_body="<p>Password reset</p>",
                email_type=EmailType.ADMIN_PASSWORD_RESET,
                status=EmailStatus.PENDING,
                triggered_by=system_admin.id,
            )
        )
        await test_db_session.flush()

        header = await make_auth_header(test_db_session, system_admin)

        response = await client.patch(
            f"/admin/users/{user.id}/password-reset",
            headers=header,
        )

        assert response.status_code == status.HTTP_409_CONFLICT


class TestExpiredRequests:
    async def test_successfully_request_password_reset_for_expired_request(
        self,
        test_db_session: AsyncSession,
        client: AsyncClient,
        system_admin: User,
    ) -> None:
        user = await make_teacher(test_db_session)

        _, password_reset_token_hash = generate_token()

        password_reset_token_expires_at = datetime.now(UTC) - timedelta(minutes=1)

        test_db_session.add(
            UserPasswordReset(
                user_id=user.id,
                password_reset_token_hash=password_reset_token_hash,
                password_reset_token_expires_at=password_reset_token_expires_at,
            )
        )
        await test_db_session.flush()

        header = await make_auth_header(test_db_session, system_admin)

        response = await client.patch(
            f"/admin/users/{user.id}/password-reset",
            headers=header,
        )

        assert response.status_code == status.HTTP_202_ACCEPTED
