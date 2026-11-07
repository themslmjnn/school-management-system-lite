from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from school_management_system_lite.auth.router import router as auth_module_routers
from school_management_system_lite.core.config import Settings, get_settings
from school_management_system_lite.core.exceptions import register_exception_handlers
from school_management_system_lite.core.logging import configure_logging
from school_management_system_lite.database.connection import (
    build_engine,
    build_session_factory,
)
from school_management_system_lite.groups.router import router as groups_module_routers
from school_management_system_lite.subjects.router import (
    router as subjects_module_routers,
)
from school_management_system_lite.users.routers import router as users_module_routers

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """
    Own the lifetime of shared resources.

    Startup:
    1. Read settings from app.state (attached by create_app)
    2. Build the DB engine (it doesn't connect yet)
    3. Verify PostgreSQL is reachable
    5. Attach the engine, session to app.state

    Shutdown (reverse of startup):
    1. Dispose the DB engine
       Shutdown runs in `finally`, so it also runs after a failed startup.
    """

    settings: Settings = app.state.settings

    logger.info("application_starting", environment=settings.ENVIRONMENT)

    engine: AsyncEngine = build_engine(settings)

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))

        logger.info("database_connected")

        app.state.session_factory = build_session_factory(engine)

        logger.info("application_ready")

        yield

    finally:
        logger.info("application_shutting_down")

        is_shutdown_completed = True

        try:
            await engine.dispose()

            logger.info("db_engine_disposed")

        except Exception as exc:
            is_shutdown_completed = False

            logger.exception("shutdown_failed", error=str(exc))

        if is_shutdown_completed:
            logger.info("application_stopped")


def create_app(settings: Settings | None = None) -> FastAPI:
    """
    Build the application.

    1. Resolve settings once. Pass `settings` explicitly in tests;
       otherwise they come from get_settings().
    2. Create the FastAPI app and attach settings to app.state.
    3. Register exception handlers, so every error leaves the app in the
       standard shape.
    4. Register routers.

    Database is not created here. The lifespan builds
    it, so tests that skip the lifespan must set them on app.state.
    """

    settings = settings or get_settings()

    configure_logging(log_level=settings.LOG_LEVEL)

    app = FastAPI(lifespan=lifespan)

    app.state.settings = settings

    # EXCEPTIONS
    register_exception_handlers(app)

    # ROUTERS
    app.include_router(auth_module_routers)
    app.include_router(users_module_routers)
    app.include_router(subjects_module_routers)
    app.include_router(groups_module_routers)

    return app


app = create_app()
