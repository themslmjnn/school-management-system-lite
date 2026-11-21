import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.users.models.users import User
from school_management_system_lite.users.utils.enums import UserRole
from tests.conftest import make_auth_header
from tests.factories import make_user


class TestSuccess:
    async def test_returns_correct_paginated_response(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
    ) -> None:
        await make_user(test_db_session, role=UserRole.TEACHER)

        header = await make_auth_header(test_db_session, system_admin)

        response = await integration_client.get(
            "/admin/users/staff?sort_by=created_at&order=desc&skip=0&limit=10",
            headers=header,
        )

        response = response.json()

        assert response["items"] is not None
        assert response["total"] == 1
        assert response["skip"] == 0
        assert response["limit"] == 10
        assert response["has_more"] is False

    async def test_list_staff_returns_correct_fields(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
    ) -> None:
        director = await make_user(test_db_session, role=UserRole.DIRECTOR)

        header = await make_auth_header(test_db_session, system_admin)

        response = await integration_client.get(
            "/admin/users/staff?sort_by=created_at&order=desc&skip=0&limit=10",
            headers=header,
        )

        response = response.json()

        assert response["items"][0]["id"] == director.id
        assert response["items"][0]["first_name"] == director.first_name
        assert response["items"][0]["last_name"] == director.last_name
        assert response["items"][0]["middle_name"] == director.middle_name
        assert response["items"][0]["role"] == director.role
        assert response["items"][0]["status"] == director.status

    async def test_applies_query_parameters(
        self,
        test_db_session: AsyncSession,
        integration_client: AsyncClient,
        system_admin: User,
    ) -> None:
        await make_user(
            test_db_session,
            role=UserRole.DIRECTOR,
            first_name="Shavkat",
        )
        matching_teacher = await make_user(
            test_db_session,
            role=UserRole.TEACHER,
            first_name="Umar",
        )
        await make_user(
            test_db_session,
            role=UserRole.TEACHER,
            first_name="Shavkat",
        )

        header = await make_auth_header(test_db_session, system_admin)

        response = await integration_client.get(
            "/admin/users/staff",
            params={
                "first_name": "umar",
                "sort_by": "first_name",
                "order": "asc",
                "skip": 0,
                "limit": 1,
            },
            headers=header,
        )

        assert response.status_code == status.HTTP_200_OK

        response_data = response.json()

        assert response_data["total"] == 1
        assert response_data["skip"] == 0
        assert response_data["limit"] == 1
        assert response_data["has_more"] is False
        assert len(response_data["items"]) == 1

        assert response_data["items"][0]["id"] == matching_teacher.id
        assert response_data["items"][0]["first_name"] == "Umar"


class TestAuth:
    async def test_unauthenticated_requests_raise_401(
        self,
        integration_client: AsyncClient,
    ) -> None:
        response = await integration_client.get(
            "/admin/users/staff?sort_by=created_at&order=desc&skip=0&limit=10"
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

        response = await integration_client.get(
            "/admin/users/staff?sort_by=created_at&order=desc&skip=0&limit=10",
            headers=header,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
