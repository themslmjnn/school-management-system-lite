from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.auth.repositories import (
    session as auth_session_repository,
)
from school_management_system_lite.core.exceptions.handlers import AppException
from school_management_system_lite.core.security import verify_password
from school_management_system_lite.users.schemas import shared as user_schemas_shared
from school_management_system_lite.users.services import shared as user_service_shared
from school_management_system_lite.users.utils import exceptions as user_exceptions
from tests.factories import make_user

CURRENT_PASSWORD = "TestPassword_123!"
NEW_PASSWORD = "NewPassword_456!"


def make_payload() -> user_schemas_shared.UpdateMyPassword:
    return user_schemas_shared.UpdateMyPassword(
        current_password=CURRENT_PASSWORD, new_password=NEW_PASSWORD
    )


class TestUpdateMyPasswordSuccess:
    async def test_update_my_password_valid_request_replaces_password(
        self,
        test_db_session: AsyncSession,
        test_resend_client: AsyncMock,
        mock_send_password_changed_notification: AsyncMock,
    ) -> None:
        user = await make_user(test_db_session, password=CURRENT_PASSWORD)

        await test_db_session.commit()

        await user_service_shared.update_my_password(
            test_db_session, test_resend_client, user.id, make_payload()
        )

        # Discards anything the service did not commit
        await test_db_session.rollback()
        await test_db_session.refresh(user)

        assert await verify_password(NEW_PASSWORD, user.password_hash)
        assert not await verify_password(CURRENT_PASSWORD, user.password_hash)

    async def test_update_my_password_valid_request_revokes_session_tokens(
        self,
        test_db_session: AsyncSession,
        test_resend_client: AsyncMock,
        mock_send_password_changed_notification: AsyncMock,
    ) -> None:
        user = await make_user(test_db_session, password=CURRENT_PASSWORD)
        user_session = await auth_session_repository.get_by_user_id(
            test_db_session, user.id
        )

        assert user_session is not None

        user_session.refresh_token_hash = "old-refresh-token-hash"
        user_session.refresh_token_expires_at = datetime.now(UTC) + timedelta(days=1)

        await test_db_session.commit()

        initial_token_version = user_session.access_token_version

        await user_service_shared.update_my_password(
            test_db_session, test_resend_client, user.id, make_payload()
        )

        await test_db_session.rollback()
        await test_db_session.refresh(user_session)

        assert user_session.access_token_version == initial_token_version + 1
        assert user_session.refresh_token_hash is None
        assert user_session.refresh_token_expires_at is None

    async def test_update_my_password_valid_request_sends_one_notification(
        self,
        test_db_session: AsyncSession,
        test_resend_client: AsyncMock,
        mock_send_password_changed_notification: AsyncMock,
    ) -> None:
        user = await make_user(test_db_session, password=CURRENT_PASSWORD)

        await user_service_shared.update_my_password(
            test_db_session, test_resend_client, user.id, make_payload()
        )

        mock_send_password_changed_notification.assert_called_once_with(
            test_resend_client, user.email
        )

    async def test_update_my_password_valid_request_leaves_other_users_unchanged(
        self,
        test_db_session: AsyncSession,
        test_resend_client: AsyncMock,
        mock_send_password_changed_notification: AsyncMock,
    ) -> None:
        user = await make_user(test_db_session, password=CURRENT_PASSWORD)
        other_user = await make_user(test_db_session, password=CURRENT_PASSWORD)
        other_session = await auth_session_repository.get_by_user_id(
            test_db_session, other_user.id
        )

        assert other_session is not None

        await test_db_session.commit()

        other_password_hash = other_user.password_hash
        other_token_version = other_session.access_token_version

        await user_service_shared.update_my_password(
            test_db_session, test_resend_client, user.id, make_payload()
        )

        await test_db_session.refresh(other_user)
        await test_db_session.refresh(other_session)

        assert other_user.password_hash == other_password_hash
        assert other_session.access_token_version == other_token_version


class TestUpdateMyPasswordRejected:
    async def test_update_my_password_unknown_user_raises_user_not_found(
        self,
        test_db_session: AsyncSession,
        test_resend_client: AsyncMock,
    ) -> None:
        unknown_user_id = 999_999

        with pytest.raises(user_exceptions.UserNotFoundError):
            await user_service_shared.update_my_password(
                test_db_session, test_resend_client, unknown_user_id, make_payload()
            )

    async def test_update_my_password_user_without_password_raises_invalid_password(
        self,
        test_db_session: AsyncSession,
        test_resend_client: AsyncMock,
    ) -> None:
        user = await make_user(test_db_session, password=None)

        with pytest.raises(user_exceptions.InvalidPasswordError):
            await user_service_shared.update_my_password(
                test_db_session, test_resend_client, user.id, make_payload()
            )

    @pytest.mark.parametrize(
        ("current_password", "new_password", "expected_error"),
        [
            pytest.param(
                "WrongPassword_123!",
                NEW_PASSWORD,
                user_exceptions.IncorrectCurrentPasswordError,
                id="wrong-current-password",
            ),
            pytest.param(
                CURRENT_PASSWORD,
                CURRENT_PASSWORD,
                user_exceptions.SamePasswordError,
                id="same-password",
            ),
        ],
    )
    async def test_update_my_password_rejected_request_changes_nothing(
        self,
        test_db_session: AsyncSession,
        test_resend_client: AsyncMock,
        mock_send_password_changed_notification: AsyncMock,
        current_password: str,
        new_password: str,
        expected_error: type[AppException],
    ) -> None:
        user = await make_user(test_db_session, password=CURRENT_PASSWORD)
        user_session = await auth_session_repository.get_by_user_id(
            test_db_session, user.id
        )

        assert user_session is not None

        await test_db_session.commit()

        initial_password_hash = user.password_hash
        initial_token_version = user_session.access_token_version

        # model_construct skips validation, so identical passwords reach the service
        payload = user_schemas_shared.UpdateMyPassword.model_construct(
            current_password=current_password, new_password=new_password
        )

        with pytest.raises(expected_error):
            await user_service_shared.update_my_password(
                test_db_session, test_resend_client, user.id, payload
            )

        await test_db_session.refresh(user)
        await test_db_session.refresh(user_session)

        assert user.password_hash == initial_password_hash
        assert user_session.access_token_version == initial_token_version

        mock_send_password_changed_notification.assert_not_called()
