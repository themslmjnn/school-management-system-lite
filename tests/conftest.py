from collections.abc import AsyncGenerator, AsyncIterator, Iterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy import NullPool, create_engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from school_management_system_lite.core.config import get_settings
from school_management_system_lite.core.dependencies import get_db_session
from school_management_system_lite.core.redis.client import build_redis
from school_management_system_lite.database.base import Base
from school_management_system_lite.main import app
from school_management_system_lite.users.models.user import User
from tests.factories import make_director, make_student, make_system_admin, make_teacher

TEST_DB_URL = "sqlite:///./test.db"

test_engine = create_async_engine(
    "sqlite+aiosqlite:///./test.db",
    poolclass=NullPool,
)


@pytest.fixture(scope="session", autouse=True)
def _guard_test_environment() -> None:
    if get_settings().ENVIRONMENT != "test":
        pytest.exit(
            f"Refusing to run tests: ENVIRONMENT is "
            f"'{get_settings().ENVIRONMENT}', expected 'test'",
            returncode=2,
        )


@pytest.fixture(scope="session")
def create_tables(_guard_test_environment: None) -> Iterator[None]:
    sync_engine = create_engine(TEST_DB_URL, poolclass=NullPool)

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
async def redis_client() -> AsyncIterator[Redis]:
    app.state.settings = get_settings()

    redis: Redis = build_redis(app)

    client: Redis = app.state.redis

    try:
        await client.flushdb()

        yield client

    finally:
        await redis.aclose()

        del app.state.redis


@pytest_asyncio.fixture
async def client(
    test_db_session: AsyncSession,
    redis_client: Redis,
) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as async_client:
        yield async_client


@pytest_asyncio.fixture
async def system_admin(test_db_session) -> User:
    return await make_system_admin(test_db_session)


@pytest_asyncio.fixture
async def director(test_db_session) -> User:
    return await make_director(test_db_session)


@pytest_asyncio.fixture
async def teacher(test_db_session) -> User:
    return await make_teacher(test_db_session)


@pytest_asyncio.fixture
async def student(test_db_session) -> User:
    return await make_student(test_db_session)
