import pytest
from httpx import AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.core.redis.cache_keys import UsersCacheKeys
from school_management_system_lite.users.models import User
from school_management_system_lite.users.schemas.system_admin import (
    UpdateUserIdentityAdmin,
)
from school_management_system_lite.users.services import (
    system_admin as user_service_admin,
)
from school_management_system_lite.users.utils.enums import UserRole
from school_management_system_lite.users.utils.exceptions import (
    PhoneNumberAlreadyTakenError,
    UserNotFoundError,
)
from tests.factories import make_user


class TestSuccess:
    async def test_successful_update(
        self,
        test_db_session: AsyncSession,
        test_redis_client: Redis | None,
        test_resend_client: AsyncClient,
        system_admin: User,
        mock_send_admin_identity_override_email,
        mock_users_delete_cache_system_admin,
    ) -> None:
        user = await make_user(test_db_session, role=UserRole.TEACHER)

        payload = UpdateUserIdentityAdmin(
            first_name="updated-firstname",
            last_name="updated-lastname",
            middle_name="updated-middlename",
            phone_number="+992 111 222 333",
            address="updated user address",
        )

        await user_service_admin.update_user_identity(
            test_db_session,
            test_redis_client,
            test_resend_client,
            system_admin.id,
            user.id,
            payload,
        )

        await test_db_session.refresh(user)

        assert user.first_name == "Updated-Firstname"
        assert user.last_name == "Updated-Lastname"
        assert user.middle_name == "Updated-Middlename"
        assert user.phone_number == "+992111222333"
        assert user.address == "updated user address"

    async def test_ignores_unset_fields(
        self,
        test_db_session: AsyncSession,
        test_redis_client: Redis | None,
        test_resend_client: AsyncClient,
        system_admin: User,
        mock_send_admin_identity_override_email,
        mock_users_delete_cache_system_admin,
    ) -> None:
        user = await make_user(test_db_session, role=UserRole.TEACHER)

        payload = UpdateUserIdentityAdmin(
            first_name="updated-firstname", phone_number="+992 111 222 333"
        )

        await user_service_admin.update_user_identity(
            test_db_session,
            test_redis_client,
            test_resend_client,
            system_admin.id,
            user.id,
            payload,
        )

        await test_db_session.refresh(user)

        assert user.first_name == "Updated-Firstname"
        assert user.phone_number == "+992111222333"

    async def test_raises_one_required_fields_with_null_values(
        self,
        test_db_session: AsyncSession,
        test_redis_client: Redis | None,
        test_resend_client: AsyncClient,
        system_admin: User,
    ) -> None:
        user = await make_user(test_db_session, role=UserRole.TEACHER)

        with pytest.raises(ValueError):
            await user_service_admin.update_user_identity(
                test_db_session,
                test_redis_client,
                test_resend_client,
                system_admin.id,
                user.id,
                UpdateUserIdentityAdmin(
                    first_name=None, phone_number="+992 111 222 333"
                ),
            )

    async def test_nothing_changes_if_payload_is_empty(
        self,
        test_db_session: AsyncSession,
        test_redis_client: Redis | None,
        test_resend_client: AsyncClient,
        system_admin: User,
        mock_send_admin_identity_override_email,
        mock_users_delete_cache_system_admin,
    ) -> None:
        user = await make_user(test_db_session, role=UserRole.TEACHER)

        original_values = {
            "first_name": user.first_name,
            "last_name": user.last_name,
            "middle_name": user.middle_name,
            "address": user.address,
            "phone_number": user.phone_number,
        }

        await user_service_admin.update_user_identity(
            test_db_session,
            test_redis_client,
            test_resend_client,
            system_admin.id,
            user.id,
            UpdateUserIdentityAdmin(),
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
        test_redis_client: Redis | None,
        test_resend_client: AsyncClient,
        system_admin: User,
        mock_send_admin_identity_override_email,
        mock_users_delete_cache_system_admin,
    ) -> None:
        user = await make_user(test_db_session, role=UserRole.TEACHER)

        original_values = {
            "first_name": user.first_name,
            "phone_number": user.phone_number,
        }

        await user_service_admin.update_user_identity(
            test_db_session,
            test_redis_client,
            test_resend_client,
            system_admin.id,
            user.id,
            UpdateUserIdentityAdmin.model_validate(original_values),
        )

        await test_db_session.refresh(user)

        assert user.first_name == original_values["first_name"]
        assert user.phone_number == original_values["phone_number"]

        mock_send_admin_identity_override_email.assert_not_called()


