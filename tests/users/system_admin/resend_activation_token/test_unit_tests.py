import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.auth.repositories import (
    activation as auth_activation_repository,
)
from school_management_system_lite.emails import repository as email_repository
from school_management_system_lite.emails.enums import EmailStatus, EmailType
from school_management_system_lite.users.models import User
from school_management_system_lite.users.services import (
    system_admin as user_service_admin,
)
from school_management_system_lite.users.utils.enums import UserStatus
from school_management_system_lite.users.utils.exceptions import (
    ResendActivationTokenDenied,
    UserNotFoundError,
)
from tests.factories import make_system_admin, make_teacher


class TestSuccess:
    async def test_successfully_resend_activation_token(
        self,
        test_db_session: AsyncSession,
        system_admin: User,
    ) -> None:
        user = await make_teacher(
            test_db_session,
            status=UserStatus.PENDING_ACTIVATION,
        )

        await user_service_admin.resend_activation_token(
            test_db_session,
            system_admin.id,
            user.id,
        )

        activation = await auth_activation_repository.get_by_user_id(
            test_db_session,
            user.id,
        )

        assert activation is not None
        assert activation.user_id == user.id
        assert activation.activation_token_hash is not None
        assert activation.activation_token_expires_at is not None

        email = await email_repository.get_by_recipient_email(
            test_db_session,
            user.email,
            email_type=frozenset({EmailType.ACCOUNT_ACTIVATION}),
            status=EmailStatus.PENDING,
        )

        assert len(email) == 1

        email = email[0]

        assert email.recipient_email == user.email
        assert email.subject is not None
        assert email.html_body is not None
        assert email.status == EmailStatus.PENDING
        assert email.email_type == EmailType.ACCOUNT_ACTIVATION
        assert email.triggered_by == system_admin.id

    async def test_successfully_replace_existing_activation_token(
        self,
        test_db_session: AsyncSession,
        system_admin: User,
    ) -> None:
        user = await make_teacher(
            test_db_session,
            status=UserStatus.PENDING_ACTIVATION,
        )

        old_activation = await auth_activation_repository.get_by_user_id(
            test_db_session, user.id
        )
        old_activation_token_hash = old_activation.activation_token_hash

        await user_service_admin.resend_activation_token(
            test_db_session,
            system_admin.id,
            user.id,
        )

        activation = await auth_activation_repository.get_by_user_id(
            test_db_session,
            user.id,
        )

        assert activation is not None
        assert activation.user_id == user.id
        assert activation.activation_token_hash != old_activation_token_hash
        assert activation.activation_token_expires_at is not None

        email = await email_repository.get_by_recipient_email(
            test_db_session,
            user.email,
            email_type=frozenset({EmailType.ACCOUNT_ACTIVATION}),
            status=EmailStatus.PENDING,
        )

        assert len(email) == 1


class TestEligibleUsers:
    async def test_resending_activation_token_for_system_admin_is_prevented(
        self,
        test_db_session: AsyncSession,
        system_admin: User,
    ) -> None:
        with pytest.raises(UserNotFoundError):
            await user_service_admin.resend_activation_token(
                test_db_session,
                system_admin.id,
                system_admin.id,
            )

    async def test_resending_activation_token_for_another_system_admin_is_prevented(
        self,
        test_db_session: AsyncSession,
        system_admin: User,
    ) -> None:
        user = await make_system_admin(test_db_session)

        with pytest.raises(UserNotFoundError):
            await user_service_admin.resend_activation_token(
                test_db_session,
                system_admin.id,
                user.id,
            )

    async def test_raise_error_on_unknown_users(
        self,
        test_db_session: AsyncSession,
        system_admin: User,
    ) -> None:
        with pytest.raises(UserNotFoundError):
            await user_service_admin.resend_activation_token(
                test_db_session,
                system_admin.id,
                999999,
            )


class TestEligibleStatuses:
    @pytest.mark.parametrize(
        "status",
        [
            UserStatus.ACTIVE,
            UserStatus.INACTIVE,
            UserStatus.EXPELLED,
            UserStatus.GRADUATED,
            UserStatus.WITHDRAWN,
        ],
    )
    async def test_raise_error_for_non_pending_activation_accounts(
        self,
        test_db_session: AsyncSession,
        system_admin: User,
        status: UserStatus,
    ) -> None:
        user = await make_teacher(
            test_db_session,
            status=status,
        )

        with pytest.raises(ResendActivationTokenDenied):
            await user_service_admin.resend_activation_token(
                test_db_session,
                system_admin.id,
                user.id,
            )
