"""Employee/user accounts."""

from __future__ import annotations

from datetime import time

from sqlalchemy import Boolean, CheckConstraint, Enum as SAEnum, Index, Integer, String, Time, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import Location, UserRole, enum_values


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="user_role", native_enum=True, values_callable=enum_values),
        nullable=False,
    )
    assigned_station: Mapped[Location | None] = mapped_column(
        SAEnum(Location, name="location", native_enum=True, values_callable=enum_values),
        nullable=True,
    )
    default_shift_start: Mapped[time] = mapped_column(
        Time,
        nullable=False,
        default=time(8, 0),
        server_default=text("'08:00:00'"),
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("1"),
    )

    sessions: Mapped[list["EmployeeSession"]] = relationship(
        back_populates="user",
        lazy="raise",
    )

    __table_args__ = (
        CheckConstraint(
            "(role = 'admin' AND assigned_station IS NULL) OR "
            "(role <> 'admin' AND assigned_station IS NOT NULL)",
            name="ck_users_role_station",
        ),
        Index("ix_users_role_active", "role", "is_active"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )
