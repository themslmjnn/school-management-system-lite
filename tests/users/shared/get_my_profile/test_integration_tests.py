from datetime import date

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.auth.utils.tokens import create_access_token
from school_management_system_lite.core.config import get_settings
from school_management_system_lite.users.models import User
from school_management_system_lite.users.utils.enums import UserRole
from tests.conftest import make_auth_header
from tests.factories import make_user


class TestSuccess:
    @pytest.mark.parametrize(
        ["role", "date_of_birth", "phone_number", "email"],
        [
            (
                UserRole.SYSTEM_ADMIN,
                date(1995, 5, 1),
                "+992777777777",
                "valid_admin_email@gmail.com",
            ),
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
        ],
    )
    async def test_correct_shape(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        role: UserRole,
        date_of_birth: date,
        phone_number: str,
        email: str,
    ) -> None:
        user = await make_user(
            test_db_session,
            role=role,
            date_of_birth=date_of_birth,
            phone_number=phone_number,
            email=email,
        )

        header = await make_auth_header(test_db_session, user)

        response = await integration_client.get("/users/me", headers=header)

        response = response.json()

        assert response["id"] == user.id
        assert response["first_name"] == user.first_name
        assert response["last_name"] == user.last_name
        assert response["middle_name"] == user.middle_name
        assert response["date_of_birth"] == user.date_of_birth.isoformat()
        assert response["phone_number"] == user.phone_number
        assert response["email"] == user.email
        assert response["created_at"] is not None


class TestAuth:
    async def test_unauthenticated_requests_raise_401(
        self, integration_client: AsyncClient
    ) -> None:
        response = await integration_client.get(
            "/users/me",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_raises_403_on_students(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
    ) -> None:
        user = await make_user(test_db_session, role=UserRole.STUDENT)

        header = await make_auth_header(test_db_session, user)

        response = await integration_client.get(
            "/users/me",
            headers=header,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
