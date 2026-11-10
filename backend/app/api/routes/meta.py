"""Department and room metadata used by kiosks and display terminals."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.constants import DEPARTMENT_LABELS, INITIAL_DESTINATIONS
from app.db.session import get_db_session
from app.models.enums import Location
from app.models.room import Room
from app.models.user import User
from app.schemas.meta import DepartmentRead, RoomRead

router = APIRouter(prefix="/meta", tags=["Metadata"])


@router.get(
    "/departments",
    response_model=list[DepartmentRead],
    summary="List destinations and whether they can be issued at the kiosk",
)
async def departments(_: User = Depends(get_current_user)) -> list[DepartmentRead]:
    return [
        DepartmentRead(
            value=location,
            label=DEPARTMENT_LABELS[location],
            is_initial_destination=location in INITIAL_DESTINATIONS,
        )
        for location in Location
    ]


@router.get(
    "/rooms",
    response_model=list[RoomRead],
    summary="List active physical rooms used for floor/room display scoping",
)
async def rooms(
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[RoomRead]:
    records = (
        await session.scalars(
            select(Room)
            .where(Room.is_active.is_(True))
            .order_by(Room.floor_number.asc(), Room.name.asc())
        )
    ).all()
    return [RoomRead.model_validate(room) for room in records]
