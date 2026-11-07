from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from school_management_system_lite.database.base import Base


class UserSession(Base):
    __tablename__ = "user_sessions"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), unique=True, nullable=False
    )

    access_token_version: Mapped[int] = mapped_column(
        nullable=False, server_default="1"
    )

    refresh_token_hash: Mapped[str | None] = mapped_column(nullable=True)
    refresh_token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)

    last_active_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
