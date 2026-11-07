from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from school_management_system_lite.database.base import Base


class Group(Base):
    __tablename__ = "groups"

    name: Mapped[str] = mapped_column(String(10), index=True, nullable=False)
    academic_year: Mapped[str] = mapped_column(String(10), nullable=False)
    grade_level: Mapped[int] = mapped_column(nullable=False)

    max_capacity: Mapped[int] = mapped_column(nullable=False, server_default="25")

    __table_args__ = (
        UniqueConstraint("name", "academic_year", name="uq_groups_name_academic_year"),
    )