class TestEligibleUsers:
    async def test_updating_system_admin_is_prevented(
        self,
        test_db_session: AsyncSession,
        test_redis_client: Redis | None,
        test_resend_client: AsyncClient,
        system_admin: User,
    ) -> None:
        with pytest.raises(UserNotFoundError):
            await user_service_admin.update_user_identity(
                test_db_session,
                test_redis_client,
                test_resend_client,
                actor_id=system_admin.id,
                user_id=system_admin.id,
                payload=UpdateUserIdentityAdmin(),
            )

    async def test_system_admin_cannot_update_another_system_admin(
        self,
        test_db_session: AsyncSession,
        test_redis_client: Redis | None,
        test_resend_client: AsyncClient,
        system_admin: User,
    ) -> None:
        user = await make_user(test_db_session, role=UserRole.SYSTEM_ADMIN)

        with pytest.raises(UserNotFoundError):
            await user_service_admin.update_user_identity(
                test_db_session,
                test_redis_client,
                test_resend_client,
                system_admin.id,
                user.id,
                payload=UpdateUserIdentityAdmin(),
            )

    async def test_raise_error_on_unknown_users(
        self,
        test_db_session: AsyncSession,
        test_redis_client: Redis | None,
        test_resend_client: AsyncClient,
        system_admin: User,
    ) -> None:
        with pytest.raises(UserNotFoundError):
            await user_service_admin.update_user_identity(
                test_db_session,
                test_redis_client,
                test_resend_client,
                system_admin.id,
                999999,
                payload=UpdateUserIdentityAdmin(),
            )


class TestEmailSending:
    async def test_identity_override_email_is_sent(
        self,
        test_db_session: AsyncSession,
        test_redis_client: Redis | None,
        test_resend_client: AsyncClient,
        system_admin: User,
        mock_send_admin_identity_override_email,
        mock_users_delete_cache_system_admin,
    ) -> None:
        user = await make_user(test_db_session, role=UserRole.TEACHER)

        payload = UpdateUserIdentityAdmin(phone_number="+992111222333")

        await user_service_admin.update_user_identity(
            test_db_session,
            test_redis_client,
            test_resend_client,
            system_admin.id,
            user.id,
            payload,
        )

        mock_send_admin_identity_override_email.assert_called_once_with(
            test_resend_client, user.email
        )


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
        test_redis_client: Redis | None,
        test_resend_client: AsyncClient,
        system_admin: User,
        role: UserRole,
        phone_number: str,
    ) -> None:
        user = await make_user(test_db_session, role=role)

        await make_user(
            test_db_session, phone_number="+992888888888", role=UserRole.DIRECTOR
        )
        await make_user(
            test_db_session, phone_number="+992777777777", role=UserRole.TEACHER
        )
        await make_user(
            test_db_session, phone_number="+992666666666", role=UserRole.STUDENT
        )

        payload = UpdateUserIdentityAdmin(phone_number=phone_number)

        with pytest.raises(PhoneNumberAlreadyTakenError):
            await user_service_admin.update_user_identity(
                test_db_session,
                test_redis_client,
                test_resend_client,
                system_admin.id,
                user.id,
                payload,
            )


class TestCacheHandling:
    async def test_successful_updating_calls_delete_cache(
        self,
        test_db_session: AsyncSession,
        test_redis_client: Redis | None,
        test_resend_client: AsyncClient,
        system_admin: User,
        mock_send_admin_identity_override_email,
        mock_users_delete_cache_system_admin,
    ) -> None:
        user = await make_user(test_db_session, role=UserRole.TEACHER)

        payload = UpdateUserIdentityAdmin(first_name="updated-firstname")

        await user_service_admin.update_user_identity(
            test_db_session,
            test_redis_client,
            test_resend_client,
            system_admin.id,
            user.id,
            payload,
        )

        mock_users_delete_cache_system_admin.assert_called_once_with(
            test_redis_client,
            UsersCacheKeys.detailed_response_key_admin(user.id),
            UsersCacheKeys.detailed_response_key_staff(user.id),
            UsersCacheKeys.detailed_response_key_self(user.id),
        )
