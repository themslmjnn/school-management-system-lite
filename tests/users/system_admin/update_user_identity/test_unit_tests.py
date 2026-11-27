import itertools
from collections.abc import Awaitable, Callable
from unittest.mock import AsyncMock

import pytest
from pytest_mock import MockerFixture
from redis.asyncio import Redis
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.core.redis.cache_keys import UsersCacheKeys
from school_management_system_lite.users.models.user import User
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

UNKNOWN_USER_ID = 999999

IDENTITY_FIELDS = (
    "first_name",
    "last_name",
    "middle_name",
    "address",
    "phone_number",
)

NON_ADMIN_ROLES = (UserRole.DIRECTOR, UserRole.TEACHER, UserRole.STUDENT)

EXISTING_AND_TARGET_ROLE_PAIRS = [
    pytest.param(
        existing_role,
        target_role,
        id=f"{existing_role.name.lower()}_exists-{target_role.name.lower()}_updated",
    )
    for existing_role, target_role in itertools.product(NON_ADMIN_ROLES, repeat=2)
]

UpdateIdentity = Callable[[int, UpdateUserIdentityAdmin], Awaitable[None]]


@pytest.fixture
def update_identity(
    test_db_session: AsyncSession,
    test_redis_client: Redis | None,
    test_resend_client: AsyncMock,
    system_admin: User,
) -> UpdateIdentity:
    async def _update_identity(user_id: int, payload: UpdateUserIdentityAdmin) -> None:
        await user_service_admin.update_user_identity(
            test_db_session,
            test_redis_client,
            test_resend_client,
            system_admin.id,
            user_id,
            payload,
        )

    return _update_identity


class TestSuccess:
    async def test_update_identity_with_some_fields_saves_only_sent_fields(
        self,
        test_db_session: AsyncSession,
        update_identity: UpdateIdentity,
        teacher: User,
        mocker: MockerFixture,
    ) -> None:
        original_last_name = teacher.last_name
        original_middle_name = teacher.middle_name
        original_address = teacher.address
        commit_spy = mocker.spy(test_db_session, "commit")

        await update_identity(
            teacher.id,
            UpdateUserIdentityAdmin(
                first_name="Updated-Firstname", phone_number="+992111222333"
            ),
        )

        commit_spy.assert_called_once()

        await test_db_session.refresh(teacher)

        assert teacher.first_name == "Updated-Firstname"
        assert teacher.phone_number == "+992111222333"
        assert teacher.last_name == original_last_name
        assert teacher.middle_name == original_middle_name
        assert teacher.address == original_address

    @pytest.mark.parametrize(
        "sent_fields",
        [(), IDENTITY_FIELDS],
        ids=["empty_payload", "current_values"],
    )
    async def test_update_identity_without_new_values_has_no_side_effects(
        self,
        test_db_session: AsyncSession,
        update_identity: UpdateIdentity,
        teacher: User,
        mocker: MockerFixture,
        mock_send_admin_identity_override_email: AsyncMock,
        mock_users_delete_cache_system_admin: AsyncMock,
        sent_fields: tuple[str, ...],
    ) -> None:
        payload = UpdateUserIdentityAdmin(
            **{field: getattr(teacher, field) for field in sent_fields}
        )
        commit_spy = mocker.spy(test_db_session, "commit")

        await update_identity(teacher.id, payload)

        commit_spy.assert_not_called()

        mock_users_delete_cache_system_admin.assert_not_awaited()
        mock_send_admin_identity_override_email.assert_not_called()


class TestEligibleUsers:
    async def test_update_identity_with_unknown_user_raises_user_not_found(
        self,
        test_db_session: AsyncSession,
        update_identity: UpdateIdentity,
        mocker: MockerFixture,
    ) -> None:
        commit_spy = mocker.spy(test_db_session, "commit")

        with pytest.raises(UserNotFoundError):
            await update_identity(
                UNKNOWN_USER_ID,
                UpdateUserIdentityAdmin(first_name="Updated-Firstname"),
            )

        commit_spy.assert_not_called()

    async def test_update_identity_of_own_admin_account_raises_user_not_found(
        self,
        test_db_session: AsyncSession,
        update_identity: UpdateIdentity,
        system_admin: User,
    ) -> None:
        original_first_name = system_admin.first_name

        with pytest.raises(UserNotFoundError):
            await update_identity(
                system_admin.id,
                UpdateUserIdentityAdmin(first_name="Updated-Firstname"),
            )

        await test_db_session.refresh(system_admin)
        assert system_admin.first_name == original_first_name

    async def test_update_identity_of_another_admin_raises_user_not_found(
        self,
        test_db_session: AsyncSession,
        update_identity: UpdateIdentity,
    ) -> None:
        other_admin = await make_user(test_db_session, role=UserRole.SYSTEM_ADMIN)
        original_first_name = other_admin.first_name

        with pytest.raises(UserNotFoundError):
            await update_identity(
                other_admin.id,
                UpdateUserIdentityAdmin(first_name="Updated-Firstname"),
            )

        await test_db_session.refresh(other_admin)
        assert other_admin.first_name == original_first_name


