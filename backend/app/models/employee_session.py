"""Employee shift / attendance sessions."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Computed,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import Location, enum_values
from app.models.user import User


class EmployeeSession(TimestampMixin, Base):
    __tablename__ = "employee_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT", name="fk_employee_sessions_user"),
        nullable=False,
    )
    station: Mapped[Location] = mapped_column(
        SAEnum(Location, name="location", native_enum=True, values_callable=enum_values),
        nullable=False,
    )
    shift_start_scheduled: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    start_session_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_session_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_late_start: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("0"),
    )
    late_minutes: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    # MySQL has no partial indexes. A stored generated column plus a unique
    # index gives us "at most one open session per employee" atomically.
    active_user_id: Mapped[int | None] = mapped_column(
        Integer,
        Computed(
            "CASE WHEN end_session_at IS NULL THEN user_id ELSE NULL END",
            persisted=True,
        ),
        nullable=True,
    )

    user: Mapped[User] = relationship(back_populates="sessions", lazy="selectin")

    __table_args__ = (
        CheckConstraint("late_minutes >= 0", name="ck_employee_sessions_late_nonnegative"),
        Index("ix_employee_sessions_user_start", "user_id", "start_session_at"),
        Index("ix_employee_sessions_start", "start_session_at"),
        Index("uq_employee_sessions_active_user", "active_user_id", unique=True),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )
