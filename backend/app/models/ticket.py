"""Queue tickets."""

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
from app.models.enums import Location, TicketStatus, enum_values


class Ticket(TimestampMixin, Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_code: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    initial_destination: Mapped[Location] = mapped_column(
        SAEnum(Location, name="location", native_enum=True, values_callable=enum_values),
        nullable=False,
    )
    current_location: Mapped[Location] = mapped_column(
        SAEnum(Location, name="location", native_enum=True, values_callable=enum_values),
        nullable=False,
    )
    status: Mapped[TicketStatus] = mapped_column(
        SAEnum(TicketStatus, name="ticket_status", native_enum=True, values_callable=enum_values),
        nullable=False,
        default=TicketStatus.WAITING,
        server_default=text("'WAITING'"),
    )
    is_overbooked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("0"),
    )
    assigned_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL", name="fk_tickets_assigned_user"),
        nullable=True,
    )
    late_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Codes are reusable after completion (1..999 circular). The generated
    # column is NULL for DONE tickets, so the unique index permits history but
    # guarantees no two *active* tickets can ever share a code.
    active_ticket_code: Mapped[int | None] = mapped_column(
        SmallInteger,
        Computed(
            "CASE WHEN status <> 'DONE' THEN ticket_code ELSE NULL END",
            persisted=True,
        ),
        nullable=True,
    )

    assigned_user: Mapped["User | None"] = relationship(  # noqa: F821
        foreign_keys=[assigned_user_id],
        lazy="selectin",
    )
    transfers: Mapped[list["TicketTransfer"]] = relationship(
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="TicketTransfer.transferred_at",
        lazy="selectin",
    )

    __table_args__ = (
        CheckConstraint("ticket_code BETWEEN 1 AND 999", name="ck_tickets_code_range"),
        CheckConstraint(
            "initial_destination <> 'Cashier'",
            name="ck_tickets_cashier_not_initial",
        ),
        Index("ix_tickets_current_location_status", "current_location", "status"),
        Index("ix_tickets_ticket_code", "ticket_code"),
        Index("ix_tickets_created_at", "created_at"),
        Index("ix_tickets_assigned_user", "assigned_user_id"),
        Index("uq_tickets_active_ticket_code", "active_ticket_code", unique=True),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )
