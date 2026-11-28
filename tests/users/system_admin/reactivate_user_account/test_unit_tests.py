import asyncio
from unittest.mock import AsyncMock

import pytest
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.core.exceptions.handlers import AppException
from school_management_system_lite.core.redis.cache_keys import UsersCacheKeys
from school_management_system_lite.users.models.user import User
from school_management_system_lite.users.services import (
    system_admin as user_service_admin,
)
from school_management_system_lite.users.utils.enums import UserRole, UserStatus
from school_management_system_lite.users.utils.exceptions import (
    UserAlreadyActiveError,
    UserGraduatedError,
    UserNotFoundError,
    UserPendingActivationError,
)
from tests.factories import make_user

UNKNOWN_USER_ID = 999_999


class TestSuccess:
    @pytest.mark.parametrize(
        ("role", "initial_status"),
        [
            (UserRole.DIRECTOR, UserStatus.INACTIVE),
            (UserRole.TEACHER, UserStatus.INACTIVE),
            (UserRole.STUDENT, UserStatus.INACTIVE),
            (UserRole.STUDENT, UserStatus.WITHDRAWN),
            (UserRole.STUDENT, UserStatus.EXPELLED),
        ],
        ids=[
            "inactive_director",
            "inactive_teacher",
            "inactive_student",
            "withdrawn_student",
            "expelled_student",
        ],
    )
    async def test_reactivate_user_account_eligible_status_sets_user_active(
        self,
        test_db_session: AsyncSession,
        test_redis_client: Redis | None,
        test_resend_client: AsyncMock,
        system_admin: User,
        mock_send_admin_account_reactivation_email: AsyncMock,
        role: UserRole,
        initial_status: UserStatus,
    ) -> None:
        target_user = await make_user(test_db_session, role=role, status=initial_status)

        await user_service_admin.reactivate_user_account(
            test_db_session,
            test_redis_client,
            test_resend_client,
            system_admin.id,
            target_user.id,
        )

        await test_db_session.refresh(target_user)

        assert target_user.status == UserStatus.ACTIVE

    async def test_reactivate_user_account_without_redis_sets_user_active(
        self,
        test_db_session: AsyncSession,
        test_resend_client: AsyncMock,
        system_admin: User,
        mock_send_admin_account_reactivation_email: AsyncMock,
    ) -> None:
        target_user = await make_user(
            test_db_session, role=UserRole.TEACHER, status=UserStatus.INACTIVE
        )

        await user_service_admin.reactivate_user_account(
            test_db_session,
            None,
            test_resend_client,
            system_admin.id,
            target_user.id,
        )

        await test_db_session.refresh(target_user)

        assert target_user.status == UserStatus.ACTIVE


class TestEligibleUsers:
    async def test_reactivate_user_account_system_admin_target_raises_not_found(
        self,
        test_db_session: AsyncSession,
        test_redis_client: Redis | None,
        test_resend_client: AsyncMock,
        system_admin: User,
    ) -> None:
        target_admin = await make_user(
            test_db_session,
            role=UserRole.SYSTEM_ADMIN,
            status=UserStatus.INACTIVE,
        )

        with pytest.raises(UserNotFoundError):
            await user_service_admin.reactivate_user_account(
                test_db_session,
                test_redis_client,
                test_resend_client,
                system_admin.id,
                target_admin.id,
            )

        await test_db_session.refresh(target_admin)

        assert target_admin.status == UserStatus.INACTIVE

    async def test_reactivate_user_account_unknown_user_id_raises_not_found(
        self,
        test_db_session: AsyncSession,
        test_redis_client: Redis | None,
        test_resend_client: AsyncMock,
        system_admin: User,
    ) -> None:
        with pytest.raises(UserNotFoundError):
            await user_service_admin.reactivate_user_account(
                test_db_session,
                test_redis_client,
                test_resend_client,
                system_admin.id,
                UNKNOWN_USER_ID,
            )


