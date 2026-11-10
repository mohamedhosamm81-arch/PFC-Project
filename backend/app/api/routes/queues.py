"""Queue and door-screen read endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db_session
from app.models.enums import Location
from app.models.user import User
from app.schemas.ticket import DisplayBoardResponse, QueueResponse, QueueSummary
from app.services.ticket_service import TicketService

router = APIRouter(prefix="/queues", tags=["Queues"])


@router.get("", response_model=list[QueueSummary], summary="Load summary for every station")
async def all_queues(
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[QueueSummary]:
    return await TicketService(session).queue_summaries()


@router.get(
    "/{station}",
    response_model=QueueResponse,
    summary="Load a station's active queue",
)
async def station_queue(
    station: Location,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> QueueResponse:
    return await TicketService(session).queue(station)


@router.get(
    "/{station}/display",
    response_model=DisplayBoardResponse,
    summary="Load the patient-facing door board for a station",
)
async def station_display(
    station: Location,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> DisplayBoardResponse:
    return await TicketService(session).display_board(station)
