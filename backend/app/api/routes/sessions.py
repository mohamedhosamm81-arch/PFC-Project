"""Employee session start/end and personal attendance."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.common import ErrorResponse, Page
from app.schemas.session import SessionRead, SessionStartRequest
from app.services.realtime import publish_session_event
from app.services.session_service import SessionService

router = APIRouter(prefix="/sessions", tags=["Sessions"])


@router.post(
    "/start",
    response_model=SessionRead,
    status_code=201,
    responses={409: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
    summary="Start a shift session and record lateness",
)
async def start_session(
    payload: SessionStartRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> SessionRead:
    record = await SessionService(session).start(user, payload)
    await publish_session_event(
        "session.started",
        station=record.station,
        user_id=user.id,
        full_name=user.full_name,
    )
    return SessionRead.model_validate(record)


@router.post(
    "/end",
    response_model=SessionRead,
    responses={404: {"model": ErrorResponse}},
    summary="End the currently open shift session",
)
async def end_session(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> SessionRead:
    record = await SessionService(session).end(user)
    await publish_session_event(
        "session.ended",
        station=record.station,
        user_id=user.id,
        full_name=user.full_name,
    )
    return SessionRead.model_validate(record)


@router.get(
    "/me",
    response_model=Page[SessionRead],
    summary="List my session history",
)
async def my_sessions(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> Page[SessionRead]:
    records, total = await SessionService(session).list_for_user(
        user.id, limit=limit, offset=offset
    )
    return Page[SessionRead](
        items=[SessionRead.model_validate(record) for record in records],
        total=total,
        limit=limit,
        offset=offset,
    )
