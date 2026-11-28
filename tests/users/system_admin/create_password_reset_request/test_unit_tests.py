import re
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.auth.models.password_reset import UserPasswordReset
from school_management_system_lite.auth.repositories import (
    password_reset as auth_password_reset_repository,
)
from school_management_system_lite.core.config import get_settings
from school_management_system_lite.core.enums import OrderBy
from school_management_system_lite.core.security import generate_token, verify_token
from school_management_system_lite.emails import repository as email_repository
from school_management_system_lite.emails.enums import EmailStatus, EmailType
from school_management_system_lite.emails.models import Email
from school_management_system_lite.users.models.user import User
from school_management_system_lite.users.services import (
    system_admin as user_service_admin,
)
from school_management_system_lite.users.utils.enums import UserRole, UserStatus
from school_management_system_lite.users.utils.exceptions import (
    UserNotFoundError,
    UserPendingActivationError,
)
from tests.factories import make_user


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


def extract_reset_token(html_body: str) -> str:
    link_prefix = f"{get_settings().APP_URL}/reset-password?token="
    token_match = re.search(re.escape(link_prefix) + r"([\w-]+)", html_body)

    assert token_match is not None

    return token_match.group(1)


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
    @pytest.mark.parametrize(
        ("role", "user_status"),
        [
            (UserRole.DIRECTOR, UserStatus.ACTIVE),
            (UserRole.TEACHER, UserStatus.ACTIVE),
            (UserRole.STUDENT, UserStatus.ACTIVE),
            (UserRole.TEACHER, UserStatus.INACTIVE),
            (UserRole.STUDENT, UserStatus.GRADUATED),
            (UserRole.STUDENT, UserStatus.WITHDRAWN),
            (UserRole.STUDENT, UserStatus.EXPELLED),
        ],
        ids=[
            "active-director",
            "active-teacher",
            "active-student",
            "inactive-teacher",
            "graduated-student",
            "withdrawn-student",
            "expelled-student",
        ],
    )
    async def test_create_password_reset_request_eligible_user_saves_request_and_queues_email(
        self,
        test_db_session: AsyncSession,
        system_admin: User,
        role: UserRole,
        user_status: UserStatus,
    ) -> None:
        target_user = await make_user(test_db_session, role=role, status=user_status)
        target_user_id = target_user.id
        target_email = target_user.email
        token_lifetime = timedelta(
            minutes=get_settings().PASSWORD_RESET_TOKEN_EXPIRES_MINUTES
        )

        started_at = datetime.now(UTC)
        await user_service_admin.create_password_reset_request(
            test_db_session, system_admin.id, target_user_id
        )
        finished_at = datetime.now(UTC)

        # No-op after a commit; discards the data if the service never committed.
        await test_db_session.rollback()

        password_reset = await auth_password_reset_repository.get_by_user_id(
            test_db_session, target_user_id
        )
        queued_emails = await get_queued_reset_emails(test_db_session, target_email)

        assert password_reset is not None
        assert (
            started_at + token_lifetime
            <= password_reset.password_reset_token_expires_at
            <= finished_at + token_lifetime
        )
        assert len(queued_emails) == 1

        queued_email = queued_emails[0]
        emailed_token = extract_reset_token(queued_email.html_body)

        assert verify_token(emailed_token, password_reset.password_reset_token_hash)
        assert queued_email.subject
        assert queued_email.status == EmailStatus.PENDING
        assert queued_email.email_type == EmailType.ADMIN_PASSWORD_RESET
        assert queued_email.triggered_by == system_admin.id

        await test_db_session.refresh(target_user)

        assert target_user.status == user_status

    @pytest.mark.parametrize(
        "existing_expiry_offset",
        [timedelta(minutes=-1), timedelta(minutes=5)],
        ids=["expired", "still-valid"],
    )
    async def test_create_password_reset_request_existing_request_overwrites_token_and_expiry(
        self,
        test_db_session: AsyncSession,
        system_admin: User,
        existing_expiry_offset: timedelta,
    ) -> None:
        target_user = await make_user(test_db_session, role=UserRole.TEACHER)
        target_user_id = target_user.id
        target_email = target_user.email
        _, old_token_hash = generate_token()
        existing_reset = UserPasswordReset(
            user_id=target_user_id,
            password_reset_token_hash=old_token_hash,
            password_reset_token_expires_at=datetime.now(UTC) + existing_expiry_offset,
        )

        test_db_session.add(existing_reset)
        await test_db_session.flush()

        existing_reset_id = existing_reset.id
        token_lifetime = timedelta(
            minutes=get_settings().PASSWORD_RESET_TOKEN_EXPIRES_MINUTES
        )

        started_at = datetime.now(UTC)
        await user_service_admin.create_password_reset_request(
            test_db_session, system_admin.id, target_user_id
        )
        finished_at = datetime.now(UTC)

        # No-op after a commit; discards the changes if the service never committed.
        await test_db_session.rollback()

        password_reset = await auth_password_reset_repository.get_by_user_id(
            test_db_session, target_user_id
        )
        queued_emails = await get_queued_reset_emails(test_db_session, target_email)

        assert password_reset is not None
        assert password_reset.id == existing_reset_id
        assert password_reset.password_reset_token_hash != old_token_hash
        assert (
            started_at + token_lifetime
            <= password_reset.password_reset_token_expires_at
            <= finished_at + token_lifetime
        )
        assert len(queued_emails) == 1

        emailed_token = extract_reset_token(queued_emails[0].html_body)

        assert verify_token(emailed_token, password_reset.password_reset_token_hash)


class TestEligibleUsers:
    async def test_create_password_reset_request_unknown_user_raises_not_found(
        self, test_db_session: AsyncSession, system_admin: User
    ) -> None:
        with pytest.raises(UserNotFoundError):
            await user_service_admin.create_password_reset_request(
                test_db_session, system_admin.id, 999999
            )

    async def test_create_password_reset_request_system_admin_target_raises_not_found(
        self, test_db_session: AsyncSession, system_admin: User
    ) -> None:
        target_admin = await make_user(test_db_session, role=UserRole.SYSTEM_ADMIN)

        with pytest.raises(UserNotFoundError):
            await user_service_admin.create_password_reset_request(
                test_db_session, system_admin.id, target_admin.id
            )

        await assert_no_reset_data_saved(test_db_session, target_admin)


class TestEligibleStatuses:
    async def test_create_password_reset_request_pending_activation_user_raises_conflict(
        self, test_db_session: AsyncSession, system_admin: User
    ) -> None:
        pending_user = await make_user(
            test_db_session,
            role=UserRole.TEACHER,
            status=UserStatus.PENDING_ACTIVATION,
        )

        with pytest.raises(UserPendingActivationError):
            await user_service_admin.create_password_reset_request(
                test_db_session, system_admin.id, pending_user.id
            )

        await assert_no_reset_data_saved(test_db_session, pending_user)
