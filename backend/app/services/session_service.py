"""Shift session lifecycle and attendance calculations."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError, ValidationError
from app.core.time import default_scheduled_start, to_utc_naive, utcnow
from app.models.employee_session import EmployeeSession
from app.models.enums import Location, UserRole
from app.models.user import User
from app.schemas.session import SessionStartRequest

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


def compute_lateness(
    start_session_at: datetime,
    shift_start_scheduled: datetime,
    grace_minutes: int | None = None,
) -> tuple[int, bool]:
    """Return (late_minutes, is_late_start) using the facility grace rule."""
    grace = settings.attendance_grace_minutes if grace_minutes is None else grace_minutes
    elapsed_minutes = int((start_session_at - shift_start_scheduled).total_seconds() // 60)
    late_minutes = max(0, elapsed_minutes - grace)
    return late_minutes, late_minutes > 0


class SessionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def start(self, actor: User, payload: SessionStartRequest) -> EmployeeSession:
        station = self._resolve_station(actor, payload.station)
        if payload.shift_start_scheduled is not None and actor.role != UserRole.ADMIN:
            # Employees must not be able to backdate their shift to erase
            # lateness. Managers configure `default_shift_start` per account;
            # only an administrator may override it for a single session.
            raise PermissionDeniedError(
                "Only administrators may override the scheduled shift start."
            )
        active = await self.session.scalar(
            select(EmployeeSession.id).where(
                EmployeeSession.user_id == actor.id,
                EmployeeSession.end_session_at.is_(None),
            )
        )
        if active is not None:
            raise ConflictError(
                "ACTIVE_SESSION_EXISTS",
                "You already have an open session. End it before starting another.",
            )

        now = utcnow()
        if payload.shift_start_scheduled is not None:
            scheduled = to_utc_naive(payload.shift_start_scheduled)
        else:
            scheduled = default_scheduled_start(actor.default_shift_start)
        late_minutes, is_late = compute_lateness(now, scheduled)

        record = EmployeeSession(
            user_id=actor.id,
            station=station,
            shift_start_scheduled=scheduled,
            start_session_at=now,
            is_late_start=is_late,
            late_minutes=late_minutes,
        )
        self.session.add(record)
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError(
                "ACTIVE_SESSION_EXISTS",
                "You already have an open session. End it before starting another.",
            ) from exc
        await self.session.refresh(record)
        return record

    async def end(self, actor: User) -> EmployeeSession:
        record = await self.session.scalar(
            select(EmployeeSession)
            .where(
                EmployeeSession.user_id == actor.id,
                EmployeeSession.end_session_at.is_(None),
            )
            .with_for_update()
        )
        if record is None:
            raise NotFoundError("Active session", "ACTIVE_SESSION_NOT_FOUND")
        record.end_session_at = utcnow()
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def current(self, user_id: int) -> EmployeeSession | None:
        return await self.session.scalar(
            select(EmployeeSession).where(
                EmployeeSession.user_id == user_id,
                EmployeeSession.end_session_at.is_(None),
            )
        )

    async def list_for_user(
        self, user_id: int, *, limit: int, offset: int
    ) -> tuple[list[EmployeeSession], int]:
        total = await self.session.scalar(
            select(func.count(EmployeeSession.id)).where(EmployeeSession.user_id == user_id)
        )
        records = (
            await self.session.scalars(
                select(EmployeeSession)
                .where(EmployeeSession.user_id == user_id)
                .order_by(EmployeeSession.start_session_at.desc())
                .limit(limit)
                .offset(offset)
            )
        ).all()
        return list(records), int(total or 0)

    async def list_all(
        self,
        *,
        start_from: datetime | None,
        start_to: datetime | None,
        user_id: int | None,
        station: Location | None,
        active_only: bool,
        limit: int,
        offset: int,
    ) -> tuple[list[EmployeeSession], int]:
        filters = []
        if start_from is not None:
            filters.append(EmployeeSession.start_session_at >= to_utc_naive(start_from))
        if start_to is not None:
            filters.append(EmployeeSession.start_session_at <= to_utc_naive(start_to))
        if user_id is not None:
            filters.append(EmployeeSession.user_id == user_id)
        if station is not None:
            filters.append(EmployeeSession.station == station)
        if active_only:
            filters.append(EmployeeSession.end_session_at.is_(None))

        total = await self.session.scalar(
            select(func.count(EmployeeSession.id)).where(*filters)
        )
        records = (
            await self.session.scalars(
                select(EmployeeSession)
                .where(*filters)
                .order_by(EmployeeSession.start_session_at.desc())
                .limit(limit)
                .offset(offset)
            )
        ).all()
        return list(records), int(total or 0)

    def _resolve_station(self, actor: User, requested: Location | None) -> Location:
        if actor.role == UserRole.ADMIN:
            if requested is None:
                raise ValidationError(
                    "STATION_REQUIRED",
                    "Administrators must specify a station when starting a session.",
                )
            return requested

        if actor.assigned_station is None:
            raise ValidationError("STATION_REQUIRED", "Your account has no assigned station.")
        if requested is not None and requested != actor.assigned_station:
            raise PermissionDeniedError("You can only start a session at your assigned station.")
        return actor.assigned_station
