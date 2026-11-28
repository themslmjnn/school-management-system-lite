import re
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.auth.models.activation import UserActivation
from school_management_system_lite.auth.repositories import (
    activation as auth_activation_repository,
)
from school_management_system_lite.core.config import get_settings
from school_management_system_lite.core.security import verify_token
from school_management_system_lite.emails import repository as email_repository
from school_management_system_lite.emails.enums import EmailStatus, EmailType
from school_management_system_lite.users.models.user import User
from school_management_system_lite.users.services import (
    system_admin as user_service_admin,
)
from school_management_system_lite.users.utils.enums import UserRole, UserStatus
from school_management_system_lite.users.utils.exceptions import (
    ResendActivationEmailDenied,
    UserNotFoundError,
)
from tests.factories import make_user

UNKNOWN_USER_ID = 999999


async def get_queued_activation_emails(
    test_db_session: AsyncSession, recipient_email: str
) -> Sequence[Any]:
    return await email_repository.get_by_recipient_email(
        test_db_session,
        recipient_email,
        email_type=frozenset({EmailType.ACCOUNT_ACTIVATION}),
        status=EmailStatus.PENDING,
    )


async def get_stored_activation(
    test_db_session: AsyncSession, user_id: int
) -> UserActivation:
    activation = await auth_activation_repository.get_by_user_id(
        test_db_session, user_id
    )
    assert activation is not None

    # Reload from the database so unflushed in-memory changes do not count
    await test_db_session.refresh(activation)

    return activation


def extract_activation_token(html_body: str) -> str:
    token_match = re.search(r"/activate\?token=([\w-]+)", html_body)

    assert token_match is not None, "Activation link not found in email body"

    return token_match.group(1)


class TestSuccess:
    @pytest.mark.parametrize(
        "role",
        [UserRole.DIRECTOR, UserRole.TEACHER, UserRole.STUDENT],
        ids=["director", "teacher", "student"],
    )
    async def test_resend_activation_email_for_pending_user_queues_email(
        self,
        test_db_session: AsyncSession,
        system_admin: User,
        role: UserRole,
    ) -> None:
        target_user = await make_user(
            test_db_session,
            role=role,
            status=UserStatus.PENDING_ACTIVATION,
        )

        await user_service_admin.resend_activation_email(
            test_db_session, system_admin.id, target_user.id
        )

        queued_emails = await get_queued_activation_emails(
            test_db_session, target_user.email
        )

        assert len(queued_emails) == 1

        queued_email = queued_emails[0]

        assert queued_email.recipient_email == target_user.email
        assert queued_email.subject is not None
        assert queued_email.html_body is not None
        assert queued_email.status == EmailStatus.PENDING
        assert queued_email.email_type == EmailType.ACCOUNT_ACTIVATION
        assert queued_email.triggered_by == system_admin.id

    async def test_resend_activation_email_without_activation_creates_one_and_queues_email(
        self,
        test_db_session: AsyncSession,
        system_admin: User,
    ) -> None:
        target_user = await make_user(
            test_db_session,
            role=UserRole.TEACHER,
            status=UserStatus.PENDING_ACTIVATION,
        )
        factory_activation = await get_stored_activation(
            test_db_session, target_user.id
        )
        await test_db_session.delete(factory_activation)
        await test_db_session.flush()

        await user_service_admin.resend_activation_email(
            test_db_session, system_admin.id, target_user.id
        )

        created_activation = await auth_activation_repository.get_by_user_id(
            test_db_session, target_user.id
        )
        queued_emails = await get_queued_activation_emails(
            test_db_session, target_user.email
        )

        assert created_activation is not None
        assert len(queued_emails) == 1

    async def test_resend_activation_email_with_existing_activation_replaces_token_hash(
        self,
        test_db_session: AsyncSession,
        system_admin: User,
    ) -> None:
        target_user = await make_user(
            test_db_session,
            role=UserRole.TEACHER,
            status=UserStatus.PENDING_ACTIVATION,
        )
        old_activation = await get_stored_activation(test_db_session, target_user.id)
        old_token_hash = old_activation.activation_token_hash

        await user_service_admin.resend_activation_email(
            test_db_session, system_admin.id, target_user.id
        )

        new_activation = await get_stored_activation(test_db_session, target_user.id)

        assert new_activation.activation_token_hash != old_token_hash

    async def test_resend_activation_email_for_pending_user_emails_token_matching_hash(
        self,
        test_db_session: AsyncSession,
        system_admin: User,
    ) -> None:
        target_user = await make_user(
            test_db_session,
            role=UserRole.TEACHER,
            status=UserStatus.PENDING_ACTIVATION,
        )

        await user_service_admin.resend_activation_email(
            test_db_session, system_admin.id, target_user.id
        )

        queued_emails = await get_queued_activation_emails(
            test_db_session, target_user.email
        )

        assert len(queued_emails) == 1

        emailed_token = extract_activation_token(queued_emails[0].html_body)
        activation = await get_stored_activation(test_db_session, target_user.id)

        assert verify_token(emailed_token, activation.activation_token_hash)

    async def test_resend_activation_email_with_expired_activation_renews_expiry(
        self,
        test_db_session: AsyncSession,
        system_admin: User,
    ) -> None:
        target_user = await make_user(
            test_db_session,
            role=UserRole.TEACHER,
            status=UserStatus.PENDING_ACTIVATION,
        )
        expired_activation = await get_stored_activation(
            test_db_session, target_user.id
        )
        expired_activation.activation_token_expires_at = datetime.now(UTC) - timedelta(
            hours=1
        )

        await test_db_session.flush()

        token_lifetime = timedelta(hours=get_settings().ACTIVATION_TOKEN_EXPIRES_HOURS)
        time_before_resend = datetime.now(UTC)

        await user_service_admin.resend_activation_email(
            test_db_session, system_admin.id, target_user.id
        )

        time_after_resend = datetime.now(UTC)
        renewed_activation = await get_stored_activation(
            test_db_session, target_user.id
        )

        assert (
            time_before_resend + token_lifetime
            <= renewed_activation.activation_token_expires_at
            <= time_after_resend + token_lifetime
        )

    async def test_resend_activation_email_twice_keeps_only_latest_token_valid(
        self,
        test_db_session: AsyncSession,
        system_admin: User,
    ) -> None:
        target_user = await make_user(
            test_db_session,
            role=UserRole.TEACHER,
            status=UserStatus.PENDING_ACTIVATION,
        )

        await user_service_admin.resend_activation_email(
            test_db_session, system_admin.id, target_user.id
        )

        emails_after_first_resend = await get_queued_activation_emails(
            test_db_session, target_user.email
        )

        assert len(emails_after_first_resend) == 1

        first_email = emails_after_first_resend[0]

        await user_service_admin.resend_activation_email(
            test_db_session, system_admin.id, target_user.id
        )

        queued_emails = await get_queued_activation_emails(
            test_db_session, target_user.email
        )

        assert len(queued_emails) == 2

        # created_at is identical within one test transaction, so match by id
        second_email = next(
            email for email in queued_emails if email.id != first_email.id
        )
        first_token = extract_activation_token(first_email.html_body)
        second_token = extract_activation_token(second_email.html_body)
        activation = await get_stored_activation(test_db_session, target_user.id)

        assert not verify_token(first_token, activation.activation_token_hash)
        assert verify_token(second_token, activation.activation_token_hash)


