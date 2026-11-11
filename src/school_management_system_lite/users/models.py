from datetime import date

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from school_management_system_lite.database.base import Base
from school_management_system_lite.users.utils.enums import UserRole, UserStatus


class User(Base):
    __tablename__ = "users"

    first_name: Mapped[str] = mapped_column(String(30), index=True, nullable=False)
    last_name: Mapped[str] = mapped_column(String(30), index=True, nullable=False)
    middle_name: Mapped[str | None] = mapped_column(String(30), nullable=True)

    date_of_birth: Mapped[date] = mapped_column(nullable=False)

    address: Mapped[str | None] = mapped_column(String(150), nullable=True)

    phone_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)

    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus),
        nullable=False,
        server_default=UserStatus.PENDING_ACTIVATION.name,
    )

    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    creator: Mapped["User | None"] = relationship(  # noqa: UP037
        "User",
        remote_side="User.id",
        foreign_keys="[User.created_by]",
        back_populates="created_users",
    )

    created_users: Mapped[list["User"]] = relationship(  # noqa: UP037
        "User", foreign_keys="[User.created_by]", back_populates="creator"
    )
