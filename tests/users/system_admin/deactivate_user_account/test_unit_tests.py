from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from pytest_mock import MockerFixture
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.auth.repositories import (
    session as auth_session_repository,
)
from school_management_system_lite.core.enums import OrderBy
from school_management_system_lite.core.redis.cache_keys import UsersCacheKeys
from school_management_system_lite.emails import repository as email_repository
from school_management_system_lite.emails.enums import EmailStatus, EmailType
from school_management_system_lite.users.models.user import User
from school_management_system_lite.users.services import (
    system_admin as user_service_admin,
)
from school_management_system_lite.users.utils.enums import UserRole, UserStatus
from school_management_system_lite.users.utils.exceptions import (
    UserAlreadyInactiveError,
    UserNotFoundError,
    UserPendingActivationError,
)
from tests.factories import make_user

UNKNOWN_USER_ID = 999999


def _make_failing_redis_client() -> AsyncMock:
    redis_client = AsyncMock(spec=Redis)
    redis_client.delete = AsyncMock(side_effect=RedisError("Redis is down"))

    return redis_client


class TestSuccess:
    @pytest.mark.parametrize(
        ("role", "target_status"),
        [
            pytest.param(UserRole.DIRECTOR, UserStatus.ACTIVE, id="active-director"),
            pytest.param(UserRole.TEACHER, UserStatus.ACTIVE, id="active-teacher"),
            pytest.param(UserRole.STUDENT, UserStatus.ACTIVE, id="active-student"),
            pytest.param(UserRole.STUDENT, UserStatus.EXPELLED, id="expelled-student"),
            pytest.param(
                UserRole.STUDENT, UserStatus.GRADUATED, id="graduated-student"
            ),
            pytest.param(
                UserRole.STUDENT, UserStatus.WITHDRAWN, id="withdrawn-student"
            ),
        ],
    )
    async def test_deactivate_user_account_eligible_user_sets_status_inactive(
        self,
        test_db_session: AsyncSession,
        system_admin: User,
        mock_users_delete_cache_system_admin: AsyncMock,
        role: UserRole,
        target_status: UserStatus,
    ) -> None:
        target_user = await make_user(test_db_session, role=role, status=target_status)

        await user_service_admin.deactivate_user_account(
            test_db_session, None, system_admin.id, target_user.id
        )

        await test_db_session.refresh(target_user)

        assert target_user.status == UserStatus.INACTIVE

    async def test_deactivate_user_account_without_session_deactivates_and_queues_email(
        self,
        test_db_session: AsyncSession,
        system_admin: User,
        mock_users_delete_cache_system_admin: AsyncMock,
    ) -> None:
        target_user = await make_user(test_db_session, role=UserRole.TEACHER)
        target_session = await auth_session_repository.get_by_user_id(
            test_db_session, target_user.id
        )

        assert target_session is not None

        await test_db_session.delete(target_session)
        await test_db_session.flush()

        await user_service_admin.deactivate_user_account(
            test_db_session, None, system_admin.id, target_user.id
        )

        await test_db_session.refresh(target_user)

        queued_emails = await email_repository.get_by_recipient_email(
            test_db_session, target_user.email, order_by=OrderBy.DESC
        )

        assert target_user.status == UserStatus.INACTIVE
        assert len(queued_emails) == 1
        assert queued_emails[0].email_type == EmailType.ADMIN_ACCOUNT_DEACTIVATION


class TestEligibleUsers:
    async def test_deactivate_user_account_own_admin_account_raises_not_found(
        self,
        test_db_session: AsyncSession,
        system_admin: User,
    ) -> None:
        with pytest.raises(UserNotFoundError):
            await user_service_admin.deactivate_user_account(
                test_db_session, None, system_admin.id, system_admin.id
            )

        await test_db_session.refresh(system_admin)

        queued_emails = await email_repository.get_by_recipient_email(
            test_db_session, system_admin.email, order_by=OrderBy.DESC
        )

        assert system_admin.status == UserStatus.ACTIVE
        assert len(queued_emails) == 0

    async def test_deactivate_user_account_other_system_admin_raises_not_found(
        self,
        test_db_session: AsyncSession,
        system_admin: User,
    ) -> None:
        target_admin = await make_user(test_db_session, role=UserRole.SYSTEM_ADMIN)

        with pytest.raises(UserNotFoundError):
            await user_service_admin.deactivate_user_account(
                test_db_session, None, system_admin.id, target_admin.id
            )

        await test_db_session.refresh(target_admin)

        queued_emails = await email_repository.get_by_recipient_email(
            test_db_session, target_admin.email, order_by=OrderBy.DESC
        )

        assert target_admin.status == UserStatus.ACTIVE
        assert len(queued_emails) == 0

    async def test_deactivate_user_account_unknown_user_raises_not_found(
        self,
        test_db_session: AsyncSession,
        system_admin: User,
        mock_users_delete_cache_system_admin: AsyncMock,
    ) -> None:
        with pytest.raises(UserNotFoundError):
            await user_service_admin.deactivate_user_account(
                test_db_session, None, system_admin.id, UNKNOWN_USER_ID
            )

        mock_users_delete_cache_system_admin.assert_not_awaited()


class TestEligibleStatuses:
    @pytest.mark.parametrize(
        ("target_status", "expected_exception"),
        [
            pytest.param(UserStatus.INACTIVE, UserAlreadyInactiveError, id="inactive"),
            pytest.param(
                UserStatus.PENDING_ACTIVATION,
                UserPendingActivationError,
                id="pending-activation",
            ),
        ],
    )
    async def test_deactivate_user_account_ineligible_status_raises_and_changes_nothing(
        self,
        test_db_session: AsyncSession,
        system_admin: User,
        mock_users_delete_cache_system_admin: AsyncMock,
        target_status: UserStatus,
        expected_exception: type[Exception],
    ) -> None:
        target_user = await make_user(
            test_db_session, role=UserRole.TEACHER, status=target_status
        )
        target_session = await auth_session_repository.get_by_user_id(
            test_db_session, target_user.id
        )

        assert target_session is not None

        token_version_before = target_session.access_token_version

        with pytest.raises(expected_exception):
            await user_service_admin.deactivate_user_account(
                test_db_session, None, system_admin.id, target_user.id
            )

        await test_db_session.refresh(target_user)
        await test_db_session.refresh(target_session)

        queued_emails = await email_repository.get_by_recipient_email(
            test_db_session, target_user.email, order_by=OrderBy.DESC
        )

        assert target_user.status == target_status
        assert target_session.access_token_version == token_version_before
        assert len(queued_emails) == 0

        mock_users_delete_cache_system_admin.assert_not_awaited()


class TestEmailRow:
    async def test_deactivate_user_account_active_user_queues_deactivation_email(
        self,
        test_db_session: AsyncSession,
        system_admin: User,
        mock_users_delete_cache_system_admin: AsyncMock,
    ) -> None:
        target_user = await make_user(test_db_session, role=UserRole.TEACHER)
        expected_subject, expected_html_body = (
            user_service_admin.build_admin_account_deactivation_email()
        )

        await user_service_admin.deactivate_user_account(
            test_db_session, None, system_admin.id, target_user.id
        )

        queued_emails = await email_repository.get_by_recipient_email(
            test_db_session, target_user.email, order_by=OrderBy.DESC
        )

        assert len(queued_emails) == 1

        queued_email = queued_emails[0]

        assert queued_email.recipient_email == target_user.email
        assert queued_email.subject == expected_subject
        assert queued_email.html_body == expected_html_body
        assert queued_email.email_type == EmailType.ADMIN_ACCOUNT_DEACTIVATION
        assert queued_email.status == EmailStatus.PENDING
        assert queued_email.triggered_by == system_admin.id


class TestSessionInvalidation:
    async def test_deactivate_user_account_active_user_revokes_session(
        self,
        test_db_session: AsyncSession,
        system_admin: User,
        mock_users_delete_cache_system_admin: AsyncMock,
    ) -> None:
        target_user = await make_user(test_db_session, role=UserRole.TEACHER)
        target_session = await auth_session_repository.get_by_user_id(
            test_db_session, target_user.id
        )

        assert target_session is not None

        target_session.refresh_token_hash = "seeded-refresh-token-hash"
        target_session.refresh_token_expires_at = datetime.now(UTC) + timedelta(days=1)

        await test_db_session.commit()

        token_version_before = target_session.access_token_version

        await user_service_admin.deactivate_user_account(
            test_db_session, None, system_admin.id, target_user.id
        )

        await test_db_session.refresh(target_session)

        assert target_session.access_token_version == token_version_before + 1
        assert target_session.refresh_token_hash is None
        assert target_session.refresh_token_expires_at is None


class TestCacheHandling:
    async def test_deactivate_user_account_active_user_invalidates_admin_and_staff_cache(
        self,
        test_db_session: AsyncSession,
        system_admin: User,
        mock_users_delete_cache_system_admin: AsyncMock,
    ) -> None:
        target_user = await make_user(test_db_session, role=UserRole.TEACHER)

        await user_service_admin.deactivate_user_account(
            test_db_session, None, system_admin.id, target_user.id
        )

        mock_users_delete_cache_system_admin.assert_awaited_once_with(
            None,
            UsersCacheKeys.detailed_response_key_admin(target_user.id),
            UsersCacheKeys.detailed_response_key_staff(target_user.id),
        )

    async def test_deactivate_user_account_failed_commit_skips_cache_invalidation(
        self,
        test_db_session: AsyncSession,
        system_admin: User,
        mock_users_delete_cache_system_admin: AsyncMock,
        mocker: MockerFixture,
    ) -> None:
        target_user = await make_user(test_db_session, role=UserRole.TEACHER)
        mocker.patch.object(
            test_db_session,
            "commit",
            new_callable=AsyncMock,
            side_effect=SQLAlchemyError("Commit failed"),
        )

        with pytest.raises(SQLAlchemyError):
            await user_service_admin.deactivate_user_account(
                test_db_session, None, system_admin.id, target_user.id
            )

        mock_users_delete_cache_system_admin.assert_not_awaited()

    @pytest.mark.parametrize(
        "redis_client",
        [None, _make_failing_redis_client()],
        ids=["redis-absent", "redis-failing"],
    )
    async def test_deactivate_user_account_unavailable_redis_persists_status(
        self,
        test_db_session: AsyncSession,
        system_admin: User,
        redis_client: Redis | None,
    ) -> None:
        target_user = await make_user(test_db_session, role=UserRole.TEACHER)

        await user_service_admin.deactivate_user_account(
            test_db_session, redis_client, system_admin.id, target_user.id
        )

        await test_db_session.refresh(target_user)

        assert target_user.status == UserStatus.INACTIVE
