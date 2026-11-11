import pytest
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.auth.repositories import (
    session as auth_session_repository,
)
from school_management_system_lite.core.enums import OrderBy
from school_management_system_lite.core.redis.cache_keys import UsersCacheKeys
from school_management_system_lite.emails.enums import EmailStatus, EmailType
from school_management_system_lite.emails.repository import EmailRepository
from school_management_system_lite.users.models import User
from school_management_system_lite.users.services import (
    system_admin as user_service_admin,
)
from school_management_system_lite.users.utils.enums import UserStatus
from school_management_system_lite.users.utils.exceptions import (
    UserAlreadyInactiveError,
    UserNotFoundError,
    UserPendingActivationError,
)
from tests.factories import make_system_admin, make_teacher


class TestSuccess:
    async def test_successful_user_account_deactivation(
        self,
        test_db_session: AsyncSession,
        redis_client: Redis,
        system_admin: User,
        mock_users_delete_cache_system_admin,
    ) -> None:
        user = await make_teacher(test_db_session)

        await user_service_admin.deactivate_user_account(
            test_db_session, redis_client, system_admin.id, user.id
        )

        await test_db_session.refresh(user)

        assert user.status == UserStatus.INACTIVE


class TestEligibleUsers:
    async def test_deactivating_system_admin_account_is_prevented(
        self, test_db_session: AsyncSession, redis_client: Redis, system_admin: User
    ) -> None:
        with pytest.raises(UserNotFoundError):
            await user_service_admin.deactivate_user_account(
                test_db_session,
                redis_client,
                actor_id=system_admin.id,
                user_id=system_admin.id,
            )

    async def test_system_admin_cannot_deactivate_another_system_admin_account(
        self, test_db_session: AsyncSession, redis_client: Redis, system_admin: User
    ) -> None:
        user = await make_system_admin(test_db_session)

        with pytest.raises(UserNotFoundError):
            await user_service_admin.deactivate_user_account(
                test_db_session,
                redis_client,
                system_admin.id,
                user.id,
            )

    async def test_raise_error_on_unknown_users(
        self, test_db_session: AsyncSession, redis_client: Redis, system_admin: User
    ) -> None:
        with pytest.raises(UserNotFoundError):
            await user_service_admin.deactivate_user_account(
                test_db_session,
                redis_client,
                system_admin.id,
                999999,
            )


class TestEligibleStatuses:
    async def test_raise_error_on_inactive_accounts(
        self, test_db_session: AsyncSession, redis_client: Redis, system_admin: User
    ) -> None:
        user = await make_teacher(test_db_session, status=UserStatus.INACTIVE)

        with pytest.raises(UserAlreadyInactiveError):
            await user_service_admin.deactivate_user_account(
                test_db_session,
                redis_client,
                system_admin.id,
                user.id,
            )

    async def test_raise_error_on_pending_activation_accounts_accounts(
        self, test_db_session: AsyncSession, redis_client: Redis, system_admin: User
    ) -> None:
        user = await make_teacher(test_db_session, status=UserStatus.PENDING_ACTIVATION)

        with pytest.raises(UserPendingActivationError):
            await user_service_admin.deactivate_user_account(
                test_db_session,
                redis_client,
                system_admin.id,
                user.id,
            )

    @pytest.mark.parametrize(
        "status",
        [
            UserStatus.ACTIVE,
            UserStatus.EXPELLED,
            UserStatus.GRADUATED,
            UserStatus.WITHDRAWN,
        ],
    )
    async def test_allow_deactivating_non_inactive_and_pending_activation_accounts(
        self,
        test_db_session: AsyncSession,
        redis_client: Redis,
        system_admin: User,
        status: UserStatus,
    ) -> None:
        user = await make_teacher(test_db_session, status=status)

        await user_service_admin.deactivate_user_account(
            test_db_session,
            redis_client,
            system_admin.id,
            user.id,
        )

        await test_db_session.refresh(user)

        assert user.status == UserStatus.INACTIVE


class TestEmailRow:
    async def test_email_row_is_added(
        self,
        test_db_session: AsyncSession,
        redis_client: Redis,
        system_admin: User,
    ) -> None:
        user = await make_teacher(test_db_session)

        await user_service_admin.deactivate_user_account(
            test_db_session,
            redis_client,
            system_admin.id,
            user.id,
        )

        email_rows = await EmailRepository.get_by_recipient_email(
            test_db_session, user.email, order_by=OrderBy.DESC
        )

        assert len(email_rows) == 1

        email_row = email_rows[0]

        assert email_row.recipient_email == user.email
        assert email_row.subject is not None
        assert email_row.html_body is not None
        assert email_row.email_type == EmailType.ADMIN_ACCOUNT_DEACTIVATION
        assert email_row.status == EmailStatus.PENDING
        assert email_row.scheduled_for is not None
        assert email_row.triggered_by == system_admin.id


class TestCacheHandling:
    async def test_successful_deactivation_invalidates_caches(
        self,
        test_db_session: AsyncSession,
        redis_client: Redis,
        system_admin: User,
        mock_users_delete_cache_system_admin,
    ) -> None:
        user = await make_teacher(test_db_session)

        await user_service_admin.deactivate_user_account(
            test_db_session,
            redis_client,
            system_admin.id,
            user.id,
        )

        mock_users_delete_cache_system_admin.assert_called_once_with(
            redis_client,
            UsersCacheKeys.detailed_response_key_admin(user.id),
            UsersCacheKeys.detailed_response_key_staff(user.id),
        )


class TestSessionInvalidating:
    async def test_successful_deactivation_invalidates_session(
        self,
        test_db_session: AsyncSession,
        redis_client: Redis,
        system_admin: User,
        mock_users_delete_cache_system_admin,
    ) -> None:
        user = await make_teacher(test_db_session)

        user_session_before = await auth_session_repository.get_by_user_id(
            test_db_session, user.id
        )
        access_token_version_before = user_session_before.access_token_version

        await user_service_admin.deactivate_user_account(
            test_db_session,
            redis_client,
            system_admin.id,
            user.id,
        )

        user_session_after = await auth_session_repository.get_by_user_id(
            test_db_session, user.id
        )

        assert (
            user_session_after.access_token_version == access_token_version_before + 1
        )
        assert user_session_after.refresh_token_hash is None
        assert user_session_after.refresh_token_expires_at is None
