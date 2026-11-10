"""Persistent 1..999 circular ticket-code allocator."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, SmallInteger, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.core.time import utcnow


class TicketSequence(Base):
    __tablename__ = "ticket_sequence"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    next_ticket_code: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
        server_default=text("CURRENT_TIMESTAMP(6)"),
    )

    __table_args__ = (
        CheckConstraint("id = 1", name="ck_ticket_sequence_singleton"),
        CheckConstraint(
            "next_ticket_code BETWEEN 1 AND 999",
            name="ck_ticket_sequence_code_range",
        ),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )
