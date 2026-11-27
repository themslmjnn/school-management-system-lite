import itertools

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.auth.models.activation import UserActivation
from school_management_system_lite.core.enums import OrderBy
from school_management_system_lite.database.base import Base
from school_management_system_lite.emails import repository as email_repository
from school_management_system_lite.emails.models import Email
from school_management_system_lite.users.models.user import User
from school_management_system_lite.users.repositories import (
    base as user_base_repository,
)
from school_management_system_lite.users.utils.enums import UserRole, UserStatus
from school_management_system_lite.users.utils.exceptions import (
    EmailAlreadyTakenError,
    PhoneNumberAlreadyTakenError,
)
from tests.conftest import make_auth_header
from tests.factories import make_create_user_payload, make_user

CREATE_USER_URL = "/admin/users"

CREATABLE_ROLES = (UserRole.DIRECTOR, UserRole.TEACHER, UserRole.STUDENT)

EXISTING_AND_NEW_ROLE_PAIRS = [
    pytest.param(
        existing_role,
        new_role,
        id=f"{existing_role.name.lower()}_exists-{new_role.name.lower()}_new",
    )
    for existing_role, new_role in itertools.product(CREATABLE_ROLES, repeat=2)
]


async def _count_rows(db_session: AsyncSession, model: type[Base]) -> int:
    return await db_session.scalar(select(func.count()).select_from(model)) or 0


class TestSuccess:
    @pytest.mark.parametrize(
        "role", CREATABLE_ROLES, ids=[role.name.lower() for role in CREATABLE_ROLES]
    )
    async def test_create_user_valid_payload_returns_201_with_user_body(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
        role: UserRole,
    ) -> None:
        payload = make_create_user_payload(role=role)
        headers = await make_auth_header(test_db_session, system_admin)

        response = await integration_client.post(
            CREATE_USER_URL, headers=headers, json=payload.model_dump(mode="json")
        )

        assert response.status_code == status.HTTP_201_CREATED

        response_body = response.json()

        assert response_body["id"] is not None
        assert response_body["first_name"] == payload.first_name
        assert response_body["last_name"] == payload.last_name
        assert response_body["middle_name"] == payload.middle_name
        assert response_body["date_of_birth"] == payload.date_of_birth.isoformat()
        assert response_body["address"] == payload.address
        assert response_body["phone_number"] == payload.phone_number
        assert response_body["email"] == payload.email
        assert response_body["role"] == role
        assert response_body["status"] == UserStatus.PENDING_ACTIVATION
        assert response_body["created_at"] is not None
        assert "password_hash" not in response_body

    async def test_create_user_valid_payload_records_calling_admin_as_creator(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
    ) -> None:
        payload = make_create_user_payload()
        headers = await make_auth_header(test_db_session, system_admin)

        response = await integration_client.post(
            CREATE_USER_URL, headers=headers, json=payload.model_dump(mode="json")
        )

        assert response.status_code == status.HTTP_201_CREATED

        created_user = await user_base_repository.get_by_id(
            test_db_session, response.json()["id"]
        )
        email_rows = await email_repository.get_by_recipient_email(
            test_db_session, payload.email, order_by=OrderBy.DESC
        )

        assert created_user is not None
        assert created_user.created_by == system_admin.id
        assert len(email_rows) == 1
        assert email_rows[0].triggered_by == system_admin.id


class TestAuth:
    async def test_create_user_without_token_returns_401(
        self, integration_client: AsyncClient
    ) -> None:
        payload = make_create_user_payload()

        response = await integration_client.post(
            CREATE_USER_URL, json=payload.model_dump(mode="json")
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize(
        "role", CREATABLE_ROLES, ids=[role.name.lower() for role in CREATABLE_ROLES]
    )
    async def test_create_user_non_admin_role_returns_403(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        role: UserRole,
    ) -> None:
        non_admin_user = await make_user(test_db_session, role=role)
        headers = await make_auth_header(test_db_session, non_admin_user)
        payload = make_create_user_payload()

        response = await integration_client.post(
            CREATE_USER_URL, headers=headers, json=payload.model_dump(mode="json")
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestDBConstraints:
    @pytest.mark.parametrize(["existing_role", "new_role"], EXISTING_AND_NEW_ROLE_PAIRS)
    async def test_create_user_duplicate_phone_number_returns_409_with_error_code(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
        existing_role: UserRole,
        new_role: UserRole,
    ) -> None:
        existing_user = await make_user(test_db_session, role=existing_role)
        payload = make_create_user_payload(
            role=new_role, phone_number=existing_user.phone_number
        )
        headers = await make_auth_header(test_db_session, system_admin)

        response = await integration_client.post(
            CREATE_USER_URL, headers=headers, json=payload.model_dump(mode="json")
        )

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.json()["error_code"] == PhoneNumberAlreadyTakenError.error_code

    @pytest.mark.parametrize(["existing_role", "new_role"], EXISTING_AND_NEW_ROLE_PAIRS)
    async def test_create_user_duplicate_email_returns_409_with_error_code(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
        existing_role: UserRole,
        new_role: UserRole,
    ) -> None:
        existing_user = await make_user(test_db_session, role=existing_role)
        payload = make_create_user_payload(role=new_role, email=existing_user.email)
        headers = await make_auth_header(test_db_session, system_admin)

        response = await integration_client.post(
            CREATE_USER_URL, headers=headers, json=payload.model_dump(mode="json")
        )

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.json()["error_code"] == EmailAlreadyTakenError.error_code

    @pytest.mark.parametrize(
        ["duplicated_field", "to_formatted_variant", "expected_error_code"],
        [
            pytest.param(
                "email",
                lambda value: f"  {value.upper()}  ",
                EmailAlreadyTakenError.error_code,
                id="email_uppercase_and_padded",
            ),
            pytest.param(
                "phone_number",
                lambda value: f"{value[:4]} {value[4:7]} {value[7:10]} {value[10:]}",
                PhoneNumberAlreadyTakenError.error_code,
                id="phone_number_with_spaces",
            ),
        ],
    )
    async def test_create_user_duplicate_with_formatting_difference_returns_409(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
        duplicated_field: str,
        to_formatted_variant,
        expected_error_code: str,
    ) -> None:
        existing_user = await make_user(test_db_session)
        request_body = make_create_user_payload().model_dump(mode="json")
        request_body[duplicated_field] = to_formatted_variant(
            getattr(existing_user, duplicated_field)
        )
        headers = await make_auth_header(test_db_session, system_admin)

        response = await integration_client.post(
            CREATE_USER_URL, headers=headers, json=request_body
        )

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.json()["error_code"] == expected_error_code


class TestRoleRestrictions:
    async def test_create_user_system_admin_role_returns_422_and_creates_nothing(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
    ) -> None:
        request_body = make_create_user_payload().model_dump(mode="json")
        request_body["role"] = UserRole.SYSTEM_ADMIN.value
        headers = await make_auth_header(test_db_session, system_admin)
        models = (User, UserActivation, Email)
        row_counts_before = [
            await _count_rows(test_db_session, model) for model in models
        ]

        response = await integration_client.post(
            CREATE_USER_URL, headers=headers, json=request_body
        )

        row_counts_after = [
            await _count_rows(test_db_session, model) for model in models
        ]

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        assert row_counts_after == row_counts_before
