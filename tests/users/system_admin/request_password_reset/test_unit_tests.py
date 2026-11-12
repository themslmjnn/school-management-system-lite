from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.auth.models.password_reset import UserPasswordReset
from school_management_system_lite.auth.repositories import (
    password_reset as auth_password_reset_repository,
)
from school_management_system_lite.core.config import get_settings
from school_management_system_lite.core.enums import OrderBy
from school_management_system_lite.core.security import generate_token
from school_management_system_lite.emails import repository as email_repository
from school_management_system_lite.emails.enums import EmailStatus, EmailType
from school_management_system_lite.emails.models import Email
from school_management_system_lite.users.models import User
from school_management_system_lite.users.services import (
    system_admin as user_service_admin,
)
from school_management_system_lite.users.utils.enums import UserStatus
from school_management_system_lite.users.utils.exceptions import (
    PasswordResetAlreadyRequestedError,
    UserNotFoundError,
    UserPendingActivationError,
)
from tests.factories import make_student, make_system_admin, make_teacher


class TestSuccess:
    async def test_successfully_request_password_reset(
        self, test_db_session: AsyncSession, system_admin: User
    ) -> None:
        user = await make_student(test_db_session)

        await user_service_admin.request_password_reset(
            test_db_session, system_admin.id, user.id
        )

        password_reset = await auth_password_reset_repository.get_by_user_id(
            test_db_session, user.id
        )

        assert password_reset is not None
        assert password_reset.user_id == user.id
        assert password_reset.password_reset_token_hash is not None
        assert password_reset.password_reset_token_expires_at is not None

        email = await email_repository.get_by_recipient_email(
            test_db_session,
            user.email,
            email_type=frozenset({EmailType.ADMIN_PASSWORD_RESET}),
            status=EmailStatus.PENDING,
            order_by=OrderBy.DESC,
        )

        assert len(email) == 1

        email = email[0]

        assert email.recipient_email == user.email
        assert email.subject is not None
        assert email.html_body is not None
        assert email.status == EmailStatus.PENDING
        assert email.email_type == EmailType.ADMIN_PASSWORD_RESET
        assert email.triggered_by == system_admin.id

    async def test_replace_expired_password_reset_request(
        self, test_db_session: AsyncSession, system_admin: User
    ) -> None:
        user = await make_teacher(test_db_session)

        _, old_token_hash = generate_token()

        expired_password_reset = UserPasswordReset(
            user_id=user.id,
            password_reset_token_hash=old_token_hash,
            password_reset_token_expires_at=datetime.now(UTC) - timedelta(minutes=1),
        )

        test_db_session.add(expired_password_reset)
        await test_db_session.flush()

        await user_service_admin.request_password_reset(
            test_db_session,
            system_admin.id,
            user.id,
        )

        password_reset = await auth_password_reset_repository.get_by_user_id(
            test_db_session, user.id
        )

        assert password_reset is not None
        assert password_reset.user_id == user.id
        assert password_reset.password_reset_token_hash != old_token_hash
        assert password_reset.password_reset_token_expires_at is not None

        email = await email_repository.get_by_recipient_email(
            test_db_session,
            user.email,
            email_type=frozenset({EmailType.ADMIN_PASSWORD_RESET}),
            status=EmailStatus.PENDING,
            order_by=OrderBy.DESC,
        )

        assert len(email) == 1


class TestEligibleUsers:
    async def test_create_request_for_system_admin_account_is_prevented(
        self, test_db_session: AsyncSession, system_admin: User
    ) -> None:
        with pytest.raises(UserNotFoundError):
            await user_service_admin.request_password_reset(
                test_db_session,
                actor_id=system_admin.id,
                user_id=system_admin.id,
            )

    async def test_system_admin_cannot_create_request_for_another_system_admin_account(
        self, test_db_session: AsyncSession, system_admin: User
    ) -> None:
        user = await make_system_admin(test_db_session)

        with pytest.raises(UserNotFoundError):
            await user_service_admin.request_password_reset(
                test_db_session,
                system_admin.id,
                user.id,
            )

    async def test_raise_error_on_unknown_users(
        self, test_db_session: AsyncSession, system_admin: User
    ) -> None:
        with pytest.raises(UserNotFoundError):
            await user_service_admin.request_password_reset(
                test_db_session,
                system_admin.id,
                999999,
            )


class TestEligibleStatuses:
    async def test_raise_error_on_pending_activation_accounts(
        self, test_db_session: AsyncSession, system_admin: User
    ) -> None:
        user = await make_teacher(test_db_session, status=UserStatus.PENDING_ACTIVATION)

        with pytest.raises(UserPendingActivationError):
            await user_service_admin.request_password_reset(
                test_db_session,
                system_admin.id,
                user.id,
            )


class TestPendingRequests:
    async def test_raise_error_on_duplicate_requests(
        self, test_db_session: AsyncSession, system_admin: User
    ):
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

        with pytest.raises(PasswordResetAlreadyRequestedError):
            await user_service_admin.request_password_reset(
                test_db_session,
                system_admin.id,
                user.id,
            )

    async def test_raise_error_on_pending_password_reset_email(
        self, test_db_session: AsyncSession, system_admin: User
    ) -> None:
        user = await make_teacher(test_db_session)

        test_db_session.add(
            Email(
                recipient_email=user.email,
                subject="Password reset",
                html_body="<p>Password reset</p>",
                email_type=EmailType.ADMIN_PASSWORD_RESET,
                triggered_by=system_admin.id,
            )
        )
        await test_db_session.flush()

        with pytest.raises(PasswordResetAlreadyRequestedError):
            await user_service_admin.request_password_reset(
                test_db_session,
                system_admin.id,
                user.id,
            )
