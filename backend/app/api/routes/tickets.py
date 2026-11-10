"""Ticket issuance, transfer, late, recall, completion and serving."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_roles
from app.core.exceptions import AppError
from app.db.session import get_db_session
from app.models.enums import Location, UserRole
from app.models.user import User
from app.schemas.common import ErrorResponse
from app.schemas.ticket import (
    DoneTicketRequest,
    IssueTicketRequest,
    LateTicketRequest,
    ServeNextRequest,
    TicketMutationResponse,
    TicketRead,
    TransferTicketRequest,
)
from app.services.realtime import publish_ticket_event
from app.services.ticket_service import TicketMutation, TicketService

logger = logging.getLogger("pfc.realtime")
router = APIRouter(prefix="/tickets", tags=["Tickets"])

ACTION_ROLES = (
    UserRole.ADMIN,
    UserRole.RECEPTION,
    UserRole.DOCTOR,
    UserRole.BRANCH_STAFF,
)


async def _publish(session: AsyncSession, mutation: TicketMutation) -> None:
    try:
        await publish_ticket_event(
            session,
            event=mutation.event,
            ticket=mutation.ticket,
            previous_location=mutation.previous_location,
        )
    except Exception as exc:  # realtime must never roll back a committed action
        logger.warning("Realtime publish failed: %s", exc)


def _response(mutation: TicketMutation) -> TicketMutationResponse:
    return TicketMutationResponse(
        ticket=TicketRead.model_validate(mutation.ticket),
        previous_location=mutation.previous_location,
        event=mutation.event,
    )


@router.post(
    "/issue",
    response_model=TicketMutationResponse,
    status_code=201,
    responses={422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
    summary="Issue the next circular ticket code (kiosk)",
)
async def issue_ticket(
    payload: IssueTicketRequest,
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.RECEPTION)),
    session: AsyncSession = Depends(get_db_session),
) -> TicketMutationResponse:
    mutation = await TicketService(session).issue(
        user,
        initial_destination=payload.initial_destination,
        is_overbooked=payload.is_overbooked,
    )
    await _publish(session, mutation)
    return _response(mutation)


@router.post(
    "/transfer",
    response_model=TicketMutationResponse,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
    summary="Transfer a ticket to another department (Cashier is transfer-only)",
)
async def transfer_ticket(
    payload: TransferTicketRequest,
    user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.RECEPTION, UserRole.DOCTOR, UserRole.BRANCH_STAFF)
    ),
    session: AsyncSession = Depends(get_db_session),
) -> TicketMutationResponse:
    mutation = await TicketService(session).transfer(
        user,
        ticket_id=payload.ticket_id,
        ticket_code=payload.ticket_code,
        to_location=payload.to_location,
        note=payload.note,
    )
    await _publish(session, mutation)
    return _response(mutation)


@router.post(
    "/late",
    response_model=TicketMutationResponse,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
    summary="Mark a ticket late and move it behind on-time waiting patients",
)
async def mark_ticket_late(
    payload: LateTicketRequest,
    user: User = Depends(require_roles(*ACTION_ROLES)),
    session: AsyncSession = Depends(get_db_session),
) -> TicketMutationResponse:
    mutation = await TicketService(session).mark_late(
        user,
        ticket_id=payload.ticket_id,
        ticket_code=payload.ticket_code,
        note=payload.note,
    )
    await _publish(session, mutation)
    return _response(mutation)


@router.post(
    "/recall",
    response_model=TicketMutationResponse,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
    summary="Return a late ticket to the normal waiting queue",
)
async def recall_ticket(
    payload: LateTicketRequest,
    user: User = Depends(require_roles(*ACTION_ROLES)),
    session: AsyncSession = Depends(get_db_session),
) -> TicketMutationResponse:
    mutation = await TicketService(session).recall(
        user,
        ticket_id=payload.ticket_id,
        ticket_code=payload.ticket_code,
        note=payload.note,
    )
    await _publish(session, mutation)
    return _response(mutation)


@router.post(
    "/done",
    response_model=TicketMutationResponse,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
    summary="Close a visit and stamp completed_at",
)
async def complete_ticket(
    payload: DoneTicketRequest,
    user: User = Depends(require_roles(*ACTION_ROLES)),
    session: AsyncSession = Depends(get_db_session),
) -> TicketMutationResponse:
    mutation = await TicketService(session).complete(
        user,
        ticket_id=payload.ticket_id,
        ticket_code=payload.ticket_code,
        note=payload.note,
    )
    await _publish(session, mutation)
    return _response(mutation)


@router.post(
    "/next",
    response_model=TicketMutationResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Call the next on-time ticket, then late tickets",
)
async def serve_next(
    payload: ServeNextRequest,
    user: User = Depends(require_roles(*ACTION_ROLES)),
    session: AsyncSession = Depends(get_db_session),
) -> TicketMutationResponse:
    mutation = await TicketService(session).serve_next(user, payload.station)
    await _publish(session, mutation)
    return _response(mutation)


@router.get(
    "/by-code/{ticket_code}",
    response_model=TicketRead,
    responses={404: {"model": ErrorResponse}},
    summary="Find a ticket by its circular code",
)
async def get_ticket_by_code(
    ticket_code: int,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> TicketRead:
    if ticket_code < 1 or ticket_code > 999:
        raise AppError(422, "INVALID_TICKET_CODE", "Ticket code must be between 1 and 999.")
    ticket = await TicketService(session).get_ticket(ticket_code=ticket_code)
    return TicketRead.model_validate(ticket)


@router.get(
    "/{ticket_id}",
    response_model=TicketRead,
    responses={404: {"model": ErrorResponse}},
    summary="Find a ticket by database id",
)
async def get_ticket(
    ticket_id: int,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> TicketRead:
    ticket = await TicketService(session).get_ticket(ticket_id=ticket_id)
    return TicketRead.model_validate(ticket)
