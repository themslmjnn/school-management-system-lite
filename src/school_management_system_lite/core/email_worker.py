import asyncio

import structlog
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from school_management_system_lite.core.config import Settings
from school_management_system_lite.core.email.service import send_email
from school_management_system_lite.emails.enums import EmailStatus
from school_management_system_lite.emails.models import Email
from school_management_system_lite.emails.repository import EmailRepository

logger = structlog.get_logger(__name__)


async def _process_email(
    db_session: AsyncSession, resend_client: AsyncClient, record: Email
) -> None:
    """
    Attempt to send one email and record the outcome.

    A failed send is recorded on the row and not raised. A database error while
    recording a successful send propagates to the sweep, which logs it. The
    email stays PENDING, so it may be sent twice (at-least-once delivery).
    """

    with structlog.contextvars.bound_contextvars(
        email_id=record.id,
        email_type=record.email_type,
        recipient_email=record.recipient_email,
    ):
        try:
            await send_email(
                resend_client,
                subject=record.subject,
                to_email=record.recipient_email,
                html_body=record.html_body,
            )

        except asyncio.CancelledError:
            await db_session.rollback()

            raise

        except Exception as exc:
            EmailRepository.mark_failed_attempt(record, str(exc))

            await db_session.commit()

            if record.status == EmailStatus.FAILED:
                logger.error(
                    "email_worker_exhausted_retries",
                    retry_count=record.retry_count,
                    error_type=type(exc).__name__,
                    error=str(exc),
                )
            else:
                logger.warning(
                    "email_worker_attempt_failed",
                    retry_count=record.retry_count,
                    error_type=type(exc).__name__,
                    error=str(exc),
                )

            return

        EmailRepository.mark_sent(record)

        await db_session.commit()

        logger.info("email_worker_sent")


async def _run_sweep(
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
    resend_client: AsyncClient,
) -> None:
    """
    One full sweep of the pending queue.
    Opens a fresh session per batch and continues until the queue is drained.
    """

    batch_size = settings.EMAIL_WORKER_BATCH_SIZE

    while True:
        async with session_factory() as session:
            batch = await EmailRepository.get_pending_batch(session, limit=batch_size)

            if not batch:
                break

            logger.info("email_worker_sweep_batch", batch_size=len(batch))

            for record in batch:
                await _process_email(session, record, resend_client)

            if len(batch) < batch_size:
                break


async def run_email_worker(
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
    resend_client: AsyncClient,
) -> None:
    logger.info(
        "email_worker_started",
        poll_interval=settings.EMAIL_WORKER_INTERVAL,
        batch_size=settings.EMAIL_WORKER_BATCH_SIZE,
    )

    while True:
        try:
            await _run_sweep(session_factory, settings, resend_client)

        except asyncio.CancelledError:
            logger.info("email_worker_stopping")

            raise

        except Exception:
            logger.exception("email_worker_sweep_failed")

        await asyncio.sleep(settings.EMAIL_WORKER_INTERVAL)
