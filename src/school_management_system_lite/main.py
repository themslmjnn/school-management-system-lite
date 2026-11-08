import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from school_management_system_lite.auth.router import router as auth_module_routers
from school_management_system_lite.core.config import Settings, get_settings
from school_management_system_lite.core.email_worker import run_email_worker
from school_management_system_lite.core.exceptions import register_exception_handlers
from school_management_system_lite.core.logging import configure_logging
from school_management_system_lite.core.redis.client import build_redis
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
    Manage the lifetime of shared application resources.

    Startup:
    1. Read settings from app.state.
    2. Build the database engine and Redis client.
    3. Verify that PostgreSQL is reachable.
       Database failure prevents the application from starting.
    4. Check Redis connectivity.
       Redis is optional, so Redis failure is logged but does not
       prevent the application from starting.
    5. Attach the database engine, session factory, and Redis client
       to app.state.
    6. Start the email worker.
    7. Yield control to the application.

    Shutdown:
    1. Cancel and wait for the email worker, if it was started.
    2. Close the Redis client.
    3. Dispose of the database engine.

    Shutdown continues even if an individual cleanup step fails.
    """

    settings: Settings = app.state.settings

    logger.info("application_starting", environment=settings.ENVIRONMENT)

    engine: AsyncEngine = build_engine(settings)
    redis: Redis = build_redis(settings)

    email_worker_task: asyncio.Task[None] | None = None

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))

        logger.info("database_connected")

        try:
            await redis.ping()

            app.state.redis = redis

            logger.info("redis_connected")

        except BaseException as exc:
            logger.error("redis_connection_failed", error=str(exc))

        app.state.engine = engine
        app.state.session_factory = build_session_factory(engine)

        email_worker_task = asyncio.create_task(
            run_email_worker(
                session_factory=app.state.session_factory,
                settings=settings,
            ),
            name="email_worker",
        )

        logger.info("application_ready")

        yield

    finally:
        logger.info("application_shutting_down")

        is_shutdown_completed = True

        if email_worker_task is not None:
            email_worker_task.cancel()

            result = await asyncio.gather(
                email_worker_task,
                return_exceptions=True,
            )

            result = result[0]

            if isinstance(result, BaseException) and not isinstance(
                result, asyncio.CancelledError
            ):
                is_shutdown_completed = False

                logger.error(
                    "worker_shutdown_error",
                    worker=email_worker_task.get_name(),
                    error=str(result),
                    error_type=type(result).__name__,
                )

        shutdown = (
            ("redis", redis.aclose, "redis_closed"),
            ("db_engine", engine.dispose, "db_engine_disposed"),
        )

        for step, close, log in shutdown:
            try:
                await close()

                logger.info(log)

            except Exception as exc:
                is_shutdown_completed = False

                logger.exception("shutdown_step_failed", step=step, error=str(exc))

        if is_shutdown_completed:
            logger.info("application_stopped")


def create_app(settings: Settings | None = None) -> FastAPI:
    """
    Build and configure the FastAPI application.

    1. Resolve settings once. Explicit settings are used in tests;
       otherwise they are loaded through get_settings().
    2. Configure application logging.
    3. Create the FastAPI application with the resource lifespan.
    4. Attach settings to app.state.
    5. Register exception handlers.
    6. Register application routers.

    Database and Redis resources are created by the lifespan rather
    than here. Tests that do not run the lifespan must provide any
    required resources on app.state themselves.
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
