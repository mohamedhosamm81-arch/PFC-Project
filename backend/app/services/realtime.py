"""Realtime fan-out for queue displays and staff consoles."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from sqlalchemy import select
from starlette.websockets import WebSocket

from app.core.time import isoformat_utc, utcnow
from app.models.enums import Location
from app.models.room import Room
from app.models.ticket import Ticket
from app.schemas.ticket import TicketRead

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("pfc.realtime")


@dataclass(eq=False)
class WSConnection:
    websocket: WebSocket
    user_id: int
    role: str
    station: str | None
    subscriptions: set[str] = field(default_factory=set)
    send_lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[WebSocket, WSConnection] = {}
        self._lock = asyncio.Lock()

    async def connect(self, connection: WSConnection) -> None:
        async with self._lock:
            self._connections[connection.websocket] = connection

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.pop(websocket, None)

    async def update_subscriptions(
        self, connection: WSConnection, *, add: set[str] | None = None, remove: set[str] | None = None
    ) -> None:
        async with self._lock:
            if add:
                connection.subscriptions.update(add)
            if remove:
                connection.subscriptions.difference_update(remove)

    async def send(self, connection: WSConnection, payload: dict) -> None:
        async with connection.send_lock:
            await connection.websocket.send_json(payload)

    async def broadcast(self, targets: set[str], payload: dict) -> None:
        if not targets:
            return
        async with self._lock:
            recipients = [
                connection
                for connection in self._connections.values()
                if connection.subscriptions.intersection(targets)
            ]
        if not recipients:
            return

        results = await asyncio.gather(
            *(self.send(connection, payload) for connection in recipients),
            return_exceptions=True,
        )
        dead: list[WebSocket] = []
        for connection, result in zip(recipients, results, strict=True):
            if isinstance(result, Exception):
                logger.debug("Dropping websocket after send failure: %s", result)
                dead.append(connection.websocket)
        for websocket in dead:
            await self.disconnect(websocket)

    async def count(self) -> int:
        async with self._lock:
            return len(self._connections)


connection_manager = ConnectionManager()


async def room_targets(session: AsyncSession, stations: set[Location]) -> set[str]:
    if not stations:
        return set()
    rows = (
        await session.execute(
            select(Room.floor_number, Room.code).where(
                Room.is_active.is_(True),
                Room.station.in_(tuple(stations)),
            )
        )
    ).all()
    targets: set[str] = set()
    for floor_number, room_code in rows:
        targets.add(f"floor:{floor_number}")
        targets.add(f"room:{room_code}")
    return targets


async def publish_ticket_event(
    session: AsyncSession,
    *,
    event: str,
    ticket: Ticket,
    previous_location: Location | None = None,
) -> None:
    """Publish after the database transaction has committed."""
    stations = {ticket.current_location}
    if previous_location is not None:
        stations.add(previous_location)
    targets = {f"station:{station.value}" for station in stations}
    targets.update(await room_targets(session, stations))

    payload = {
        "type": event,
        "ticket": TicketRead.model_validate(ticket).model_dump(mode="json"),
        "station": ticket.current_location.value,
        "previous_location": previous_location.value if previous_location else None,
        "emitted_at": isoformat_utc(utcnow()),
    }
    await connection_manager.broadcast(targets, payload)


async def publish_session_event(
    event: str,
    *,
    station: Location,
    user_id: int,
    full_name: str,
) -> None:
    payload = {
        "type": event,
        "user_id": user_id,
        "full_name": full_name,
        "station": station.value,
        "emitted_at": isoformat_utc(utcnow()),
    }
    await connection_manager.broadcast({f"station:{station.value}"}, payload)
