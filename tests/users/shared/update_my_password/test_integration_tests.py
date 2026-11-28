from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.auth.repositories import (
    session as auth_session_repository,
)
from school_management_system_lite.core.security import verify_password
from school_management_system_lite.users.utils.enums import UserRole, UserStatus
from tests.factories import make_user
from tests.helpers import make_auth_header

pytestmark = pytest.mark.usefixtures("test_resend_client")

ENDPOINT = "/users/me/password"
CURRENT_PASSWORD = "TestPassword_123!"
NEW_PASSWORD = "NewPassword_456!"
VALID_PAYLOAD = {
    "current_password": CURRENT_PASSWORD,
    "new_password": NEW_PASSWORD,
}


class TestUpdateMyPasswordEndpointSuccess:
    @pytest.mark.parametrize(
        "role",
        [
            pytest.param(UserRole.SYSTEM_ADMIN, id="system-admin"),
            pytest.param(UserRole.DIRECTOR, id="director"),
            pytest.param(UserRole.TEACHER, id="teacher"),
            pytest.param(UserRole.STUDENT, id="student"),
        ],
    )
    async def test_update_my_password_any_role_returns_204_and_saves_password(
        self,
        integration_client: AsyncClient,
        test_db_session: AsyncSession,
        mock_send_password_changed_notification: AsyncMock,
        role: UserRole,
    ) -> None:
        user = await make_user(test_db_session, role=role, password=CURRENT_PASSWORD)
        headers = await make_auth_header(test_db_session, user)

        await test_db_session.commit()

        response = await integration_client.patch(
            ENDPOINT, json=VALID_PAYLOAD, headers=headers
        )

        assert response.status_code == 204
        assert response.content == b""

        # Discards anything the app did not commit
        await test_db_session.rollback()
        await test_db_session.refresh(user)

        assert await verify_password(NEW_PASSWORD, user.password_hash)

    @pytest.mark.parametrize(
        "user_status",
        [
            pytest.param(UserStatus.GRADUATED, id="graduated"),
            pytest.param(UserStatus.EXPELLED, id="expelled"),
            pytest.param(UserStatus.WITHDRAWN, id="withdrawn"),
        ],
    )
    async def test_update_my_password_non_active_student_returns_204(
        self,
        integration_client: AsyncClient,
        test_db_session: AsyncSession,
        mock_send_password_changed_notification: AsyncMock,
        user_status: UserStatus,
    ) -> None:
        student = await make_user(
            test_db_session,
            role=UserRole.STUDENT,
            status=user_status,
            password=CURRENT_PASSWORD,
        )
        headers = await make_auth_header(test_db_session, student)

        response = await integration_client.patch(
            ENDPOINT, json=VALID_PAYLOAD, headers=headers
        )

        assert response.status_code == 204

    async def test_update_my_password_reused_token_after_change_returns_401(
        self,
        integration_client: AsyncClient,
        test_db_session: AsyncSession,
        mock_send_password_changed_notification: AsyncMock,
    ) -> None:
        user = await make_user(test_db_session, password=CURRENT_PASSWORD)
        headers = await make_auth_header(test_db_session, user)

        first_response = await integration_client.patch(
            ENDPOINT, json=VALID_PAYLOAD, headers=headers
        )
        second_response = await integration_client.patch(
            ENDPOINT,
            json={
                "current_password": NEW_PASSWORD,
                "new_password": "AnotherPassword_789!",
            },
            headers=headers,
        )

        assert first_response.status_code == 204
        assert second_response.status_code == 401
        assert second_response.json()["error_code"] == "INVALID_ACCESS_TOKEN"

    async def test_update_my_password_valid_request_notifies_user_with_app_client(
        self,
        integration_client: AsyncClient,
        test_db_session: AsyncSession,
        test_resend_client: AsyncMock,
        mock_send_password_changed_notification: AsyncMock,
    ) -> None:
        user = await make_user(test_db_session, password=CURRENT_PASSWORD)
        headers = await make_auth_header(test_db_session, user)

        response = await integration_client.patch(
            ENDPOINT, json=VALID_PAYLOAD, headers=headers
        )

        assert response.status_code == 204

        mock_send_password_changed_notification.assert_called_once_with(
            test_resend_client, user.email
        )

    async def test_update_my_password_failing_notification_still_saves_password(
        self,
        integration_client: AsyncClient,
        test_db_session: AsyncSession,
        mock_send_password_changed_notification: AsyncMock,
    ) -> None:
        mock_send_password_changed_notification.side_effect = RuntimeError(
            "Email provider unavailable"
        )

        user = await make_user(test_db_session, password=CURRENT_PASSWORD)
        headers = await make_auth_header(test_db_session, user)

        await test_db_session.commit()

        response = await integration_client.patch(
            ENDPOINT, json=VALID_PAYLOAD, headers=headers
        )

        assert response.status_code == 204

        await test_db_session.rollback()
        await test_db_session.refresh(user)

        assert await verify_password(NEW_PASSWORD, user.password_hash)


class TestUpdateMyPasswordEndpointAuthentication:
    @pytest.mark.parametrize(
        "headers",
        [
            pytest.param({}, id="no-header"),
            pytest.param(
                {"Authorization": "Bearer not-a-valid-token"}, id="malformed-token"
            ),
        ],
    )
    async def test_update_my_password_unauthenticated_request_returns_401(
        self,
        integration_client: AsyncClient,
        headers: dict[str, str],
    ) -> None:
        response = await integration_client.patch(
            ENDPOINT, json=VALID_PAYLOAD, headers=headers
        )

        assert response.status_code == 401
        assert response.json()["error_code"] == "INVALID_ACCESS_TOKEN"

    async def test_update_my_password_inactive_user_returns_401(
        self,
        integration_client: AsyncClient,
        test_db_session: AsyncSession,
    ) -> None:
        user = await make_user(
            test_db_session, status=UserStatus.INACTIVE, password=CURRENT_PASSWORD
        )
        headers = await make_auth_header(test_db_session, user)

        await test_db_session.commit()

        initial_password_hash = user.password_hash

        response = await integration_client.patch(
            ENDPOINT, json=VALID_PAYLOAD, headers=headers
        )

        assert response.status_code == 401
        assert response.json()["error_code"] == "ACCOUNT_INACTIVE"

        await test_db_session.refresh(user)

        assert user.password_hash == initial_password_hash


class TestUpdateMyPasswordEndpointRejected:
    async def test_update_my_password_wrong_current_password_returns_400(
        self,
        integration_client: AsyncClient,
        test_db_session: AsyncSession,
        mock_send_password_changed_notification: AsyncMock,
    ) -> None:
        user = await make_user(test_db_session, password=CURRENT_PASSWORD)
        user_session = await auth_session_repository.get_by_user_id(
            test_db_session, user.id
        )

        assert user_session is not None

        headers = await make_auth_header(test_db_session, user)

        await test_db_session.commit()

        initial_password_hash = user.password_hash
        initial_token_version = user_session.access_token_version

        response = await integration_client.patch(
            ENDPOINT,
            json={**VALID_PAYLOAD, "current_password": "WrongPassword_123!"},
            headers=headers,
        )

        assert response.status_code == 400
        assert response.json()["error_code"] == "INCORRECT_CURRENT_PASSWORD"

        await test_db_session.refresh(user)
        await test_db_session.refresh(user_session)

        assert user.password_hash == initial_password_hash
        assert user_session.access_token_version == initial_token_version

        mock_send_password_changed_notification.assert_not_called()
