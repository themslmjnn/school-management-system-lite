from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.core.enums import OrderBy
from school_management_system_lite.core.security import generate_token
from school_management_system_lite.emails import repository as email_repository
from school_management_system_lite.emails.enums import EmailStatus, EmailType
from school_management_system_lite.users.models.email_changes import UserEmailChange
from school_management_system_lite.users.repositories import (
    email_change as user_email_change_repository,
)
from school_management_system_lite.users.schemas.shared import UpdateEmailMe
from school_management_system_lite.users.services import shared as user_service_shared
from school_management_system_lite.users.utils.enums import UserRole
from school_management_system_lite.users.utils.exceptions import (
    EmailAlreadyTakenError,
    UserNotFoundError,
)
from tests.factories import make_user


class TestSuccess:
    async def test_successfully_requested_email_change(
        self, test_db_session: AsyncSession
    ) -> None:
        user = await make_user(test_db_session, role=UserRole.STUDENT)

        payload = UpdateEmailMe(new_email="new_user_email@gmail.com")

        await user_service_shared.request_email_change(
            test_db_session, user.id, payload
        )

        email_change_row = await user_email_change_repository.get_by_user_id(
            test_db_session, user.id
        )

        assert email_change_row is not None
        assert email_change_row.user_id == user.id
        assert email_change_row.new_email == "new_user_email@gmail.com"
        assert email_change_row.email_change_token_hash is not None
        assert email_change_row.email_change_token_expires_at is not None

        email = await email_repository.get_by_recipient_email(
            test_db_session,
            payload.new_email,
            email_type=frozenset({EmailType.EMAIL_CHANGE_REQUEST}),
            status=EmailStatus.PENDING,
            order_by=OrderBy.DESC,
        )

        assert len(email) == 1

        email_row = email[0]

        assert email_row.recipient_email == payload.new_email
        assert email_row.subject is not None
        assert email_row.html_body is not None
        assert email_row.status == EmailStatus.PENDING
        assert email_row.email_type == EmailType.EMAIL_CHANGE_REQUEST
        assert email_row.triggered_by is None

    async def test_replace_old_request_with_new_request(
        self, test_db_session: AsyncSession
    ) -> None:
        user = await make_user(test_db_session, role=UserRole.STUDENT)

        _, old_email_change_token_hash = generate_token()

        old_email_change = UserEmailChange(
            user_id=user.id,
            new_email="new_user_email@gmail.com",
            email_change_token_hash=old_email_change_token_hash,
            email_change_token_expires_at=datetime.now(UTC) - timedelta(minutes=1),
        )

        test_db_session.add(old_email_change)
        await test_db_session.flush()

        await user_service_shared.request_email_change(
            test_db_session,
            user.id,
            UpdateEmailMe(new_email="user_new_email@gmail.com"),
        )

        email_change_row = await user_email_change_repository.get_by_user_id(
            test_db_session, user.id
        )

        assert email_change_row is not None
        assert email_change_row.user_id == user.id
        assert email_change_row.email_change_token_hash != old_email_change_token_hash
        assert email_change_row.email_change_token_expires_at is not None

        email = await email_repository.get_by_recipient_email(
            test_db_session,
            "user_new_email@gmail.com",
            email_type=frozenset({EmailType.EMAIL_CHANGE_REQUEST}),
            status=EmailStatus.PENDING,
            order_by=OrderBy.DESC,
        )

        assert len(email) == 1


class TestEligibleUsers:
    async def test_raise_error_on_unknown_users(
        self,
        test_db_session: AsyncSession,
    ) -> None:
        with pytest.raises(UserNotFoundError):
            await user_service_shared.request_email_change(
                test_db_session, 999999, UpdateEmailMe(new_email="new_email@gmail.com")
            )


class TestDBConstraints:
    async def test_raises_on_duplicate_emails(
        self, test_db_session: AsyncSession
    ) -> None:
        await make_user(
            test_db_session, role=UserRole.STUDENT, email="student_one_email@gmail.com"
        )
        user = await make_user(test_db_session, role=UserRole.STUDENT)

        with pytest.raises(EmailAlreadyTakenError):
            await user_service_shared.request_email_change(
                test_db_session,
                user.id,
                UpdateEmailMe(new_email="student_one_email@gmail.com"),
            )
