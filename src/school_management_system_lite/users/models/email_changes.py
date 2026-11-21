from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from school_management_system_lite.database.base import Base


class UserEmailChange(Base):
    __tablename__ = "user_email_changes"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
    )
    new_email: Mapped[str] = mapped_column(String(50), nullable=False)
    email_change_token_hash: Mapped[str] = mapped_column(nullable=False)
    email_change_token_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
