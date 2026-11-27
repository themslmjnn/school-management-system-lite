import itertools
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from redis.asyncio import Redis
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.auth.repositories import (
    session as auth_session_repository,
)
from school_management_system_lite.core.enums import OrderBy
from school_management_system_lite.core.redis.cache_keys import UsersCacheKeys
from school_management_system_lite.emails import repository as email_repository
from school_management_system_lite.emails.enums import EmailStatus, EmailType
from school_management_system_lite.users.models.user import User
from school_management_system_lite.users.schemas.system_admin import (
    UpdateUserEmailAdmin,
)
from school_management_system_lite.users.services import (
    system_admin as user_service_admin,
)
from school_management_system_lite.users.utils.enums import UserRole, UserStatus
from school_management_system_lite.users.utils.exceptions import (
    EmailAlreadyTakenError,
    UserNotFoundError,
)
from tests.factories import make_user

NEW_EMAIL = "updated_email@gmail.com"
UNKNOWN_USER_ID = 999999

NON_ADMIN_ROLES = (UserRole.DIRECTOR, UserRole.TEACHER, UserRole.STUDENT)

EXISTING_AND_TARGET_ROLE_PAIRS = [
    pytest.param(
        existing_role,
        target_role,
        id=f"{existing_role.name.lower()}_exists-{target_role.name.lower()}_updated",
    )
    for existing_role, target_role in itertools.product(NON_ADMIN_ROLES, repeat=2)
]

UpdateEmail = Callable[..., Awaitable[None]]


@pytest.fixture
def update_email(test_db_session: AsyncSession, system_admin: User) -> UpdateEmail:
    system_admin_id = system_admin.id

    async def _update_email(
        user_id: int,
        new_email: str = NEW_EMAIL,
        *,
        actor_id: int = system_admin_id,
        redis_client: Redis | None = None,
    ) -> None:
        await user_service_admin.update_user_email(
            test_db_session,
            redis_client,
            actor_id,
            user_id,
            UpdateUserEmailAdmin(email=new_email),
        )

    return _update_email


class TestSuccess:
    @pytest.mark.parametrize(
        "target_role",
        NON_ADMIN_ROLES,
        ids=[role.name.lower() for role in NON_ADMIN_ROLES],
    )
    async def test_update_email_for_non_admin_user_saves_new_email(
        self,
        test_db_session: AsyncSession,
        update_email: UpdateEmail,
        target_role: UserRole,
    ) -> None:
        target_user = await make_user(test_db_session, role=target_role)

        await update_email(target_user.id)

        await test_db_session.refresh(target_user)

        assert target_user.email == NEW_EMAIL

    @pytest.mark.parametrize(
        "user_status",
        list(UserStatus),
        ids=[user_status.name.lower() for user_status in UserStatus],
    )
    async def test_update_email_for_user_of_any_status_saves_new_email(
        self,
        test_db_session: AsyncSession,
        update_email: UpdateEmail,
        user_status: UserStatus,
    ) -> None:
        target_user = await make_user(test_db_session, status=user_status)

        await update_email(target_user.id)

        await test_db_session.refresh(target_user)

        assert target_user.email == NEW_EMAIL

    async def test_update_email_for_user_without_session_saves_new_email(
        self,
        test_db_session: AsyncSession,
        update_email: UpdateEmail,
    ) -> None:
        target_user = await make_user(test_db_session, role=UserRole.TEACHER)
        user_session = await auth_session_repository.get_by_user_id(
            test_db_session, target_user.id
        )

        assert user_session is not None

        await test_db_session.delete(user_session)
        await test_db_session.commit()

        await update_email(target_user.id)

        await test_db_session.refresh(target_user)

        assert target_user.email == NEW_EMAIL

    async def test_update_email_with_current_email_changes_nothing(
        self,
        test_db_session: AsyncSession,
        update_email: UpdateEmail,
        mock_users_delete_cache_system_admin: AsyncMock,
    ) -> None:
        target_user = await make_user(test_db_session, role=UserRole.TEACHER)
        user_session = await auth_session_repository.get_by_user_id(
            test_db_session, target_user.id
        )

        assert user_session is not None

        original_email = target_user.email
        original_token_version = user_session.access_token_version

        await update_email(target_user.id, original_email)

        queued_emails = await email_repository.get_by_recipient_email(
            test_db_session, original_email, order_by=OrderBy.DESC
        )

        await test_db_session.refresh(target_user)
        await test_db_session.refresh(user_session)

        assert target_user.email == original_email
        assert user_session.access_token_version == original_token_version
        assert len(queued_emails) == 0

        mock_users_delete_cache_system_admin.assert_not_awaited()


