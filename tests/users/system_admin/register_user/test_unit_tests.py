from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.auth.repositories.activation import (
    UserActivationRepository,
)
from school_management_system_lite.auth.repositories.session import (
    UserSessionRepository,
)
from school_management_system_lite.core.config import get_settings
from school_management_system_lite.emails.enums import EmailStatus, EmailType
from school_management_system_lite.emails.repository import EmailRepository
from school_management_system_lite.users.models.user import User
from school_management_system_lite.users.schemas.system_admin import CreateUserAdmin
from school_management_system_lite.users.services.system_admin import UserServiceAdmin
from school_management_system_lite.users.utils.exceptions import (
    EmailAlreadyTakenError,
    PhoneNumberAlreadyTakenError,
)
from school_management_system_lite.utils.enums import OrderBy, UserRole, UserStatus
from tests.factories import make_director, make_student, make_teacher


class TestSuccess:
    async def test_successful_staff_registration(
        self,
        test_db_session: AsyncSession,
        system_admin: User,
        valid_user_payload: CreateUserAdmin,
    ) -> None:
        valid_user_payload.date_of_birth = date(2000, 5, 1)
        valid_user_payload.phone_number = "+992111222111"
        valid_user_payload.email = "valid_staff_email@gmail.com"
        valid_user_payload.role = UserRole.TEACHER

        registered_user = await UserServiceAdmin.register_user(
            test_db_session, system_admin.id, valid_user_payload
        )

        assert registered_user.id is not None
        assert registered_user.first_name == "Valid-First-Name"
        assert registered_user.last_name == "Valid-Last-Name"
        assert registered_user.middle_name is None
        assert registered_user.date_of_birth == date(2000, 5, 1)
        assert registered_user.address == "valid_address"
        assert registered_user.phone_number == "+992111222111"
        assert registered_user.email == "valid_staff_email@gmail.com"
        assert registered_user.password_hash is None
        assert registered_user.role == UserRole.TEACHER
        assert registered_user.status == UserStatus.PENDING_ACTIVATION
        assert registered_user.created_at is not None
        assert registered_user.updated_at is not None
        assert registered_user.created_by == system_admin.id

    async def test_successful_student_registration(
        self,
        test_db_session: AsyncSession,
        system_admin: User,
        valid_user_payload: CreateUserAdmin,
    ) -> None:
        registered_user = await UserServiceAdmin.register_user(
            test_db_session, system_admin.id, valid_user_payload
        )

        assert registered_user.id is not None
        assert registered_user.first_name == "Valid-First-Name"
        assert registered_user.last_name == "Valid-Last-Name"
        assert registered_user.middle_name is None
        assert registered_user.date_of_birth == date(2008, 5, 1)
        assert registered_user.address == "valid_address"
        assert registered_user.phone_number == "+992222111222"
        assert registered_user.email == "valid_student_email@gmail.com"
        assert registered_user.password_hash is None
        assert registered_user.role == UserRole.STUDENT
        assert registered_user.status == UserStatus.PENDING_ACTIVATION
        assert registered_user.created_at is not None
        assert registered_user.updated_at is not None
        assert registered_user.created_by == system_admin.id


class TestUserSessionRow:
    async def test_user_session_is_added(
        self,
        test_db_session: AsyncSession,
        system_admin: User,
        valid_user_payload: CreateUserAdmin,
    ) -> None:
        registered_user = await UserServiceAdmin.register_user(
            test_db_session, system_admin.id, valid_user_payload
        )

        session_row = await UserSessionRepository.get_by_user_id(
            test_db_session, registered_user.id
        )

        assert session_row is not None
        assert session_row.user_id == registered_user.id
        assert session_row.access_token_version == 1
        assert session_row.refresh_token_hash is None
        assert session_row.refresh_token_expires_at is None


class TestUserActivationRow:
    async def test_user_activation_row_is_added(
        self,
        test_db_session: AsyncSession,
        system_admin: User,
        valid_user_payload: CreateUserAdmin,
    ) -> None:
        registered_user = await UserServiceAdmin.register_user(
            test_db_session, system_admin.id, valid_user_payload
        )

        activation_row = await UserActivationRepository.get_by_user_id(
            test_db_session, registered_user.id
        )

        assert activation_row is not None
        assert activation_row.user_id == registered_user.id
        assert activation_row.activation_token_hash is not None
        assert activation_row.activation_token_expires_at is not None
        assert activation_row.activation_token_expires_at.replace(
            tzinfo=UTC
        ) <= datetime.now(UTC) + timedelta(
            get_settings().ACTIVATION_TOKEN_EXPIRES_HOURS
        )


class TestEmailRow:
    async def test_email_row_is_added(
        self,
        test_db_session: AsyncSession,
        system_admin: User,
        valid_user_payload: CreateUserAdmin,
    ) -> None:
        registered_user = await UserServiceAdmin.register_user(
            test_db_session, system_admin.id, valid_user_payload
        )

        email_rows = await EmailRepository.get_by_recipient_email(
            test_db_session, registered_user.email, order_by=OrderBy.DESC
        )

        assert len(email_rows) == 1

        email_row = email_rows[0]

        assert email_row.recipient_email == registered_user.email
        assert email_row.subject is not None
        assert email_row.html_body is not None
        assert email_row.email_type == EmailType.ACCOUNT_ACTIVATION
        assert email_row.status == EmailStatus.PENDING
        assert email_row.scheduled_for is not None
        assert email_row.triggered_by == system_admin.id


class TestDBConstraints:
    @pytest.mark.parametrize(
        ["role", "phone_number"],
        [
            (UserRole.DIRECTOR, "+992666666666"),
            (UserRole.DIRECTOR, "+992777777777"),
            (UserRole.TEACHER, "+992666666666"),
            (UserRole.TEACHER, "+992888888888"),
            (UserRole.STUDENT, "+992666666666"),
            (UserRole.STUDENT, "+992777777777"),
        ],
    )
    async def test_duplicate_phone_number_is_caught(
        self,
        test_db_session: AsyncSession,
        system_admin: User,
        valid_user_payload: CreateUserAdmin,
        role: UserRole,
        phone_number: str,
    ) -> None:
        await make_director(test_db_session, phone_number="+992888888888")
        await make_teacher(test_db_session, phone_number="+992777777777")
        await make_student(test_db_session, phone_number="+992666666666")

        valid_user_payload.phone_number = phone_number
        valid_user_payload.role = role

        with pytest.raises(PhoneNumberAlreadyTakenError):
            await UserServiceAdmin.register_user(
                test_db_session, system_admin.id, valid_user_payload
            )

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
        system_admin: User,
        valid_user_payload: CreateUserAdmin,
        role: UserRole,
        email: str,
    ) -> None:
        await make_director(test_db_session, email="director_email@gmail.com")
        await make_teacher(test_db_session, email="teacher_email@gmail.com")
        await make_student(test_db_session, email="student_email@gmail.com")

        valid_user_payload.role = role
        valid_user_payload.email = email

        with pytest.raises(EmailAlreadyTakenError):
            await UserServiceAdmin.register_user(
                test_db_session, system_admin.id, valid_user_payload
            )
