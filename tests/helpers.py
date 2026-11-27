from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.auth.repositories import (
    session as auth_session_repository,
)
from school_management_system_lite.auth.utils.tokens import create_access_token
from school_management_system_lite.core.config import get_settings
from school_management_system_lite.users.models.user import User

settings = get_settings()

async def make_auth_header(test_db_session: AsyncSession, user: User) -> dict[str, str]:
    user_session = await auth_session_repository.get_by_user_id(
        test_db_session, user.id
    )

    access_token = create_access_token(
        user_id=user.id,
        role=user.role,
        session_id=user_session.id,
        access_token_version=user_session.access_token_version,
        settings=get_settings(),
    )

    return {"Authorization": f"Bearer {access_token}"}
