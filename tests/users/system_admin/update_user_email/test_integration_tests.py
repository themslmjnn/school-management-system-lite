import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.users.models.user import User
from school_management_system_lite.utils.enums import UserRole
from tests.conftest import make_auth_header
from tests.factories import (
    make_director,
    make_student,
    make_system_admin,
    make_teacher,
    make_user,
)


class TestSuccess:
    async def test_successful_update(
        self,
        test_db_session: AsyncSession,
        client: AsyncClient,
        system_admin: User,
    ) -> None:
        user = await make_teacher(test_db_session)

        header = await make_auth_header(test_db_session, system_admin)

        response = await client.patch(
            f"/admin/users/{user.id}/email",
            headers=header,
            json={"email": "updated_email@gmail.com"},
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        await test_db_session.refresh(user)

        assert user.email == "updated_email@gmail.com"


class TestAuth:
    async def test_unauthenticated_requests_raise_401(
        self, client: AsyncClient
    ) -> None:
        response = await client.patch(
            "/admin/users/9999999/email",
            json={"email": "updated_email@gmail.com"},
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

        header = await make_auth_header(test_db_session, user)

        response = await client.patch(
            "/admin/users/9999999/email",
            headers=header,
            json={"email": "updated_email@gmail.com"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestEligibleUsers:
    async def test_updating_system_admin_is_prevented(
        self, test_db_session: AsyncSession, client: AsyncClient, system_admin: User
    ) -> None:
        header = await make_auth_header(test_db_session, system_admin)

        response = await client.patch(
            f"/admin/users/{system_admin.id}/email",
            headers=header,
            json={"email": "updated_email@gmail.com"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_system_admin_cannot_update_another_system_admin(
        self, test_db_session: AsyncSession, client: AsyncClient, system_admin: User
    ) -> None:
        user = await make_system_admin(test_db_session)

        header = await make_auth_header(test_db_session, system_admin)

        response = await client.patch(
            f"/admin/users/{user.id}/email",
            headers=header,
            json={"email": "updated_email@gmail.com"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_raise_error_on_unknown_users(
        self, test_db_session: AsyncSession, client: AsyncClient, system_admin: User
    ) -> None:
        header = await make_auth_header(test_db_session, system_admin)

        response = await client.patch(
            "/admin/users/999999/email",
            headers=header,
            json={"email": "updated_email@gmail.com"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


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
    async def test_raises_409_on_duplicate_email(
        self,
        test_db_session: AsyncSession,
        client: AsyncClient,
        system_admin: User,
        role: UserRole,
        email: str,
    ) -> None:
        user = await make_user(test_db_session, role=role)

        await make_director(test_db_session, email="director_email@gmail.com")
        await make_teacher(test_db_session, email="teacher_email@gmail.com")
        await make_student(test_db_session, email="student_email@gmail.com")

        header = await make_auth_header(test_db_session, system_admin)

        response = await client.patch(
            f"/admin/users/{user.id}/email",
            headers=header,
            json={"email": email},
        )

        assert response.status_code == status.HTTP_409_CONFLICT
