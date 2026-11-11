from datetime import date

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.users.models import User
from school_management_system_lite.users.schemas.system_admin import CreateUserAdmin
from school_management_system_lite.users.utils.enums import UserRole, UserStatus
from tests.conftest import make_auth_header
from tests.factories import make_director, make_student, make_teacher, make_user

ENDPOINT = "/admin/users"


class TestSuccess:
    async def test_successful_staff_registration(
        self,
        test_db_session: AsyncSession,
        client: AsyncClient,
        system_admin: User,
        valid_user_payload: CreateUserAdmin,
    ) -> None:
        valid_user_payload.date_of_birth = date(2000, 5, 1)
        valid_user_payload.phone_number = "+992111222111"
        valid_user_payload.email = "valid_staff_email@gmail.com"
        valid_user_payload.role = UserRole.TEACHER

        header = await make_auth_header(test_db_session, system_admin)

        response = await client.post(
            ENDPOINT,
            headers=header,
            json=valid_user_payload.model_dump(mode="json"),
        )

        assert response.status_code == status.HTTP_201_CREATED

        response = response.json()

        assert response["id"] is not None
        assert response["first_name"] == "Valid-First-Name"
        assert response["last_name"] == "Valid-Last-Name"
        assert response["middle_name"] is None
        assert response["date_of_birth"] == "2000-05-01"
        assert response["address"] == "valid_address"
        assert response["phone_number"] == "+992111222111"
        assert response["email"] == "valid_staff_email@gmail.com"
        assert response["role"] == UserRole.TEACHER
        assert response["status"] == UserStatus.PENDING_ACTIVATION
        assert response["created_at"] is not None

    async def test_successful_student_registration(
        self,
        test_db_session: AsyncSession,
        client: AsyncClient,
        system_admin: User,
        valid_user_payload: CreateUserAdmin,
    ) -> None:
        header = await make_auth_header(test_db_session, system_admin)

        response = await client.post(
            ENDPOINT,
            headers=header,
            json=valid_user_payload.model_dump(mode="json"),
        )

        assert response.status_code == status.HTTP_201_CREATED

        response = response.json()

        assert response["id"] is not None
        assert response["first_name"] == "Valid-First-Name"
        assert response["last_name"] == "Valid-Last-Name"
        assert response["middle_name"] is None
        assert response["date_of_birth"] == "2008-05-01"
        assert response["address"] == "valid_address"
        assert response["phone_number"] == "+992222111222"
        assert response["email"] == "valid_student_email@gmail.com"
        assert response["role"] == UserRole.STUDENT
        assert response["status"] == UserStatus.PENDING_ACTIVATION
        assert response["created_at"] is not None


class TestAuth:
    async def test_unauthenticated_requests_raise_401(
        self, client: AsyncClient, valid_user_payload: CreateUserAdmin
    ) -> None:
        response = await client.post(
            ENDPOINT,
            json=valid_user_payload.model_dump(mode="json"),
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize(
        "role", [UserRole.DIRECTOR, UserRole.TEACHER, UserRole.STUDENT]
    )
    async def test_raises_403_on_non_admins(
        self,
        test_db_session: AsyncSession,
        client: AsyncClient,
        valid_user_payload: CreateUserAdmin,
        role: UserRole,
    ) -> None:
        user = await make_user(test_db_session, role=role)

        header = await make_auth_header(test_db_session, user)

        response = await client.post(
            ENDPOINT,
            headers=header,
            json=valid_user_payload.model_dump(mode="json"),
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
        valid_user_payload: CreateUserAdmin,
        role: UserRole,
        phone_number: str,
    ) -> None:
        await make_director(test_db_session, phone_number="+992888888888")
        await make_teacher(test_db_session, phone_number="+992777777777")
        await make_student(test_db_session, phone_number="+992666666666")

        valid_user_payload.phone_number = phone_number
        valid_user_payload.role = role

        if role != UserRole.STUDENT:
            valid_user_payload.date_of_birth = date(2000, 5, 1)

        header = await make_auth_header(test_db_session, system_admin)

        response = await client.post(
            ENDPOINT,
            headers=header,
            json=valid_user_payload.model_dump(mode="json"),
        )

        assert response.status_code == status.HTTP_409_CONFLICT

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
    async def test_raises_409_on_duplicate_email(
        self,
        test_db_session: AsyncSession,
        client: AsyncClient,
        system_admin: User,
        valid_user_payload: CreateUserAdmin,
        role: UserRole,
        email: str,
    ) -> None:
        await make_director(test_db_session, email="director_email@gmail.com")
        await make_teacher(test_db_session, email="teacher_email@gmail.com")
        await make_student(test_db_session, email="student_email@gmail.com")

        valid_user_payload.role = role
        valid_user_payload.email = email

        if role != UserRole.STUDENT:
            valid_user_payload.date_of_birth = date(2000, 5, 1)

        header = await make_auth_header(test_db_session, system_admin)

        response = await client.post(
            ENDPOINT,
            headers=header,
            json=valid_user_payload.model_dump(mode="json"),
        )

        assert response.status_code == status.HTTP_409_CONFLICT