class TestEligibleUsers:
    async def test_update_email_for_system_admin_raises_user_not_found_error(
        self,
        test_db_session: AsyncSession,
        update_email: UpdateEmail,
    ) -> None:
        other_admin = await make_user(test_db_session, role=UserRole.SYSTEM_ADMIN)

        with pytest.raises(UserNotFoundError):
            await update_email(other_admin.id)

    async def test_update_email_for_unknown_user_raises_user_not_found_error(
        self,
        update_email: UpdateEmail,
    ) -> None:
        with pytest.raises(UserNotFoundError):
            await update_email(UNKNOWN_USER_ID)


class TestEmailRows:
    async def test_update_email_queues_override_email_to_old_and_new_address(
        self,
        test_db_session: AsyncSession,
        system_admin: User,
        update_email: UpdateEmail,
    ) -> None:
        target_user = await make_user(test_db_session, role=UserRole.TEACHER)
        old_email = target_user.email

        await update_email(target_user.id)

        for recipient_email in (old_email, NEW_EMAIL):
            queued_emails = await email_repository.get_by_recipient_email(
                test_db_session, recipient_email, order_by=OrderBy.DESC
            )

            assert len(queued_emails) == 1

            queued_email = queued_emails[0]

            assert queued_email.recipient_email == recipient_email
            assert queued_email.email_type == EmailType.ADMIN_USER_EMAIL_OVERRIDE
            assert queued_email.status == EmailStatus.PENDING
            assert queued_email.triggered_by == system_admin.id
            assert NEW_EMAIL in queued_email.html_body


class TestSessionInvalidation:
    async def test_update_email_for_user_with_session_invalidates_tokens(
        self,
        test_db_session: AsyncSession,
        update_email: UpdateEmail,
    ) -> None:
        target_user = await make_user(test_db_session, role=UserRole.TEACHER)
        user_session = await auth_session_repository.get_by_user_id(
            test_db_session, target_user.id
        )

        assert user_session is not None

        user_session.refresh_token_hash = "old-refresh-token-hash"
        user_session.refresh_token_expires_at = datetime.now(UTC) + timedelta(days=1)

        await test_db_session.commit()

        original_token_version = user_session.access_token_version

        await update_email(target_user.id)

        await test_db_session.refresh(user_session)

        assert user_session.access_token_version == original_token_version + 1
        assert user_session.refresh_token_hash is None
        assert user_session.refresh_token_expires_at is None


class TestCacheHandling:
    async def test_update_email_with_new_email_invalidates_user_caches(
        self,
        test_db_session: AsyncSession,
        test_redis_client: Redis | None,
        update_email: UpdateEmail,
        mock_users_delete_cache_system_admin: AsyncMock,
    ) -> None:
        target_user = await make_user(test_db_session, role=UserRole.TEACHER)

        await update_email(target_user.id, redis_client=test_redis_client)

        mock_users_delete_cache_system_admin.assert_awaited_once_with(
            test_redis_client,
            UsersCacheKeys.detailed_response_key_admin(target_user.id),
            UsersCacheKeys.detailed_response_key_self(target_user.id),
        )


class TestDBConstraints:
    @pytest.mark.parametrize(
        ["existing_role", "target_role"], EXISTING_AND_TARGET_ROLE_PAIRS
    )
    async def test_update_email_with_taken_email_raises_email_taken_error(
        self,
        test_db_session: AsyncSession,
        update_email: UpdateEmail,
        mock_users_delete_cache_system_admin: AsyncMock,
        existing_role: UserRole,
        target_role: UserRole,
    ) -> None:
        existing_user = await make_user(test_db_session, role=existing_role)
        target_user = await make_user(test_db_session, role=target_role)
        user_session = await auth_session_repository.get_by_user_id(
            test_db_session, target_user.id
        )

        assert user_session is not None

        await test_db_session.commit()

        taken_email = existing_user.email
        original_email = target_user.email
        original_token_version = user_session.access_token_version

        with pytest.raises(EmailAlreadyTakenError):
            await update_email(target_user.id, taken_email)

        await test_db_session.refresh(target_user)
        await test_db_session.refresh(user_session)

        assert target_user.email == original_email
        assert user_session.access_token_version == original_token_version

        for recipient_email in (original_email, taken_email):
            queued_emails = await email_repository.get_by_recipient_email(
                test_db_session, recipient_email, order_by=OrderBy.DESC
            )

            assert len(queued_emails) == 0

        mock_users_delete_cache_system_admin.assert_not_awaited()

    async def test_update_email_with_unknown_actor_reraises_integrity_error(
        self,
        test_db_session: AsyncSession,
        update_email: UpdateEmail,
    ) -> None:
        target_user = await make_user(test_db_session, role=UserRole.TEACHER)
        await test_db_session.commit()

        with pytest.raises(IntegrityError, match="fk_emails_triggered_by_users"):
            await update_email(target_user.id, actor_id=UNKNOWN_USER_ID)
