import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.users.models import User
from school_management_system_lite.users.utils.enums import UserRole
from tests.conftest import make_auth_header
from tests.factories import make_user


class TestSuccess:
    async def test_successful_update(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
        mock_send_admin_identity_override_email,
        mock_users_delete_cache_system_admin,
    ) -> None:
        user = await make_user(test_db_session, role=UserRole.TEACHER)

        payload = {
            "first_name": "updated-firstname",
            "last_name": "updated-lastname",
            "middle_name": "updated-middlename",
            "address": "updated user address",
            "phone_number": "+992 111 222 333",
        }

        header = await make_auth_header(test_db_session, system_admin)

        response = await integration_client.patch(
            f"/admin/users/{user.id}/identity", headers=header, json=payload
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        await test_db_session.refresh(user)

        assert user.first_name == "Updated-Firstname"
        assert user.last_name == "Updated-Lastname"
        assert user.middle_name == "Updated-Middlename"
        assert user.address == "updated user address"
        assert user.phone_number == "+992111222333"


class TestAuth:
    async def test_unauthenticated_requests_raise_401(
        self, integration_client: AsyncClient
    ) -> None:

        response = await integration_client.patch(
            "/admin/users/9999999/identity",
            json={"first_name": "updated-firstname"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize(
        "role", [UserRole.DIRECTOR, UserRole.TEACHER, UserRole.STUDENT]
    )
    async def test_raises_403_on_non_admins(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        role: UserRole,
    ) -> None:
        user = await make_user(test_db_session, role=role)

        header = await make_auth_header(test_db_session, user)

        response = await integration_client.patch(
            "/admin/users/9999999/identity",
            headers=header,
            json={"first_name": "updated-firstname"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestEligibleUsers:
    async def test_updating_system_admin_is_prevented(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
    ) -> None:
        header = await make_auth_header(test_db_session, system_admin)

        response = await integration_client.patch(
            f"/admin/users/{system_admin.id}/identity",
            headers=header,
            json={"first_name": "updated-firstname"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_system_admin_cannot_update_another_system_admin(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
    ) -> None:
        user = await make_user(test_db_session, role=UserRole.SYSTEM_ADMIN)

        header = await make_auth_header(test_db_session, system_admin)

        response = await integration_client.patch(
            f"/admin/users/{user.id}/identity",
            headers=header,
            json={"first_name": "updated-firstname"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_raise_error_on_unknown_users(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
    ) -> None:
        header = await make_auth_header(test_db_session, system_admin)

        response = await integration_client.patch(
            "/admin/users/999999/identity",
            headers=header,
            json={"first_name": "updated-firstname"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


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
    async def test_raises_409_on_duplicate_phone_number(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
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

        header = await make_auth_header(test_db_session, system_admin)

        response = await integration_client.patch(
            f"/admin/users/{user.id}/identity",
            headers=header,
            json={"phone_number": phone_number},
        )

        assert response.status_code == status.HTTP_409_CONFLICT
