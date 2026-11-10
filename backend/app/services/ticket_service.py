"""Core queue, ticket and audit-trail business rules."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import case, func, select
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.constants import (
    INITIAL_DESTINATIONS,
    TICKET_MAX_CODE,
    TICKET_MIN_CODE,
    TICKET_SEQUENCE_ID,
)
from app.core.exceptions import (
    AppError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from app.core.time import facility_today, local_day_bounds, to_utc_naive, utcnow
from app.models.enums import Location, TicketStatus, TransferAction, UserRole
from app.models.ticket import Ticket
from app.models.ticket_sequence import TicketSequence
from app.models.ticket_transfer import TicketTransfer
from app.models.user import User
from app.schemas.ticket import DisplayBoardResponse, QueueResponse, QueueSummary, TicketRead

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(slots=True)
class TicketMutation:
    ticket: Ticket
    event: str
    previous_location: Location | None = None


def _queue_order():
    status_rank = case(
        (Ticket.status == TicketStatus.SERVING, 0),
        (Ticket.status == TicketStatus.WAITING, 1),
        (Ticket.status == TicketStatus.LATE, 2),
        else_=3,
    )
    within_status = case(
        (
            Ticket.status == TicketStatus.LATE,
            func.coalesce(Ticket.late_at, Ticket.created_at),
        ),
        else_=Ticket.created_at,
    )
    return status_rank, within_status


class TicketService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ------------------------------------------------------------------ issue
    async def issue(
        self,
        actor: User,
        initial_destination: Location,
        is_overbooked: bool | None = None,
    ) -> TicketMutation:
        if initial_destination not in INITIAL_DESTINATIONS:
            raise ValidationError(
                "CASHIER_NOT_INITIAL_DESTINATION",
                "Cashier tickets cannot be created at the kiosk. Transfer a ticket to Cashier instead.",
            )

        overbooked = (
            is_overbooked
            if is_overbooked is not None
            else await self._compute_overbooked(initial_destination)
        )

        sequence = await self._lock_sequence()
        chosen: int | None = None
        for _ in range(TICKET_MAX_CODE):
            candidate = sequence.next_ticket_code
            sequence.next_ticket_code = (
                TICKET_MIN_CODE if candidate >= TICKET_MAX_CODE else candidate + 1
            )
            in_use = await self.session.scalar(
                select(Ticket.id)
                .where(
                    Ticket.ticket_code == candidate,
                    Ticket.status != TicketStatus.DONE,
                )
                .limit(1)
            )
            if in_use is None:
                chosen = candidate
                break

        if chosen is None:
            await self.session.rollback()
            raise AppError(
                503,
                "TICKET_CODE_POOL_EXHAUSTED",
                "All 999 active ticket codes are in use. Complete or cancel stale tickets and try again.",
            )

        now = utcnow()
        ticket = Ticket(
            ticket_code=chosen,
            initial_destination=initial_destination,
            current_location=initial_destination,
            status=TicketStatus.WAITING,
            is_overbooked=bool(overbooked),
            assigned_user_id=None,
            created_at=now,
            updated_at=now,
        )
        self.session.add(ticket)
        await self.session.flush()
        self._audit(
            ticket=ticket,
            actor=actor,
            action=TransferAction.ISSUED,
            from_location=None,
            to_location=initial_destination,
            at=now,
            note="Ticket issued at kiosk",
        )
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError(
                "TICKET_ALLOCATION_CONFLICT",
                "The ticket code could not be allocated. Please retry.",
            ) from exc
        return TicketMutation(ticket=ticket, event="ticket.created")

    async def _compute_overbooked(self, destination: Location) -> bool:
        if destination != Location.CMO:
            return False
        day_start, day_end = local_day_bounds(facility_today())
        issued_today = await self.session.scalar(
            select(func.count(Ticket.id)).where(
                Ticket.initial_destination == Location.CMO,
                Ticket.created_at >= day_start,
                Ticket.created_at < day_end,
            )
        )
        return int(issued_today or 0) >= settings.doctor_daily_slot_limit

    async def _lock_sequence(self) -> TicketSequence:
        sequence = await self.session.scalar(
            select(TicketSequence)
            .where(TicketSequence.id == TICKET_SEQUENCE_ID)
            .with_for_update()
        )
        if sequence is None:
            # This should only happen on a manually-created database. The
            # migration and seed both insert the singleton row.
            sequence = TicketSequence(id=TICKET_SEQUENCE_ID, next_ticket_code=TICKET_MIN_CODE)
            self.session.add(sequence)
            await self.session.flush()
        return sequence

    # ----------------------------------------------------------------- actions
    async def transfer(
        self,
        actor: User,
        *,
        ticket_id: int | None,
        ticket_code: int | None,
        to_location: Location,
        note: str | None = None,
    ) -> TicketMutation:
        ticket = await self._load_ticket(ticket_id, ticket_code, for_update=True)
        if ticket.status == TicketStatus.DONE:
            raise ConflictError("TICKET_CLOSED", "A completed ticket cannot be transferred.")
        self._assert_station_access(actor, ticket.current_location)
        if to_location == ticket.current_location:
            raise ValidationError(
                "SAME_DESTINATION",
                "The ticket is already at that destination.",
            )

        previous = ticket.current_location
        ticket.current_location = to_location
        ticket.status = TicketStatus.WAITING
        ticket.assigned_user_id = None
        ticket.late_at = None
        ticket.completed_at = None
        self._audit(
            ticket=ticket,
            actor=actor,
            action=TransferAction.TRANSFER,
            from_location=previous,
            to_location=to_location,
            note=note,
        )
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError("TICKET_UPDATE_CONFLICT", "The transfer could not be saved.") from exc
        return TicketMutation(ticket=ticket, event="ticket.transferred", previous_location=previous)

    async def mark_late(
        self,
        actor: User,
        *,
        ticket_id: int | None,
        ticket_code: int | None,
        note: str | None = None,
    ) -> TicketMutation:
        ticket = await self._load_ticket(ticket_id, ticket_code, for_update=True)
        if ticket.status == TicketStatus.DONE:
            raise ConflictError("TICKET_CLOSED", "A completed ticket cannot be marked late.")
        self._assert_station_access(actor, ticket.current_location)
        if ticket.status == TicketStatus.LATE:
            return TicketMutation(ticket=ticket, event="ticket.late")

        now = utcnow()
        ticket.status = TicketStatus.LATE
        ticket.late_at = now
        ticket.assigned_user_id = None
        self._audit(
            ticket=ticket,
            actor=actor,
            action=TransferAction.LATE,
            from_location=ticket.current_location,
            to_location=ticket.current_location,
            at=now,
            note=note,
        )
        await self.session.commit()
        return TicketMutation(ticket=ticket, event="ticket.late")

    async def recall(
        self,
        actor: User,
        *,
        ticket_id: int | None,
        ticket_code: int | None,
        note: str | None = None,
    ) -> TicketMutation:
        ticket = await self._load_ticket(ticket_id, ticket_code, for_update=True)
        if ticket.status != TicketStatus.LATE:
            raise ConflictError("TICKET_NOT_LATE", "Only a late ticket can be recalled.")
        self._assert_station_access(actor, ticket.current_location)

        ticket.status = TicketStatus.WAITING
        ticket.late_at = None
        self._audit(
            ticket=ticket,
            actor=actor,
            action=TransferAction.RECALL,
            from_location=ticket.current_location,
            to_location=ticket.current_location,
            note=note,
        )
        await self.session.commit()
        return TicketMutation(ticket=ticket, event="ticket.recalled")

    async def complete(
        self,
        actor: User,
        *,
        ticket_id: int | None,
        ticket_code: int | None,
        note: str | None = None,
    ) -> TicketMutation:
        ticket = await self._load_ticket(ticket_id, ticket_code, for_update=True)
        if ticket.status == TicketStatus.DONE:
            return TicketMutation(ticket=ticket, event="ticket.completed")
        self._assert_station_access(actor, ticket.current_location)

        now = utcnow()
        ticket.status = TicketStatus.DONE
        ticket.completed_at = now
        if ticket.assigned_user_id is None:
            ticket.assigned_user_id = actor.id
        self._audit(
            ticket=ticket,
            actor=actor,
            action=TransferAction.DONE,
            from_location=ticket.current_location,
            to_location=ticket.current_location,
            at=now,
            note=note,
        )
        await self.session.commit()
        return TicketMutation(ticket=ticket, event="ticket.completed")

    async def serve_next(self, actor: User, station: Location | None = None) -> TicketMutation:
        target_station = self._resolve_station(actor, station)
        ticket = await self.session.scalar(
            select(Ticket)
            .where(
                Ticket.current_location == target_station,
                Ticket.status.in_((TicketStatus.WAITING, TicketStatus.LATE)),
            )
            .order_by(*_queue_order())
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if ticket is None:
            raise NotFoundError("Waiting ticket", "NO_WAITING_TICKETS")

        ticket.status = TicketStatus.SERVING
        ticket.assigned_user_id = actor.id
        self._audit(
            ticket=ticket,
            actor=actor,
            action=TransferAction.SERVING,
            from_location=ticket.current_location,
            to_location=ticket.current_location,
        )
        await self.session.commit()
        return TicketMutation(ticket=ticket, event="ticket.serving")

    # ------------------------------------------------------------------ reads
    async def get_ticket(
        self,
        *,
        ticket_id: int | None = None,
        ticket_code: int | None = None,
    ) -> Ticket:
        return await self._load_ticket(ticket_id, ticket_code, for_update=False)

    async def queue(self, station: Location) -> QueueResponse:
        tickets = (
            await self.session.scalars(
                select(Ticket)
                .where(
                    Ticket.current_location == station,
                    Ticket.status != TicketStatus.DONE,
                )
                .order_by(*_queue_order())
            )
        ).all()
        serving = [ticket for ticket in tickets if ticket.status == TicketStatus.SERVING]
        waiting = [ticket for ticket in tickets if ticket.status == TicketStatus.WAITING]
        late = [ticket for ticket in tickets if ticket.status == TicketStatus.LATE]
        return QueueResponse(
            station=station,
            serving=[TicketRead.model_validate(ticket) for ticket in serving],
            waiting=[TicketRead.model_validate(ticket) for ticket in waiting],
            late=[TicketRead.model_validate(ticket) for ticket in late],
            total_active=len(tickets),
            waiting_count=len(waiting),
            late_count=len(late),
            generated_at=utcnow(),
        )

    async def queue_summaries(self) -> list[QueueSummary]:
        rows = (
            await self.session.execute(
                select(
                    Ticket.current_location,
                    Ticket.status,
                    func.count(Ticket.id),
                )
                .where(Ticket.status != TicketStatus.DONE)
                .group_by(Ticket.current_location, Ticket.status)
            )
        ).all()
        counts: dict[Location, dict[TicketStatus, int]] = {}
        for station, status, count in rows:
            counts.setdefault(station, {})[status] = int(count)
        summaries: list[QueueSummary] = []
        for station in Location:
            station_counts = counts.get(station, {})
            serving = station_counts.get(TicketStatus.SERVING, 0)
            waiting = station_counts.get(TicketStatus.WAITING, 0)
            late = station_counts.get(TicketStatus.LATE, 0)
            summaries.append(
                QueueSummary(
                    station=station,
                    serving=serving,
                    waiting=waiting,
                    late=late,
                    total_active=serving + waiting + late,
                )
            )
        return summaries

    async def display_board(self, station: Location) -> DisplayBoardResponse:
        queue = await self.queue(station)
        waiting = queue.waiting + queue.late
        return DisplayBoardResponse(
            station=station,
            now_serving=queue.serving[0] if queue.serving else None,
            waiting_preview=waiting[:4],
            waiting_count=queue.waiting_count,
            late_count=queue.late_count,
            generated_at=queue.generated_at,
        )

    async def history(
        self,
        *,
        station: Location | None,
        status: TicketStatus | None,
        ticket_code: int | None,
        created_from: datetime | None,
        created_to: datetime | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Ticket], int]:
        filters = []
        if station is not None:
            filters.append(Ticket.current_location == station)
        if status is not None:
            filters.append(Ticket.status == status)
        if ticket_code is not None:
            filters.append(Ticket.ticket_code == ticket_code)
        if created_from is not None:
            filters.append(Ticket.created_at >= to_utc_naive(created_from))
        if created_to is not None:
            filters.append(Ticket.created_at <= to_utc_naive(created_to))

        total = await self.session.scalar(select(func.count(Ticket.id)).where(*filters))
        tickets = (
            await self.session.scalars(
                select(Ticket)
                .where(*filters)
                .order_by(Ticket.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
        ).all()
        return list(tickets), int(total or 0)

    # ---------------------------------------------------------------- internal
    async def _load_ticket(
        self,
        ticket_id: int | None,
        ticket_code: int | None,
        *,
        for_update: bool,
    ) -> Ticket:
        if ticket_id is None and ticket_code is None:
            raise ValidationError(
                "TICKET_LOCATOR_REQUIRED",
                "Provide either ticket_id or ticket_code.",
            )
        if ticket_id is not None:
            statement = select(Ticket).where(Ticket.id == ticket_id)
        else:
            statement = select(Ticket).where(Ticket.ticket_code == ticket_code).order_by(
                Ticket.created_at.desc()
            )
        if for_update:
            statement = statement.with_for_update()
        ticket = await self.session.scalar(statement.limit(1))
        if ticket is None:
            raise NotFoundError("Ticket", "TICKET_NOT_FOUND")
        if ticket_id is not None and ticket_code is not None and ticket.ticket_code != ticket_code:
            raise ValidationError(
                "TICKET_LOCATOR_MISMATCH",
                "ticket_id and ticket_code refer to different tickets.",
            )
        return ticket

    @staticmethod
    def _assert_station_access(actor: User, station: Location) -> None:
        if actor.role in (UserRole.ADMIN, UserRole.RECEPTION):
            return
        if actor.assigned_station != station:
            raise PermissionDeniedError(
                "You can only act on tickets currently at your assigned station."
            )

    @staticmethod
    def _resolve_station(actor: User, requested: Location | None) -> Location:
        if actor.role == UserRole.ADMIN:
            if requested is None:
                raise ValidationError(
                    "STATION_REQUIRED",
                    "Administrators must specify a station when calling the next ticket.",
                )
            return requested
        if requested is not None and requested != actor.assigned_station:
            raise PermissionDeniedError("You can only call tickets for your assigned station.")
        if actor.assigned_station is None:
            raise ValidationError("STATION_REQUIRED", "Your account has no assigned station.")
        return actor.assigned_station

    def _audit(
        self,
        *,
        ticket: Ticket,
        actor: User,
        action: TransferAction,
        from_location: Location | None,
        to_location: Location | None,
        at: datetime | None = None,
        note: str | None = None,
    ) -> None:
        self.session.add(
            TicketTransfer(
                ticket_id=ticket.id,
                from_location=from_location,
                to_location=to_location,
                transferred_by=actor.id,
                transferred_at=at or utcnow(),
                action_type=action,
                note=note,
            )
        )
