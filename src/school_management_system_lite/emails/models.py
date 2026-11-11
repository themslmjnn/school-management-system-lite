from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from school_management_system_lite.database.base import Base
from school_management_system_lite.emails.enums import EmailStatus, EmailType

if TYPE_CHECKING:
    from school_management_system_lite.users.models import User


class Email(Base):
    __tablename__ = "emails"

    recipient_email: Mapped[str] = mapped_column(String(50), nullable=False)
    subject: Mapped[str] = mapped_column(String(150), nullable=False)
    html_body: Mapped[str] = mapped_column(Text, nullable=False)

    email_type: Mapped[EmailType] = mapped_column(
        Enum(EmailType), index=True, nullable=False
    )
    status: Mapped[EmailStatus] = mapped_column(
        Enum(EmailStatus),
        index=True,
        server_default=EmailStatus.PENDING.name,
        nullable=False,
    )

    retry_count: Mapped[int] = mapped_column(nullable=False, default=0)
    max_retries: Mapped[int] = mapped_column(nullable=False, default=3)

    scheduled_for: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    triggered_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        index=True,
        nullable=True,
    )

    triggered_by_user: Mapped["User | None"] = relationship(  # noqa: UP037
        "User",
        foreign_keys=[triggered_by],
    )
