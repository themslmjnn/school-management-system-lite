from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from school_management_system_lite.emails.enums import EmailStatus
from school_management_system_lite.emails.models import Email
from school_management_system_lite.utils.enums import OrderBy

RETRY_DELAY = timedelta(minutes=2)


class EmailRepository:
    @staticmethod
    async def get_by_recipient_email(
        db_session: AsyncSession, recipient_email: str, order_by: OrderBy = OrderBy.ASC
    ) -> Sequence[Email]:
        stmt = select(Email).where(Email.recipient_email == recipient_email)

        if order_by == OrderBy.DESC:
            stmt = stmt.order_by(Email.created_at.desc())

        stmt = stmt.order_by(Email.created_at.asc())

        result = await db_session.execute(stmt)

        return result.scalars().all()

    @staticmethod
    async def get_pending_batch(
        db_session: AsyncSession, *, limit: int = 10
    ) -> Sequence[Email]:
        query = (
            select(Email)
            .where(
                Email.status == EmailStatus.PENDING,
                Email.scheduled_for <= func.now(),
            )
            .order_by(Email.id.asc())
            .limit(limit)
        )

        result = await db_session.execute(query)

        return result.scalars().all()

    @staticmethod
    def mark_failed_attempt(record: Email, error: str) -> None:
        record.retry_count += 1
        record.last_error = error[:500]

        if record.retry_count >= record.max_retries:
            record.status = EmailStatus.FAILED
        else:
            record.scheduled_for = datetime.now(UTC) + RETRY_DELAY * record.retry_count

    @staticmethod
    def mark_sent(record: Email) -> None:
        record.status = EmailStatus.SENT
        record.sent_at = datetime.now(UTC)
