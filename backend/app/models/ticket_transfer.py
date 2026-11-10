"""Immutable ticket audit trail."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import Location, TransferAction, enum_values


class TicketTransfer(Base):
    __tablename__ = "ticket_transfers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(
        ForeignKey("tickets.id", ondelete="RESTRICT", name="fk_ticket_transfers_ticket"),
        nullable=False,
    )
    from_location: Mapped[Location | None] = mapped_column(
        SAEnum(Location, name="location", native_enum=True, values_callable=enum_values),
        nullable=True,
    )
    to_location: Mapped[Location | None] = mapped_column(
        SAEnum(Location, name="location", native_enum=True, values_callable=enum_values),
        nullable=True,
    )
    transferred_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT", name="fk_ticket_transfers_user"),
        nullable=False,
    )
    transferred_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP(6)"),
    )
    action_type: Mapped[TransferAction] = mapped_column(
        SAEnum(TransferAction, name="transfer_action", native_enum=True, values_callable=enum_values),
        nullable=False,
    )
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)

    ticket: Mapped["Ticket"] = relationship(back_populates="transfers", lazy="raise")  # noqa: F821
    actor: Mapped["User"] = relationship(foreign_keys=[transferred_by], lazy="selectin")  # noqa: F821

    __table_args__ = (
        Index("ix_ticket_transfers_ticket_time", "ticket_id", "transferred_at"),
        Index("ix_ticket_transfers_action", "action_type"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )
