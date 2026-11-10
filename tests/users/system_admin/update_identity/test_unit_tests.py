import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.users.models.user import User
from school_management_system_lite.users.schemas.system_admin import UpdateIdentityAdmin
from school_management_system_lite.users.services.system_admin import UserServiceAdmin
from school_management_system_lite.users.utils.exceptions import (
    PhoneNumberAlreadyTakenError,
)
from school_management_system_lite.utils.enums import UserRole
from tests.factories import make_director, make_student, make_teacher, make_user


class TestSuccess:
    async def test_successful_update(
        self,
        test_db_session: AsyncSession,
        system_admin: User,
        mock_send_admin_identity_override_email,
    ) -> None:
        user = await make_teacher(test_db_session)

        payload = UpdateIdentityAdmin(
            first_name="updated-first-name",
            last_name="updated-last-name",
            middle_name="updated-middle-name",
            address="updated address",
            phone_number="+992 111 222 333",
        )

        await UserServiceAdmin.update_identity(
            test_db_session, system_admin.id, user.id, payload
        )

        await test_db_session.refresh(user)

        assert user.first_name == "Updated-First-Name"
        assert user.last_name == "Updated-Last-Name"
        assert user.middle_name == "Updated-Middle-Name"
        assert user.address == "updated address"
        assert user.phone_number == "+992111222333"

    async def test_ignores_unset_fields(
        self,
        test_db_session: AsyncSession,
        system_admin: User,
        mock_send_admin_identity_override_email,
    ) -> None:
        user = await make_teacher(test_db_session)

        payload = UpdateIdentityAdmin(
            first_name="updated-first-name", phone_number="+992 111 222 333"
        )

        await UserServiceAdmin.update_identity(
            test_db_session, system_admin.id, user.id, payload
        )

        await test_db_session.refresh(user)

        assert user.first_name == "Updated-First-Name"
        assert user.phone_number == "+992111222333"

    async def test_nothing_changes_if_payload_is_empty(
        self,
        test_db_session: AsyncSession,
        system_admin: User,
        mock_send_admin_identity_override_email,
    ) -> None:
        user = await make_teacher(test_db_session)

        original_values = {
            "first_name": user.first_name,
            "last_name": user.last_name,
            "middle_name": user.middle_name,
            "address": user.address,
            "phone_number": user.phone_number,
        }

        await UserServiceAdmin.update_identity(
            test_db_session, system_admin.id, user.id, UpdateIdentityAdmin()
        )

        await test_db_session.refresh(user)

        assert user.first_name == original_values["first_name"]
        assert user.last_name == original_values["last_name"]
        assert user.middle_name == original_values["middle_name"]
        assert user.address == original_values["address"]
        assert user.phone_number == original_values["phone_number"]

        mock_send_admin_identity_override_email.assert_not_called()

    async def test_nothing_changes_if_current_values_are_provided(
        self,
        test_db_session: AsyncSession,
        system_admin: User,
        mock_send_admin_identity_override_email,
    ) -> None:
        user = await make_teacher(test_db_session)

        original_values = {
            "first_name": user.first_name,
            "phone_number": user.phone_number,
        }

        await UserServiceAdmin.update_identity(
            test_db_session,
            system_admin.id,
            user.id,
            UpdateIdentityAdmin.model_validate(original_values),
        )

        await test_db_session.refresh(user)

        assert user.first_name == original_values["first_name"]
        assert user.phone_number == original_values["phone_number"]

        mock_send_admin_identity_override_email.assert_not_called()


class TestEmailSending:
    async def test_identity_override_email_is_sent(
        self,
        test_db_session: AsyncSession,
        system_admin: User,
        mock_send_admin_identity_override_email,
    ) -> None:
        user = await make_teacher(test_db_session)

        payload = UpdateIdentityAdmin(phone_number="+992111222333")

        await UserServiceAdmin.update_identity(
            test_db_session, system_admin.id, user.id, payload
        )

        mock_send_admin_identity_override_email.assert_called_once_with(user.email)


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
        role: UserRole,
        phone_number: str,
    ) -> None:
        user = await make_user(test_db_session, role=role)

        await make_director(test_db_session, phone_number="+992888888888")
        await make_teacher(test_db_session, phone_number="+992777777777")
        await make_student(test_db_session, phone_number="+992666666666")

        payload = UpdateIdentityAdmin(phone_number=phone_number)

        with pytest.raises(PhoneNumberAlreadyTakenError):
            await UserServiceAdmin.update_identity(
                test_db_session, system_admin.id, user.id, payload
            )
