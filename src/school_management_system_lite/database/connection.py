from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from school_management_system_lite.core.config import Settings


def build_db_engine(settings: Settings) -> AsyncEngine:
    return create_async_engine(
        url=settings.DATABASE_URL,
        pool_pre_ping=True,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        connect_args={"timeout": settings.DB_CONNECT_TIMEOUT},
    )


def build_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