class TestEligibleStatuses:
    @pytest.mark.parametrize(
        ("initial_status", "expected_error"),
        [
            (UserStatus.ACTIVE, UserAlreadyActiveError),
            (UserStatus.PENDING_ACTIVATION, UserPendingActivationError),
            (UserStatus.GRADUATED, UserGraduatedError),
        ],
        ids=["already_active", "pending_activation", "graduated"],
    )
    async def test_reactivate_user_account_ineligible_status_raises_without_side_effects(
        self,
        test_db_session: AsyncSession,
        test_redis_client: Redis | None,
        test_resend_client: AsyncMock,
        system_admin: User,
        mock_send_admin_account_reactivation_email: AsyncMock,
        mock_users_delete_cache_system_admin: AsyncMock,
        initial_status: UserStatus,
        expected_error: type[AppException],
    ) -> None:
        target_user = await make_user(
            test_db_session, role=UserRole.STUDENT, status=initial_status
        )

        with pytest.raises(expected_error):
            await user_service_admin.reactivate_user_account(
                test_db_session,
                test_redis_client,
                test_resend_client,
                system_admin.id,
                target_user.id,
            )

        await test_db_session.refresh(target_user)

        assert target_user.status == initial_status

        mock_users_delete_cache_system_admin.assert_not_called()
        mock_send_admin_account_reactivation_email.assert_not_called()


class TestEmailSending:
    async def test_reactivate_user_account_eligible_user_sends_activation_email(
        self,
        test_db_session: AsyncSession,
        test_redis_client: Redis | None,
        test_resend_client: AsyncMock,
        system_admin: User,
        mock_send_admin_account_reactivation_email: AsyncMock,
    ) -> None:
        target_user = await make_user(
            test_db_session, role=UserRole.TEACHER, status=UserStatus.INACTIVE
        )

        await user_service_admin.reactivate_user_account(
            test_db_session,
            test_redis_client,
            test_resend_client,
            system_admin.id,
            target_user.id,
        )

        # Yield to the event loop so the background email task runs.
        await asyncio.sleep(0)

        mock_send_admin_account_reactivation_email.assert_awaited_once_with(
            test_resend_client, target_user.email
        )

    async def test_reactivate_user_account_email_failure_keeps_user_active(
        self,
        test_db_session: AsyncSession,
        test_redis_client: Redis | None,
        test_resend_client: AsyncMock,
        system_admin: User,
        mock_send_admin_account_reactivation_email: AsyncMock,
    ) -> None:
        mock_send_admin_account_reactivation_email.side_effect = RuntimeError(
            "Email provider unavailable"
        )
        target_user = await make_user(
            test_db_session, role=UserRole.TEACHER, status=UserStatus.INACTIVE
        )

        await user_service_admin.reactivate_user_account(
            test_db_session,
            test_redis_client,
            test_resend_client,
            system_admin.id,
            target_user.id,
        )

        # Yield to the event loop so the background email task runs and fails.
        await asyncio.sleep(0)
        await test_db_session.refresh(target_user)

        mock_send_admin_account_reactivation_email.assert_awaited_once()

        assert target_user.status == UserStatus.ACTIVE


class TestCacheHandling:
    async def test_reactivate_user_account_cached_user_removes_admin_and_staff_keys(
        self,
        test_db_session: AsyncSession,
        test_redis_client: Redis | None,
        test_resend_client: AsyncMock,
        system_admin: User,
        mock_send_admin_account_reactivation_email: AsyncMock,
    ) -> None:
        if test_redis_client is None:
            pytest.skip("Redis is not available")

        target_user = await make_user(
            test_db_session, role=UserRole.TEACHER, status=UserStatus.INACTIVE
        )
        cache_keys = (
            UsersCacheKeys.detailed_response_key_admin(target_user.id),
            UsersCacheKeys.detailed_response_key_staff(target_user.id),
        )
        for cache_key in cache_keys:
            await test_redis_client.set(cache_key, "{}")

        await user_service_admin.reactivate_user_account(
            test_db_session,
            test_redis_client,
            test_resend_client,
            system_admin.id,
            target_user.id,
        )

        assert await test_redis_client.exists(*cache_keys) == 0
