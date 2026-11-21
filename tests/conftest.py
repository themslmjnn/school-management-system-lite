from collections.abc import AsyncIterator, Iterator
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy import NullPool, create_engine
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
)

from school_management_system_lite.auth.repositories import (
    session as auth_session_repository,
)
from school_management_system_lite.auth.utils.tokens import create_access_token
from school_management_system_lite.core.config import get_settings
from school_management_system_lite.core.dependencies.database import get_db_session
from school_management_system_lite.core.dependencies.resend import get_resend_client
from school_management_system_lite.core.redis.client import build_redis_client
from school_management_system_lite.database.base import Base
from school_management_system_lite.main import app
from school_management_system_lite.users.models.users import User
from school_management_system_lite.users.utils.enums import UserRole
from tests.factories import make_user

settings = get_settings()

SYNC_DB_URL = URL.create(
    "postgresql+psycopg2",
    username=settings.DB_USER,
    password=settings.DB_PASSWORD.get_secret_value(),
    host=settings.DB_HOST,
    port=settings.DB_PORT,
    database=settings.DB_NAME,
)

test_engine = create_async_engine(
    url=settings.DATABASE_URL,
    poolclass=NullPool,
)


@pytest.fixture(scope="session", autouse=True)
def _guard_test_environment() -> None:
    if settings.ENVIRONMENT != "test":
        pytest.exit(
            f"Refusing to run tests: ENVIRONMENT is "
            f"'{settings.ENVIRONMENT}', expected 'test'",
            returncode=2,
        )


@pytest.fixture(scope="session")
def create_tables(_guard_test_environment: None) -> Iterator[None]:
    sync_engine = create_engine(SYNC_DB_URL, poolclass=NullPool)

    try:
        Base.metadata.create_all(sync_engine)

        yield

    finally:
        Base.metadata.drop_all(sync_engine)

        sync_engine.dispose()


@pytest_asyncio.fixture
async def test_db_session(
    create_tables: None,
) -> AsyncIterator[AsyncSession]:
    async with test_engine.connect() as conn:
        outer = await conn.begin()

        session = AsyncSession(
            bind=conn,
            expire_on_commit=False,
            autoflush=False,
            join_transaction_mode="create_savepoint",
        )

        async def override_get_db_session() -> AsyncIterator[AsyncSession]:
            yield session

        app.dependency_overrides[get_db_session] = override_get_db_session

        try:
            yield session

        finally:
            app.dependency_overrides.pop(get_db_session, None)

            await session.close()
            await outer.rollback()


@pytest_asyncio.fixture
async def test_redis_client() -> AsyncIterator[Redis | None]:
    redis_client = build_redis_client(settings)

    app.state.redis_client = None

    try:
        await redis_client.ping()

    except Exception:
        yield None

        await redis_client.aclose()

        return

    app.state.redis_client = redis_client

    try:
        await redis_client.flushdb()

        yield redis_client

    finally:
        await redis_client.aclose()

        app.state.redis_client = None


@pytest_asyncio.fixture
async def integration_client(
    test_db_session: AsyncSession,
) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


@pytest_asyncio.fixture
async def test_resend_client() -> AsyncIterator[AsyncMock]:
    resend_client = AsyncMock(spec=AsyncClient)

    app.dependency_overrides[get_resend_client] = lambda: resend_client

    try:
        yield resend_client

    finally:
        app.dependency_overrides.pop(get_resend_client, None)


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


@pytest_asyncio.fixture
async def system_admin(test_db_session: AsyncSession) -> User:
    return await make_user(test_db_session, role=UserRole.SYSTEM_ADMIN)


@pytest_asyncio.fixture
async def director(test_db_session: AsyncSession) -> User:
    return await make_user(test_db_session, role=UserRole.DIRECTOR)


@pytest_asyncio.fixture
async def teacher(test_db_session: AsyncSession) -> User:
    return await make_user(test_db_session, role=UserRole.TEACHER)


@pytest_asyncio.fixture
async def student(test_db_session: AsyncSession) -> User:
    return await make_user(test_db_session, role=UserRole.STUDENT)
