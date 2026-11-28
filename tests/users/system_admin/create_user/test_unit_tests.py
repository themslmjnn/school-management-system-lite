import itertools
import re
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.auth.models.activation import UserActivation
from school_management_system_lite.auth.repositories import (
    activation as auth_activation_repository,
)
from school_management_system_lite.core.config import get_settings
from school_management_system_lite.core.enums import OrderBy
from school_management_system_lite.core.security import verify_token
from school_management_system_lite.database.base import Base
from school_management_system_lite.emails import repository as email_repository
from school_management_system_lite.emails.enums import EmailStatus, EmailType
from school_management_system_lite.emails.models import Email
from school_management_system_lite.users.models.user import User
from school_management_system_lite.users.services import (
    system_admin as user_service_admin,
)
from school_management_system_lite.users.utils.enums import UserRole, UserStatus
from school_management_system_lite.users.utils.exceptions import (
    EmailAlreadyTakenError,
    PhoneNumberAlreadyTakenError,
)
from tests.factories import make_create_user_payload, make_user

CREATABLE_ROLES = (UserRole.DIRECTOR, UserRole.TEACHER, UserRole.STUDENT)

EXISTING_AND_NEW_ROLE_PAIRS = [
    pytest.param(
        existing_role,
        new_role,
        id=f"{existing_role.name.lower()}_exists-{new_role.name.lower()}_new",
    )
    for existing_role, new_role in itertools.product(CREATABLE_ROLES, repeat=2)
]

ACTIVATION_LINK_TOKEN_PATTERN = re.compile(r"/activate\?token=([A-Za-z0-9_-]+)")


async def _count_rows(db_session: AsyncSession, model: type[Base]) -> int:
    return await db_session.scalar(select(func.count()).select_from(model)) or 0


class TestSuccess:
    @pytest.mark.parametrize(
        "role", CREATABLE_ROLES, ids=[role.name.lower() for role in CREATABLE_ROLES]
    )
    async def test_create_user_valid_payload_persists_pending_activation_user(
        self,
        test_db_session: AsyncSession,
        system_admin: User,
        role: UserRole,
    ) -> None:
        payload = make_create_user_payload(role=role)

        created_user = await user_service_admin.create_user(
            test_db_session, system_admin.id, payload
        )

        assert created_user.id is not None
        assert created_user.first_name == payload.first_name
        assert created_user.last_name == payload.last_name
        assert created_user.middle_name == payload.middle_name
        assert created_user.date_of_birth == payload.date_of_birth
        assert created_user.address == payload.address
        assert created_user.phone_number == payload.phone_number
        assert created_user.email == payload.email
        assert created_user.password_hash is None
        assert created_user.role == role
        assert created_user.status == UserStatus.PENDING_ACTIVATION
        assert created_user.created_by == system_admin.id
        assert created_user.created_at is not None
        assert created_user.updated_at is not None


class TestUserActivationRow:
    async def test_create_user_valid_payload_stores_activation_hash_with_expiry_in_window(
        self,
        test_db_session: AsyncSession,
        system_admin: User,
    ) -> None:
        expiry_window = timedelta(hours=get_settings().ACTIVATION_TOKEN_EXPIRES_HOURS)
        payload = make_create_user_payload()

        time_before_call = datetime.now(UTC)
        created_user = await user_service_admin.create_user(
            test_db_session, system_admin.id, payload
        )
        time_after_call = datetime.now(UTC)

        activation_row = await auth_activation_repository.get_by_user_id(
            test_db_session, created_user.id
        )

        assert activation_row is not None
        assert activation_row.user_id == created_user.id
        assert activation_row.activation_token_hash
        assert (
            time_before_call + expiry_window
            <= activation_row.activation_token_expires_at
            <= time_after_call + expiry_window
        )

    async def test_create_user_valid_payload_email_link_token_matches_stored_hash(
        self,
        test_db_session: AsyncSession,
        system_admin: User,
    ) -> None:
        payload = make_create_user_payload()

        created_user = await user_service_admin.create_user(
            test_db_session, system_admin.id, payload
        )

        activation_row = await auth_activation_repository.get_by_user_id(
            test_db_session, created_user.id
        )
        email_rows = await email_repository.get_by_recipient_email(
            test_db_session, created_user.email, order_by=OrderBy.DESC
        )
        token_match = ACTIVATION_LINK_TOKEN_PATTERN.search(email_rows[0].html_body)

        assert activation_row is not None
        assert token_match is not None
        assert verify_token(token_match.group(1), activation_row.activation_token_hash)


