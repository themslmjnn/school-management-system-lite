import pytest
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.core.redis.cache_keys import UsersCacheKeys
from school_management_system_lite.users.models import User
from school_management_system_lite.users.services import (
    system_admin as user_service_admin,
)
from school_management_system_lite.users.utils.enums import UserStatus
from school_management_system_lite.users.utils.exceptions import (
    UserAlreadyActiveError,
    UserNotFoundError,
    UserPendingActivationError,
)
from tests.factories import make_system_admin, make_teacher


class TestSuccess:
    async def test_successful_user_account_activation(
        self,
        test_db_session: AsyncSession,
        redis_client: Redis,
        system_admin: User,
        mock_send_admin_account_activation_email,
        mock_users_delete_cache_system_admin,
    ) -> None:
        user = await make_teacher(test_db_session, status=UserStatus.INACTIVE)

        await user_service_admin.activate_user_account(
            test_db_session, redis_client, system_admin.id, user.id
        )

        await test_db_session.refresh(user)

        assert user.status == UserStatus.ACTIVE


class TestEligibleUsers:
    async def test_activating_system_admin_account_is_prevented(
        self, test_db_session: AsyncSession, redis_client: Redis, system_admin: User
    ) -> None:
        with pytest.raises(UserNotFoundError):
            await user_service_admin.activate_user_account(
                test_db_session,
                redis_client,
                actor_id=system_admin.id,
                user_id=system_admin.id,
            )

    async def test_system_admin_cannot_activate_another_system_admin_account(
        self, test_db_session: AsyncSession, redis_client: Redis, system_admin: User
    ) -> None:
        user = await make_system_admin(test_db_session)

        with pytest.raises(UserNotFoundError):
            await user_service_admin.activate_user_account(
                test_db_session,
                redis_client,
                system_admin.id,
                user.id,
            )

    async def test_raise_error_on_unknown_users(
        self, test_db_session: AsyncSession, redis_client: Redis, system_admin: User
    ) -> None:
        with pytest.raises(UserNotFoundError):
            await user_service_admin.activate_user_account(
                test_db_session,
                redis_client,
                system_admin.id,
                999999,
            )


class TestEligibleStatuses:
    async def test_raise_error_on_active_accounts(
        self, test_db_session: AsyncSession, redis_client: Redis, system_admin: User
    ) -> None:
        user = await make_teacher(test_db_session, status=UserStatus.ACTIVE)

        with pytest.raises(UserAlreadyActiveError):
            await user_service_admin.activate_user_account(
                test_db_session,
                redis_client,
                system_admin.id,
                user.id,
            )

    async def test_raise_error_on_pending_activation_accounts(
        self, test_db_session: AsyncSession, redis_client: Redis, system_admin: User
    ) -> None:
        user = await make_teacher(test_db_session, status=UserStatus.PENDING_ACTIVATION)

        with pytest.raises(UserPendingActivationError):
            await user_service_admin.activate_user_account(
                test_db_session,
                redis_client,
                system_admin.id,
                user.id,
            )


class TestEmailSending:
    async def test_account_activated_email_is_sent(
        self,
        test_db_session: AsyncSession,
        redis_client: Redis,
        system_admin: User,
        mock_send_admin_account_activation_email,
        mock_users_delete_cache_system_admin,
    ) -> None:
        user = await make_teacher(test_db_session, status=UserStatus.INACTIVE)

        await user_service_admin.activate_user_account(
            test_db_session,
            redis_client,
            system_admin.id,
            user.id,
        )

        mock_send_admin_account_activation_email.assert_called_once_with(
            to_email=user.email
        )


class TestCacheHandling:
    async def test_successful_activation_invalidates_caches(
        self,
        test_db_session: AsyncSession,
        redis_client: Redis,
        system_admin: User,
        mock_send_admin_account_activation_email,
        mock_users_delete_cache_system_admin,
    ) -> None:
        user = await make_teacher(test_db_session, status=UserStatus.INACTIVE)

        await user_service_admin.activate_user_account(
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
