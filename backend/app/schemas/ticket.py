"""Ticket, queue and display schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import Field, model_validator

from app.models.enums import Location, TicketStatus, TransferAction
from app.schemas.common import ORMModel, UtcDateTime


class TicketRead(ORMModel):
    id: int
    ticket_code: int
    initial_destination: Location
    current_location: Location
    status: TicketStatus
    is_overbooked: bool
    assigned_user_id: int | None
    late_at: UtcDateTime | None
    created_at: UtcDateTime
    completed_at: UtcDateTime | None


class TicketTransferRead(ORMModel):
    id: int
    from_location: Location | None
    to_location: Location | None
    transferred_by: int
    transferred_at: UtcDateTime
    action_type: TransferAction
    note: str | None


class TicketDetail(TicketRead):
    transfers: list[TicketTransferRead]


class TicketLocator(ORMModel):
    ticket_id: int | None = Field(default=None, ge=1)
    ticket_code: int | None = Field(default=None, ge=1, le=999)

    @model_validator(mode="after")
    def require_locator(self) -> "TicketLocator":
        if self.ticket_id is None and self.ticket_code is None:
            raise ValueError("Provide either ticket_id or ticket_code.")
        return self


class IssueTicketRequest(ORMModel):
    initial_destination: Location
    is_overbooked: bool | None = None


class TransferTicketRequest(TicketLocator):
    to_location: Location
    note: Annotated[str | None, Field(default=None, max_length=255)] = None


class LateTicketRequest(TicketLocator):
    note: Annotated[str | None, Field(default=None, max_length=255)] = None


class DoneTicketRequest(TicketLocator):
    note: Annotated[str | None, Field(default=None, max_length=255)] = None


class ServeNextRequest(ORMModel):
    station: Location | None = None


class QueueResponse(ORMModel):
    station: Location
    serving: list[TicketRead]
    waiting: list[TicketRead]
    late: list[TicketRead]
    total_active: int
    waiting_count: int
    late_count: int
    generated_at: UtcDateTime


class QueueSummary(ORMModel):
    station: Location
    serving: int
    waiting: int
    late: int
    total_active: int


class DisplayBoardResponse(ORMModel):
    station: Location
    now_serving: TicketRead | None
    waiting_preview: list[TicketRead]
    waiting_count: int
    late_count: int
    generated_at: UtcDateTime


class TicketMutationResponse(ORMModel):
    ticket: TicketRead
    previous_location: Location | None = None
    event: str
