import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.users.models.user import User
from school_management_system_lite.utils.enums import UserRole
from tests.conftest import make_auth_header
from tests.factories import make_director, make_student, make_teacher, make_user


class TestSuccess:
    async def test_successful_update(
        self,
        test_db_session: AsyncSession,
        client: AsyncClient,
        system_admin: User,
        mock_send_admin_identity_override_email,
    ) -> None:
        user = await make_teacher(test_db_session)

        payload = {
            "first_name": "updated-first-name",
            "last_name": "updated-last-name",
            "middle_name": "updated-middle-name",
            "address": "updated address",
            "phone_number": "+992 111 222 333",
        }

        header = await make_auth_header(test_db_session, system_admin)

        response = await client.patch(
            f"/admin/users/{user.id}/identity", headers=header, json=payload
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        await test_db_session.refresh(user)

        assert user.first_name == "Updated-First-Name"
        assert user.last_name == "Updated-Last-Name"
        assert user.middle_name == "Updated-Middle-Name"
        assert user.address == "updated address"
        assert user.phone_number == "+992111222333"

    async def test_ignores_unset_fields(
        self,
        test_db_session: AsyncSession,
        client: AsyncClient,
        system_admin: User,
        mock_send_admin_identity_override_email,
    ) -> None:
        user = await make_teacher(test_db_session)

        payload = {
            "first_name": "updated-first-name",
            "phone_number": "+992 111 222 333",
        }

        header = await make_auth_header(test_db_session, system_admin)

        response = await client.patch(
            f"/admin/users/{user.id}/identity", headers=header, json=payload
        )

        assert response.status_code == 204

        await test_db_session.refresh(user)

        assert user.first_name == "Updated-First-Name"
        assert user.phone_number == "+992111222333"


class TestAuth:
    async def test_unauthenticated_requests_raise_401(
        self, client: AsyncClient
    ) -> None:
        payload = {
            "first_name": "updated-first-name",
            "phone_number": "+992 111 222 333",
        }

        response = await client.patch(
            "/admin/users/9999999/identity",
            json=payload,
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize(
        "role", [UserRole.DIRECTOR, UserRole.TEACHER, UserRole.STUDENT]
    )
    async def test_raises_403_on_non_admins(
        self,
        test_db_session: AsyncSession,
        client: AsyncClient,
        role: UserRole,
    ) -> None:
        user = await make_user(test_db_session, role=role)

        payload = {
            "first_name": "updated-first-name",
            "phone_number": "+992 111 222 333",
        }

        header = await make_auth_header(test_db_session, user)

        response = await client.patch(
            "/admin/users/9999999/identity",
            headers=header,
            json=payload,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


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
        client: AsyncClient,
        system_admin: User,
        role: UserRole,
        phone_number: str,
    ) -> None:
        user = await make_user(test_db_session, role=role)

        await make_director(test_db_session, phone_number="+992888888888")
        await make_teacher(test_db_session, phone_number="+992777777777")
        await make_student(test_db_session, phone_number="+992666666666")

        payload = {"phone_number": phone_number}

        header = await make_auth_header(test_db_session, system_admin)

        response = await client.patch(
            f"/admin/users/{user.id}/identity",
            headers=header,
            json=payload,
        )

        assert response.status_code == status.HTTP_409_CONFLICT
