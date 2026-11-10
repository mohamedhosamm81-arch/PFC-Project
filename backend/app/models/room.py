"""Physical floor/room destinations used to scope realtime display boards."""

from __future__ import annotations

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Enum as SAEnum,
    Index,
    Integer,
    SmallInteger,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.enums import Location, enum_values


class Room(TimestampMixin, Base):
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    floor_number: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    station: Mapped[Location] = mapped_column(
        SAEnum(Location, name="location", native_enum=True, values_callable=enum_values),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("1"),
    )

    __table_args__ = (
        CheckConstraint("floor_number > 0", name="ck_rooms_floor_positive"),
        Index("ix_rooms_floor_station", "floor_number", "station"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )
