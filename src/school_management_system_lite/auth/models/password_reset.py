from datetime import datetime

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from school_management_system_lite.database.base import Base


class UserPasswordReset(Base):
    __tablename__ = "user_password_resets"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), unique=True, nullable=False
    )

    password_reset_token_hash: Mapped[str] = mapped_column(nullable=False)
    password_reset_token_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
