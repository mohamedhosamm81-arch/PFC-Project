"""Administrative user, attendance and ticket-history endpoints."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db_session
from app.models.enums import Location, TicketStatus, UserRole
from app.models.ticket_sequence import TicketSequence
from app.models.user import User
from app.schemas.common import ErrorResponse, Page
from app.schemas.session import SessionWithUser
from app.schemas.ticket import TicketRead
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.services.session_service import SessionService
from app.services.ticket_service import TicketService
from app.services.user_service import UserService

router = APIRouter(
    prefix="/admin",
    tags=["Administration"],
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)


@router.get("/users", response_model=Page[UserRead], summary="List employee accounts")
async def list_users(
    search: str | None = Query(default=None, max_length=120),
    role: UserRole | None = None,
    station: Location | None = None,
    active_only: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> Page[UserRead]:
    users, total = await UserService(session).list(
        search=search,
        role=role,
        station=station,
        active_only=active_only,
        limit=limit,
        offset=offset,
    )
    return Page[UserRead](
        items=[UserRead.model_validate(user) for user in users],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/users",
    response_model=UserRead,
    status_code=201,
    responses={409: {"model": ErrorResponse}},
    summary="Create an employee account",
)
async def create_user(
    payload: UserCreate,
    session: AsyncSession = Depends(get_db_session),
) -> UserRead:
    user = await UserService(session).create(payload)
    return UserRead.model_validate(user)


@router.patch(
    "/users/{user_id}",
    response_model=UserRead,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
    summary="Update an employee account, station, role or password",
)
async def update_user(
    user_id: int,
    payload: UserUpdate,
    actor: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> UserRead:
    user = await UserService(session).update(user_id, payload, actor.id)
    return UserRead.model_validate(user)


@router.get(
    "/sessions",
    response_model=Page[SessionWithUser],
    summary="Query active and historical attendance sessions",
)
async def list_sessions(
    start_from: datetime | None = None,
    start_to: datetime | None = None,
    user_id: int | None = Query(default=None, ge=1),
    station: Location | None = None,
    active_only: bool = False,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> Page[SessionWithUser]:
    records, total = await SessionService(session).list_all(
        start_from=start_from,
        start_to=start_to,
        user_id=user_id,
        station=station,
        active_only=active_only,
        limit=limit,
        offset=offset,
    )
    return Page[SessionWithUser](
        items=[SessionWithUser.model_validate(record) for record in records],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/tickets",
    response_model=Page[TicketRead],
    summary="Query historical tickets",
)
async def list_tickets(
    station: Location | None = None,
    status: TicketStatus | None = None,
    ticket_code: int | None = Query(default=None, ge=1, le=999),
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> Page[TicketRead]:
    tickets, total = await TicketService(session).history(
        station=station,
        status=status,
        ticket_code=ticket_code,
        created_from=created_from,
        created_to=created_to,
        limit=limit,
        offset=offset,
    )
    return Page[TicketRead](
        items=[TicketRead.model_validate(ticket) for ticket in tickets],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/ticket-sequence", summary="Inspect the persistent circular ticket counter")
async def ticket_sequence(
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, int]:
    sequence = await session.scalar(select(TicketSequence).where(TicketSequence.id == 1))
    if sequence is None:
        return {"next_ticket_code": 1}
    return {"next_ticket_code": sequence.next_ticket_code}
