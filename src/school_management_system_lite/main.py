from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from school_management_system_lite.core.config import Settings, get_settings
from school_management_system_lite.core.exceptions import register_exception_handlers
from school_management_system_lite.database.connection import (
    build_engine,
    build_session_factory,
)
from school_management_system_lite.users.routers import router as users_module_routers


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

    engine: AsyncEngine = build_engine(settings)

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))

        app.state.session_factory = build_session_factory(engine)

        yield

    finally:
        await engine.dispose()


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

    app = FastAPI(lifespan=lifespan)

    app.state.settings = settings

    # EXCEPTIONS
    register_exception_handlers(app)

    # ROUTERS
    app.include_router(users_module_routers)

    return app


app = create_app()
