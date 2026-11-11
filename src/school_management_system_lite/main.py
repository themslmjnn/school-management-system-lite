import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from httpx import AsyncClient
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from school_management_system_lite.auth.router import router as auth_module_routers
from school_management_system_lite.core.config import Settings, get_settings
from school_management_system_lite.core.email.providers import build_resend_client
from school_management_system_lite.core.email_worker import run_email_worker
from school_management_system_lite.core.exceptions.handlers import (
    register_exception_handlers,
)
from school_management_system_lite.core.logging import configure_logging
from school_management_system_lite.core.redis.client import (
    build_redis_client,
)
from school_management_system_lite.database.connection import (
    build_db_engine,
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
    1. Read application settings from app.state.
    2. Build the database engine and Redis client.
    3. Verify that PostgreSQL is reachable.
       Database failure prevents the application from starting.
    4. Check Redis connectivity.
       Redis is optional, so a Redis failure is logged without
       preventing the application from starting.
    5. Build the Resend HTTP client in staging and production.
       Resend availability is not checked during startup because
       temporary Resend outages should not prevent the application
       from starting.
    6. Attach shared resources to app.state.
    7. Start the email worker.
    8. Yield control to the application.

    Shutdown:
    1. Cancel and wait for the email worker, if it was started.
    2. Close the Resend HTTP client, if it was created.
    3. Close the Redis client.
    4. Dispose of the database engine.

    Shutdown continues even if an individual cleanup step fails.
    """

    settings: Settings = app.state.settings

    logger.info("application_starting", environment=settings.ENVIRONMENT)

    db_engine: AsyncEngine = build_db_engine(settings)
    redis_client: Redis = build_redis_client(settings)

    resend_client: AsyncClient | None = None

    if settings.ENVIRONMENT in ("staging", "production"):
        resend_client = build_resend_client()

    email_worker_task: asyncio.Task[None] | None = None

    try:
        async with db_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))

        logger.info("database_connected")

        try:
            await redis_client.ping()

            app.state.redis_client = redis_client

            logger.info("redis_client_connected")

        except Exception as exc:
            logger.warning("redis_connection_failed", error=str(exc))

        if settings.ENVIRONMENT in ("staging", "production") and resend_client is None:
            raise RuntimeError(
                "Resend client must be reachable in staging and production"
            )

        app.state.db_engine = db_engine
        app.state.session_factory = build_session_factory(db_engine)
        app.state.resend_client = resend_client

        email_worker_task = asyncio.create_task(
            run_email_worker(
                session_factory=app.state.session_factory,
                settings=settings,
                resend_client=app.state.resend_client,
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

            logger.info("email_worker_stopped")

        if resend_client is not None:
            try:
                await resend_client.aclose()

                logger.info("resend_client_closed")

            except Exception as exc:
                is_shutdown_completed = False

                logger.exception(
                    "shutdown_step_failed",
                    step="resend_client",
                    error=str(exc),
                )

        shutdown = (
            ("redis_client", redis_client.aclose, "redis_client_closed"),
            ("db_engine", db_engine.dispose, "db_engine_disposed"),
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

    1. Resolve application settings once. Explicit settings are used
       in tests; otherwise settings are loaded through get_settings().
    2. Configure application logging.
    3. Create the FastAPI application with the resource lifespan.
    4. Initialize optional shared resources on app.state.
    5. Attach settings to app.state.
    6. Register exception handlers.
    7. Register application routers.

    Database, Redis, and Resend resources are created by the lifespan
    rather than here. Tests that do not run the lifespan must provide
    any required resources on app.state themselves.
    """

    settings = settings or get_settings()

    configure_logging(log_level=settings.LOG_LEVEL)

    app = FastAPI(lifespan=lifespan)

    app.state.settings = settings
    app.state.redis_client = None
    app.state.resend_client = None

    # EXCEPTIONS
    register_exception_handlers(app)

    # ROUTERS
    app.include_router(auth_module_routers)
    app.include_router(users_module_routers)
    app.include_router(subjects_module_routers)
    app.include_router(groups_module_routers)

    return app


app = create_app()