class TestEmailRow:
    async def test_create_user_valid_payload_queues_pending_activation_email(
        self,
        test_db_session: AsyncSession,
        system_admin: User,
    ) -> None:
        payload = make_create_user_payload()

        created_user = await user_service_admin.create_user(
            test_db_session, system_admin.id, payload
        )

        email_rows = await email_repository.get_by_recipient_email(
            test_db_session, created_user.email, order_by=OrderBy.DESC
        )

        assert len(email_rows) == 1

        email_row = email_rows[0]

        assert email_row.recipient_email == created_user.email
        assert email_row.subject
        assert email_row.html_body
        assert email_row.email_type == EmailType.ACCOUNT_ACTIVATION
        assert email_row.status == EmailStatus.PENDING
        assert email_row.scheduled_for is not None
        assert email_row.triggered_by == system_admin.id


class TestDBConstraints:
    @pytest.mark.parametrize(["existing_role", "new_role"], EXISTING_AND_NEW_ROLE_PAIRS)
    async def test_create_user_duplicate_phone_number_raises_phone_taken_error(
        self,
        test_db_session: AsyncSession,
        system_admin: User,
        existing_role: UserRole,
        new_role: UserRole,
    ) -> None:
        existing_user = await make_user(test_db_session, role=existing_role)
        payload = make_create_user_payload(
            role=new_role, phone_number=existing_user.phone_number
        )

        with pytest.raises(PhoneNumberAlreadyTakenError):
            await user_service_admin.create_user(
                test_db_session, system_admin.id, payload
            )

    @pytest.mark.parametrize(["existing_role", "new_role"], EXISTING_AND_NEW_ROLE_PAIRS)
    async def test_create_user_duplicate_email_raises_email_taken_error(
        self,
        test_db_session: AsyncSession,
        system_admin: User,
        existing_role: UserRole,
        new_role: UserRole,
    ) -> None:
        existing_user = await make_user(test_db_session, role=existing_role)
        payload = make_create_user_payload(role=new_role, email=existing_user.email)

        with pytest.raises(EmailAlreadyTakenError):
            await user_service_admin.create_user(
                test_db_session, system_admin.id, payload
            )


class TestFailureHandling:
    @pytest.mark.parametrize("duplicated_field", ["email", "phone_number"])
    async def test_create_user_duplicate_value_persists_nothing(
        self,
        test_db_session: AsyncSession,
        system_admin: User,
        duplicated_field: str,
    ) -> None:
        existing_user = await make_user(test_db_session)
        await test_db_session.commit()

        system_admin_id = system_admin.id
        payload = make_create_user_payload(
            **{duplicated_field: getattr(existing_user, duplicated_field)}
        )
        models = (User, UserActivation, Email)
        row_counts_before = [
            await _count_rows(test_db_session, model) for model in models
        ]

        with pytest.raises((EmailAlreadyTakenError, PhoneNumberAlreadyTakenError)):
            await user_service_admin.create_user(
                test_db_session, system_admin_id, payload
            )

        row_counts_after = [
            await _count_rows(test_db_session, model) for model in models
        ]

        assert row_counts_after == row_counts_before

    async def test_create_user_unknown_actor_id_raises_integrity_error(
        self, test_db_session: AsyncSession
    ) -> None:
        unknown_actor_id = 999_999_999
        payload = make_create_user_payload()

        with pytest.raises(IntegrityError):
            await user_service_admin.create_user(
                test_db_session, unknown_actor_id, payload
            )
