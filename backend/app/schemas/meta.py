"""Room / department metadata schemas."""

from __future__ import annotations

from app.models.enums import Location
from app.schemas.common import ORMModel, UtcDateTime


class RoomRead(ORMModel):
    id: int
    code: str
    name: str
    floor_number: int
    station: Location
    is_active: bool
    created_at: UtcDateTime


class DepartmentRead(ORMModel):
    value: Location
    label: str
    is_initial_destination: bool
