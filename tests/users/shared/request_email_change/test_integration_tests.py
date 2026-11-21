from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.users.utils.enums import UserRole
from tests.conftest import make_auth_header
from tests.factories import make_user


class TestSuccess:
    async def test_successfully_requested_email_change(
        self, test_db_session: AsyncSession, integration_client: AsyncClient
    ) -> None:
        user = await make_user(test_db_session, role=UserRole.STUDENT)

        header = await make_auth_header(test_db_session, user)

        response = await integration_client.post(
            "/users/me/email", headers=header, json={"new_email": "new_email@gmail.com"}
        )

        assert response.status_code == status.HTTP_202_ACCEPTED


class TestAuth:
    async def test_unauthenticated_requests_raise_401(
        self, integration_client: AsyncClient
    ) -> None:
        response = await integration_client.post("/users/me/email")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestDBConstraints:
    async def test_raises_on_duplicate_emails(
        self, test_db_session: AsyncSession, integration_client: AsyncClient
    ) -> None:
        await make_user(
            test_db_session, role=UserRole.STUDENT, email="student_email@gmail.com"
        )
        user = await make_user(test_db_session, role=UserRole.STUDENT)

        header = await make_auth_header(test_db_session, user)

        response = await integration_client.post(
            "/users/me/email",
            headers=header,
            json={"new_email": "student_email@gmail.com"},
        )

        assert response.status_code == status.HTTP_409_CONFLICT
