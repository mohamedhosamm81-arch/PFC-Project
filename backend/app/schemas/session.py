"""Employee session schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.models.enums import Location
from app.schemas.common import ORMModel, UtcDateTime
from app.schemas.user import UserRead


class SessionStartRequest(ORMModel):
    shift_start_scheduled: datetime | None = None
    station: Location | None = None


class SessionRead(ORMModel):
    id: int
    user_id: int
    station: Location
    shift_start_scheduled: UtcDateTime
    start_session_at: UtcDateTime
    end_session_at: UtcDateTime | None
    is_late_start: bool
    late_minutes: int
    created_at: UtcDateTime


class SessionWithUser(SessionRead):
    user: UserRead


class SessionFilter(ORMModel):
    start_from: datetime | None = None
    start_to: datetime | None = None
    user_id: int | None = Field(default=None, ge=1)
    station: Location | None = None
    active_only: bool = False
