from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.auth.repositories import (
    activation as auth_activation_repository,
)
from school_management_system_lite.core.config import get_settings
from school_management_system_lite.core.enums import OrderBy
from school_management_system_lite.emails import repository as email_repository
from school_management_system_lite.emails.enums import EmailStatus, EmailType
from school_management_system_lite.users.models import User
from school_management_system_lite.users.schemas.system_admin import CreateUserAdmin
from school_management_system_lite.users.services import (
    system_admin as user_service_admin,
)
from school_management_system_lite.users.utils.enums import UserRole, UserStatus
from school_management_system_lite.users.utils.exceptions import (
    EmailAlreadyTakenError,
    PhoneNumberAlreadyTakenError,
)
from tests.factories import make_user


class TestSuccess:
    @pytest.mark.parametrize(
        ["role", "date_of_birth", "phone_number", "email"],
        [
            (
                UserRole.DIRECTOR,
                date(1990, 5, 1),
                "+992999999999",
                "valid_director_email@gmail.com",
            ),
            (
                UserRole.TEACHER,
                date(2000, 5, 1),
                "+992888888888",
                "valid_teacher_email@gmail.com",
            ),
            (
                UserRole.STUDENT,
                date(2010, 5, 1),
                "+992777777777",
                "valid_student_email@gmail.com",
            ),
        ],
    )
    async def test_successful_registration(
        self,
        test_db_session: AsyncSession,
        system_admin: User,
        valid_user_payload: CreateUserAdmin,
        role: UserRole,
        date_of_birth: date,
        phone_number: str,
        email: str,
    ) -> None:
        valid_user_payload.role = role
        valid_user_payload.date_of_birth = date_of_birth
        valid_user_payload.phone_number = phone_number
        valid_user_payload.email = email

        created_user = await user_service_admin.create_user(
            test_db_session, system_admin.id, valid_user_payload
        )

        assert created_user.id is not None
        assert created_user.first_name == "Valid-Firstname"
        assert created_user.last_name == "Valid-Lastname"
        assert created_user.middle_name == "Valid-Middlename"
        assert created_user.date_of_birth == date_of_birth
        assert created_user.address == "Valid test address"
        assert created_user.phone_number == phone_number
        assert created_user.email == email
        assert created_user.password_hash is None
        assert created_user.role == role
        assert created_user.status == UserStatus.PENDING_ACTIVATION
        assert created_user.created_at is not None
        assert created_user.updated_at is not None
        assert created_user.created_by == system_admin.id


class TestUserActivationRow:
    async def test_user_activation_row_is_added(
        self,
        test_db_session: AsyncSession,
        system_admin: User,
        valid_user_payload: CreateUserAdmin,
    ) -> None:
        created_user = await user_service_admin.create_user(
            test_db_session, system_admin.id, valid_user_payload
        )

        activation_row = await auth_activation_repository.get_by_user_id(
            test_db_session, created_user.id
        )

        assert activation_row is not None
        assert activation_row.user_id == created_user.id
        assert activation_row.activation_token_hash is not None
        assert activation_row.activation_token_expires_at is not None
        assert activation_row.activation_token_expires_at <= datetime.now(
            UTC
        ) + timedelta(get_settings().ACTIVATION_TOKEN_EXPIRES_HOURS)


class TestEmailRow:
    async def test_email_row_is_added(
        self,
        test_db_session: AsyncSession,
        system_admin: User,
        valid_user_payload: CreateUserAdmin,
    ) -> None:
        created_user = await user_service_admin.create_user(
            test_db_session, system_admin.id, valid_user_payload
        )

        email_rows = await email_repository.get_by_recipient_email(
            test_db_session, created_user.email, order_by=OrderBy.DESC
        )

        assert len(email_rows) == 1

        email_row = email_rows[0]

        assert email_row.recipient_email == created_user.email
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
        await make_user(
            test_db_session, phone_number="+992888888888", role=UserRole.DIRECTOR
        )
        await make_user(
            test_db_session, phone_number="+992777777777", role=UserRole.TEACHER
        )
        await make_user(
            test_db_session, phone_number="+992666666666", role=UserRole.STUDENT
        )

        valid_user_payload.phone_number = phone_number
        valid_user_payload.role = role

        with pytest.raises(PhoneNumberAlreadyTakenError):
            await user_service_admin.create_user(
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
        await make_user(
            test_db_session, email="director_email@gmail.com", role=UserRole.DIRECTOR
        )
        await make_user(
            test_db_session, email="teacher_email@gmail.com", role=UserRole.TEACHER
        )
        await make_user(
            test_db_session, email="student_email@gmail.com", role=UserRole.STUDENT
        )

        valid_user_payload.role = role
        valid_user_payload.email = email

        with pytest.raises(EmailAlreadyTakenError):
            await user_service_admin.create_user(
                test_db_session, system_admin.id, valid_user_payload
            )
