import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.emails.enums import EmailStatus, EmailType
from school_management_system_lite.emails.repository import EmailRepository
from school_management_system_lite.users.models.user import User
from school_management_system_lite.users.schemas.system_admin import UpdateEmailAdmin
from school_management_system_lite.users.services.system_admin import UserServiceAdmin
from school_management_system_lite.users.utils.exceptions import EmailAlreadyTakenError
from school_management_system_lite.utils.enums import OrderBy, UserRole
from tests.factories import make_director, make_student, make_teacher, make_user


class TestSuccess:
    async def test_successful_update(
        self, test_db_session: AsyncSession, system_admin: User
    ) -> None:
        user = await make_teacher(test_db_session)

        await UserServiceAdmin.update_email(
            test_db_session,
            system_admin.id,
            user.id,
            UpdateEmailAdmin(email="updated_email@gmail.com"),
        )

        await test_db_session.refresh(user)

        assert user.email == "updated_email@gmail.com"

    async def test_nothing_changes_if_payload_is_empty(
        self, test_db_session: AsyncSession, system_admin: User
    ) -> None:
        user = await make_teacher(test_db_session)

        email_before = user.email

        await UserServiceAdmin.update_identity(
            test_db_session, system_admin.id, user.id, UpdateEmailAdmin()
        )

        await test_db_session.refresh(user)

        assert user.email == email_before

    async def test_nothing_changes_if_current_values_are_provided(
        self, test_db_session: AsyncSession, system_admin: User
    ) -> None:
        user = await make_teacher(test_db_session)

        email_before = user.email

        await UserServiceAdmin.update_identity(
            test_db_session,
            system_admin.id,
            user.id,
            UpdateEmailAdmin(email=user.email),
        )

        await test_db_session.refresh(user)

        assert user.email == email_before


class TestEmailRow:
    async def test_email_row_is_added(
        self, test_db_session: AsyncSession, system_admin: User
    ) -> None:
        user = await make_teacher(test_db_session)

        await UserServiceAdmin.update_email(
            test_db_session,
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
                test_db_session, system_admin.id, user.id, UpdateEmailAdmin(email=email)
            )