class TestEmailSending:
    async def test_update_identity_with_new_value_sends_email_to_user_once(
        self,
        update_identity: UpdateIdentity,
        teacher: User,
        test_resend_client: AsyncMock,
        mock_send_admin_identity_override_email: AsyncMock,
    ) -> None:
        await update_identity(
            teacher.id, UpdateUserIdentityAdmin(first_name="Updated-Firstname")
        )

        mock_send_admin_identity_override_email.assert_called_once_with(
            test_resend_client, teacher.email
        )


class TestCacheHandling:
    async def test_update_identity_with_new_value_deletes_user_cache_keys(
        self,
        update_identity: UpdateIdentity,
        teacher: User,
        test_redis_client: Redis | None,
        mock_users_delete_cache_system_admin: AsyncMock,
    ) -> None:
        await update_identity(
            teacher.id, UpdateUserIdentityAdmin(first_name="Updated-Firstname")
        )

        mock_users_delete_cache_system_admin.assert_awaited_once_with(
            test_redis_client,
            UsersCacheKeys.detailed_response_key_admin(teacher.id),
            UsersCacheKeys.detailed_response_key_staff(teacher.id),
            UsersCacheKeys.detailed_response_key_self(teacher.id),
        )


class TestDBConstraints:
    @pytest.mark.parametrize(
        ["existing_role", "target_role"], EXISTING_AND_TARGET_ROLE_PAIRS
    )
    async def test_update_identity_with_taken_phone_raises_phone_taken_error(
        self,
        test_db_session: AsyncSession,
        update_identity: UpdateIdentity,
        mock_send_admin_identity_override_email: AsyncMock,
        mock_users_delete_cache_system_admin: AsyncMock,
        existing_role: UserRole,
        target_role: UserRole,
    ) -> None:
        existing_user = await make_user(test_db_session, role=existing_role)
        target_user = await make_user(test_db_session, role=target_role)

        await test_db_session.commit()

        original_first_name = target_user.first_name
        original_phone_number = target_user.phone_number
        payload = UpdateUserIdentityAdmin(
            first_name="Updated-Firstname",
            phone_number=existing_user.phone_number,
        )

        with pytest.raises(PhoneNumberAlreadyTakenError):
            await update_identity(target_user.id, payload)

        await test_db_session.refresh(target_user)

        assert target_user.first_name == original_first_name
        assert target_user.phone_number == original_phone_number

        mock_users_delete_cache_system_admin.assert_not_awaited()
        mock_send_admin_identity_override_email.assert_not_called()

    async def test_update_identity_with_other_integrity_error_rolls_back_and_reraises(
        self,
        test_db_session: AsyncSession,
        update_identity: UpdateIdentity,
        teacher: User,
        mocker: MockerFixture,
        mock_send_admin_identity_override_email: AsyncMock,
        mock_users_delete_cache_system_admin: AsyncMock,
    ) -> None:
        await test_db_session.commit()

        integrity_error = IntegrityError(
            "UPDATE users", {}, Exception("other constraint")
        )

        mocker.patch.object(test_db_session, "commit", side_effect=integrity_error)

        rollback_spy = mocker.spy(test_db_session, "rollback")

        with pytest.raises(IntegrityError) as raised_error:
            await update_identity(
                teacher.id, UpdateUserIdentityAdmin(first_name="Updated-Firstname")
            )

        assert raised_error.value is integrity_error

        rollback_spy.assert_called_once()

        mock_users_delete_cache_system_admin.assert_not_awaited()
        mock_send_admin_identity_override_email.assert_not_called()