class TestEligibleUsers:
    async def test_resend_activation_email_for_pending_system_admin_raises_not_found(
        self,
        test_db_session: AsyncSession,
        system_admin: User,
    ) -> None:
        target_admin = await make_user(
            test_db_session,
            role=UserRole.SYSTEM_ADMIN,
            status=UserStatus.PENDING_ACTIVATION,
        )

        with pytest.raises(UserNotFoundError):
            await user_service_admin.resend_activation_email(
                test_db_session, system_admin.id, target_admin.id
            )

        queued_emails = await get_queued_activation_emails(
            test_db_session, target_admin.email
        )

        assert not queued_emails

    async def test_resend_activation_email_for_unknown_user_raises_not_found(
        self,
        test_db_session: AsyncSession,
        system_admin: User,
    ) -> None:
        with pytest.raises(UserNotFoundError):
            await user_service_admin.resend_activation_email(
                test_db_session, system_admin.id, UNKNOWN_USER_ID
            )


class TestEligibleStatuses:
    @pytest.mark.parametrize(
        "user_status",
        [
            UserStatus.ACTIVE,
            UserStatus.INACTIVE,
            UserStatus.EXPELLED,
            UserStatus.GRADUATED,
            UserStatus.WITHDRAWN,
        ],
        ids=["active", "inactive", "expelled", "graduated", "withdrawn"],
    )
    async def test_resend_activation_email_for_non_pending_user_is_denied_without_changes(
        self,
        test_db_session: AsyncSession,
        system_admin: User,
        user_status: UserStatus,
    ) -> None:
        target_user = await make_user(
            test_db_session,
            role=UserRole.TEACHER,
            status=user_status,
        )

        with pytest.raises(ResendActivationEmailDenied):
            await user_service_admin.resend_activation_email(
                test_db_session, system_admin.id, target_user.id
            )

        activation = await auth_activation_repository.get_by_user_id(
            test_db_session, target_user.id
        )
        queued_emails = await get_queued_activation_emails(
            test_db_session, target_user.email
        )

        assert activation is None
        assert not queued_emails
