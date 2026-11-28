from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.auth.models.password_reset import UserPasswordReset
from school_management_system_lite.auth.repositories import (
    password_reset as auth_password_reset_repository,
)
from school_management_system_lite.core.enums import OrderBy
from school_management_system_lite.core.security import generate_token
from school_management_system_lite.emails import repository as email_repository
from school_management_system_lite.emails.enums import EmailStatus, EmailType
from school_management_system_lite.emails.models import Email
from school_management_system_lite.users.models.user import User
from school_management_system_lite.users.utils.enums import UserRole, UserStatus
from tests.factories import make_user
from tests.helpers import make_auth_header


async def get_queued_reset_emails(
    test_db_session: AsyncSession, recipient_email: str
) -> Sequence[Email]:
    return await email_repository.get_by_recipient_email(
        test_db_session,
        recipient_email,
        email_type=frozenset({EmailType.ADMIN_PASSWORD_RESET}),
        status=EmailStatus.PENDING,
        order_by=OrderBy.DESC,
    )


async def assert_no_reset_data_saved(
    test_db_session: AsyncSession, target_user: User
) -> None:
    password_reset = await auth_password_reset_repository.get_by_user_id(
        test_db_session, target_user.id
    )
    queued_emails = await get_queued_reset_emails(test_db_session, target_user.email)

    assert password_reset is None
    assert len(queued_emails) == 0


class TestSuccess:
    async def test_request_password_reset_valid_target_returns_accepted_and_saves_data(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
    ) -> None:
        target_user = await make_user(test_db_session, role=UserRole.TEACHER)
        admin_headers = await make_auth_header(test_db_session, system_admin)

        response = await integration_client.post(
            f"/admin/users/{target_user.id}/password-reset",
            headers=admin_headers,
        )

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.json() is None

        password_reset = await auth_password_reset_repository.get_by_user_id(
            test_db_session, target_user.id
        )
        queued_emails = await get_queued_reset_emails(
            test_db_session, target_user.email
        )

        assert password_reset is not None
        assert len(queued_emails) == 1
        assert queued_emails[0].triggered_by == system_admin.id


class TestAuth:
    @pytest.mark.parametrize(
        "request_headers",
        [{}, {"Authorization": "Bearer not-a-valid-token"}],
        ids=["missing-token", "malformed-token"],
    )
    async def test_request_password_reset_invalid_authentication_returns_unauthorized(
        self,
        integration_client: AsyncClient,
        request_headers: dict[str, str],
    ) -> None:
        response = await integration_client.post(
            "/admin/users/999999/password-reset",
            headers=request_headers,
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize(
        "actor_role",
        [UserRole.DIRECTOR, UserRole.TEACHER, UserRole.STUDENT],
        ids=["director", "teacher", "student"],
    )
    async def test_request_password_reset_non_admin_returns_forbidden(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        actor_role: UserRole,
    ) -> None:
        actor = await make_user(test_db_session, role=actor_role)
        target_user = await make_user(test_db_session, role=UserRole.TEACHER)
        actor_headers = await make_auth_header(test_db_session, actor)

        response = await integration_client.post(
            f"/admin/users/{target_user.id}/password-reset",
            headers=actor_headers,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        await assert_no_reset_data_saved(test_db_session, target_user)


class TestEligibleUsers:
    @pytest.mark.parametrize(
        "unknown_user_id",
        [999999, 2147483647],
        ids=["unknown-id", "upper-limit-id"],
    )
    async def test_request_password_reset_unknown_user_returns_not_found(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
        unknown_user_id: int,
    ) -> None:
        admin_headers = await make_auth_header(test_db_session, system_admin)

        response = await integration_client.post(
            f"/admin/users/{unknown_user_id}/password-reset",
            headers=admin_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["error_code"] == "USER_NOT_FOUND"

    async def test_request_password_reset_system_admin_target_returns_not_found(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
    ) -> None:
        target_admin = await make_user(test_db_session, role=UserRole.SYSTEM_ADMIN)
        admin_headers = await make_auth_header(test_db_session, system_admin)

        response = await integration_client.post(
            f"/admin/users/{target_admin.id}/password-reset",
            headers=admin_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["error_code"] == "USER_NOT_FOUND"
        await assert_no_reset_data_saved(test_db_session, target_admin)


class TestEligibleStatuses:
    async def test_request_password_reset_pending_activation_user_returns_conflict(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
    ) -> None:
        pending_user = await make_user(
            test_db_session,
            role=UserRole.TEACHER,
            status=UserStatus.PENDING_ACTIVATION,
        )
        admin_headers = await make_auth_header(test_db_session, system_admin)

        response = await integration_client.post(
            f"/admin/users/{pending_user.id}/password-reset",
            headers=admin_headers,
        )

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.json()["error_code"] == "USER_PENDING_ACTIVATION"
        await assert_no_reset_data_saved(test_db_session, pending_user)


class TestExistingRequests:
    async def test_request_password_reset_existing_request_returns_accepted_and_replaces_token(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
    ) -> None:
        target_user = await make_user(test_db_session, role=UserRole.TEACHER)
        _, old_token_hash = generate_token()
        test_db_session.add(
            UserPasswordReset(
                user_id=target_user.id,
                password_reset_token_hash=old_token_hash,
                password_reset_token_expires_at=datetime.now(UTC)
                + timedelta(minutes=5),
            )
        )
        await test_db_session.flush()
        admin_headers = await make_auth_header(test_db_session, system_admin)

        response = await integration_client.post(
            f"/admin/users/{target_user.id}/password-reset",
            headers=admin_headers,
        )

        assert response.status_code == status.HTTP_202_ACCEPTED

        password_reset = await auth_password_reset_repository.get_by_user_id(
            test_db_session, target_user.id
        )

        assert password_reset is not None
        assert password_reset.password_reset_token_hash != old_token_hash


class TestValidation:
    @pytest.mark.parametrize(
        "invalid_user_id",
        [0, -1, 2147483648, "abc"],
        ids=["zero", "negative", "above-upper-limit", "non-integer"],
    )
    async def test_request_password_reset_invalid_user_id_returns_unprocessable(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
        invalid_user_id: int | str,
    ) -> None:
        admin_headers = await make_auth_header(test_db_session, system_admin)

        response = await integration_client.post(
            f"/admin/users/{invalid_user_id}/password-reset",
            headers=admin_headers,
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
