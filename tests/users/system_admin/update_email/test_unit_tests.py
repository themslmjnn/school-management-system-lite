import pytest
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.auth.repositories.session import (
    UserSessionRepository,
)
from school_management_system_lite.core.redis.cache_keys import UsersCacheKeys
from school_management_system_lite.emails.enums import EmailStatus, EmailType
from school_management_system_lite.emails.repository import EmailRepository
from school_management_system_lite.users.models.user import User
from school_management_system_lite.users.schemas.system_admin import UpdateEmailAdmin
from school_management_system_lite.users.services.system_admin import UserServiceAdmin
from school_management_system_lite.users.utils.exceptions import (
    EmailAlreadyTakenError,
    UserNotFoundError,
)
from school_management_system_lite.utils.enums import OrderBy, UserRole
from tests.factories import (
    make_director,
    make_student,
    make_system_admin,
    make_teacher,
    make_user,
)


class TestSuccess:
    async def test_successful_update(
        self,
        test_db_session: AsyncSession,
        redis_client: Redis,
        system_admin: User,
        mock_users_delete_cache_system_admin,
    ) -> None:
        user = await make_teacher(test_db_session)

        await UserServiceAdmin.update_email(
            test_db_session,
            redis_client,
            system_admin.id,
            user.id,
            UpdateEmailAdmin(email="updated_email@gmail.com"),
        )

        await test_db_session.refresh(user)

        assert user.email == "updated_email@gmail.com"

    async def test_nothing_changes_if_payload_is_empty(
        self,
        test_db_session: AsyncSession,
        redis_client: Redis,
        system_admin: User,
        mock_users_delete_cache_system_admin,
    ) -> None:
        user = await make_teacher(test_db_session)

        email_before = user.email

        await UserServiceAdmin.update_email(
            test_db_session, redis_client, system_admin.id, user.id, UpdateEmailAdmin()
        )

        await test_db_session.refresh(user)

        assert user.email == email_before

    async def test_nothing_changes_if_current_values_are_provided(
        self,
        test_db_session: AsyncSession,
        redis_client: Redis,
        system_admin: User,
        mock_users_delete_cache_system_admin,
    ) -> None:
        user = await make_teacher(test_db_session)

        email_before = user.email

        await UserServiceAdmin.update_email(
            test_db_session,
            redis_client,
            system_admin.id,
            user.id,
            UpdateEmailAdmin(email=user.email),
        )

        await test_db_session.refresh(user)

        assert user.email == email_before


class TestEligibleUsers:
    async def test_updating_system_admin_is_prevented(
        self, test_db_session: AsyncSession, redis_client: Redis, system_admin: User
    ) -> None:
        with pytest.raises(UserNotFoundError):
            await UserServiceAdmin.update_email(
                test_db_session,
                redis_client,
                actor_id=system_admin.id,
                user_id=system_admin.id,
                payload=UpdateEmailAdmin(),
            )

    async def test_system_admin_cannot_update_another_system_admin(
        self, test_db_session: AsyncSession, redis_client: Redis, system_admin: User
    ) -> None:
        user = await make_system_admin(test_db_session)

        with pytest.raises(UserNotFoundError):
            await UserServiceAdmin.update_email(
                test_db_session,
                redis_client,
                system_admin.id,
                user.id,
                payload=UpdateEmailAdmin(),
            )

    async def test_raise_error_on_unknown_users(
        self, test_db_session: AsyncSession, redis_client: Redis, system_admin: User
    ) -> None:
        with pytest.raises(UserNotFoundError):
            await UserServiceAdmin.update_email(
                test_db_session,
                redis_client,
                system_admin.id,
                999999,
                payload=UpdateEmailAdmin(),
            )


class TestEmailRow:
    async def test_email_row_is_added(
        self,
        test_db_session: AsyncSession,
        redis_client: Redis,
        system_admin: User,
        mock_users_delete_cache_system_admin,
    ) -> None:
        user = await make_teacher(test_db_session)

        await UserServiceAdmin.update_email(
            test_db_session,
            redis_client,
            system_admin.id,
            user.id,
            UpdateEmailAdmin(email="updated_email@gmail.com"),
        )

        email_rows = await EmailRepository.get_by_recipient_email(
            test_db_session, user.email, order_by=OrderBy.DESC
        )

        assert len(email_rows) == 1

        email_row = email_rows[0]

        assert email_row.recipient_email == user.email
        assert email_row.subject is not None
        assert email_row.html_body is not None
        assert email_row.email_type == EmailType.ADMIN_CREDENTIALS_OVERRIDE
        assert email_row.status == EmailStatus.PENDING
        assert email_row.scheduled_for is not None
        assert email_row.triggered_by == system_admin.id


class TestDBConstraints:
    @pytest.mark.parametrize(
        ["role", "email"],
        [
            (UserRole.DIRECTOR, "teacher_email@gmail.com"),
            (UserRole.DIRECTOR, "student_email@gmail.com"),
            (UserRole.TEACHER, "director_email@gmail.com"),
            (UserRole.TEACHER, "student_email@gmail.com"),
            (UserRole.STUDENT, "director_email@gmail.com"),
            (UserRole.STUDENT, "teacher_email@gmail.com"),
        ],
    )
    async def test_duplicate_email_is_caught(
        self,
        test_db_session: AsyncSession,
        redis_client: Redis,
        system_admin: User,
        role: UserRole,
        email: str,
    ) -> None:
        user = await make_user(test_db_session, role=role)

        await make_director(test_db_session, email="director_email@gmail.com")
        await make_teacher(test_db_session, email="teacher_email@gmail.com")
        await make_student(test_db_session, email="student_email@gmail.com")

        with pytest.raises(EmailAlreadyTakenError):
            await UserServiceAdmin.update_email(
                test_db_session,
                redis_client,
                system_admin.id,
                user.id,
                UpdateEmailAdmin(email=email),
            )


class TestCacheHandling:
    async def test_successful_updating_invalidates_caches(
        self,
        test_db_session: AsyncSession,
        redis_client: Redis,
        system_admin: User,
        mock_users_delete_cache_system_admin,
    ) -> None:
        user = await make_teacher(test_db_session)

        await UserServiceAdmin.update_email(
            test_db_session,
            redis_client,
            system_admin.id,
            user.id,
            UpdateEmailAdmin(email="updated_email@gmail.com"),
        )

        mock_users_delete_cache_system_admin.assert_called_once_with(
            redis_client,
            UsersCacheKeys.detailed_response_key_admin(user.id),
            UsersCacheKeys.detailed_response_key_staff(user.id),
            UsersCacheKeys.detailed_response_key_self(user.id),
        )


class TestSessionInvalidating:
    async def test_successful_updating_invalidates_session(
        self,
        test_db_session: AsyncSession,
        redis_client: Redis,
        system_admin: User,
        mock_users_delete_cache_system_admin,
    ) -> None:
        user = await make_teacher(test_db_session)

        user_session_before = await UserSessionRepository.get_by_user_id(
            test_db_session, user.id
        )
        access_token_version_before = user_session_before.access_token_version

        await UserServiceAdmin.update_email(
            test_db_session,
            redis_client,
            system_admin.id,
            user.id,
            UpdateEmailAdmin(email="updated_email@gmail.com"),
        )

        user_session_after = await UserSessionRepository.get_by_user_id(
            test_db_session, user.id
        )

        assert (
            user_session_after.access_token_version == access_token_version_before + 1
        )
        assert user_session_after.refresh_token_hash is None
        assert user_session_after.refresh_token_expires_at is None
