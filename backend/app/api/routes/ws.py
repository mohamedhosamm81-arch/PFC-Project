"""Authenticated WebSocket endpoint for queue/display synchronisation."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.core.config import settings
from app.core.security import decode_access_token
from app.core.time import isoformat_utc, utcnow
from app.db.session import SessionFactory
from app.models.enums import Location, UserRole
from app.models.room import Room
from app.models.user import User
from app.services.realtime import WSConnection, connection_manager
from app.services.ticket_service import TicketService

logger = logging.getLogger("pfc.ws")
router = APIRouter(tags=["Realtime"])


@dataclass(slots=True)
class WSIdentity:
    id: int
    role: UserRole
    station: Location | None
    full_name: str
    is_active: bool


@dataclass(frozen=True, slots=True)
class RoomRef:
    """Detached, read-only room snapshot safe to use after the session closes."""

    code: str
    name: str
    floor_number: int
    station: Location


async def _load_identity(token: str) -> WSIdentity | None:
    try:
        claims = decode_access_token(token)
        user_id = int(claims["sub"])
    except Exception:
        return None
    async with SessionFactory() as session:
        user = await session.get(User, user_id)
        if user is None or not user.is_active:
            return None
        return WSIdentity(
            id=user.id,
            role=user.role,
            station=user.assigned_station,
            full_name=user.full_name,
            is_active=user.is_active,
        )


def _station_allowed(identity: WSIdentity, station: Location) -> bool:
    if identity.role in (UserRole.ADMIN, UserRole.RECEPTION):
        return True
    return identity.station == station


async def _floor_allowed(identity: WSIdentity, floor_number: int) -> bool:
    if identity.role in (UserRole.ADMIN, UserRole.RECEPTION):
        return True
    if identity.station is None:
        return False
    async with SessionFactory() as session:
        room_id = await session.scalar(
            select(Room.id)
            .where(
                Room.floor_number == floor_number,
                Room.station == identity.station,
                Room.is_active.is_(True),
            )
            .limit(1)
        )
        return room_id is not None


async def _room_allowed(identity: WSIdentity, room_code: str) -> RoomRef | None:
    async with SessionFactory() as session:
        room = await session.scalar(select(Room).where(Room.code == room_code))
        if room is None or not room.is_active:
            return None
        if identity.role not in (UserRole.ADMIN, UserRole.RECEPTION) and (
            identity.station != room.station
        ):
            return None
        return RoomRef(
            code=room.code,
            name=room.name,
            floor_number=room.floor_number,
            station=room.station,
        )


async def _send(connection: WSConnection, payload: dict) -> bool:
    try:
        await connection_manager.send(connection, payload)
        return True
    except Exception:
        return False


async def _send_snapshot(connection: WSConnection, station: Location) -> bool:
    async with SessionFactory() as session:
        board = await TicketService(session).display_board(station)
        payload = board.model_dump(mode="json")
    return await _send(
        connection,
        {"type": "queue.snapshot", "station": station.value, "data": payload},
    )


async def _add_target(connection: WSConnection, target: str) -> bool:
    if target in connection.subscriptions:
        return True
    if len(connection.subscriptions) >= settings.max_ws_subscriptions:
        await _send(
            connection,
            {
                "type": "error",
                "code": "SUBSCRIPTION_LIMIT",
                "message": "Too many active subscriptions.",
            },
        )
        return False
    await connection_manager.update_subscriptions(connection, add={target})
    return True


@router.websocket("/ws/queues")
async def queue_socket(websocket: WebSocket) -> None:
    origin = websocket.headers.get("origin")
    allowed_origins = settings.ws_origins_list
    if origin and allowed_origins and origin not in allowed_origins:
        await websocket.accept()
        await websocket.close(code=4403, reason="Origin not allowed")
        return

    token = websocket.query_params.get("token")
    if not token:
        auth_header = websocket.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()
    if not token:
        await websocket.accept()
        await websocket.close(code=4401, reason="Missing access token")
        return

    identity = await _load_identity(token)
    if identity is None:
        await websocket.accept()
        await websocket.close(code=4401, reason="Invalid or expired access token")
        return

    await websocket.accept()
    connection = WSConnection(
        websocket=websocket,
        user_id=identity.id,
        role=identity.role.value,
        station=identity.station.value if identity.station else None,
    )
    await connection_manager.connect(connection)

    if not await _send(
        connection,
        {
            "type": "connected",
            "user_id": identity.id,
            "role": identity.role.value,
            "station": identity.station.value if identity.station else None,
            "server_time": isoformat_utc(utcnow()),
            "subscriptions": [],
        },
    ):
        await connection_manager.disconnect(websocket)
        return

    # Optional initial subscriptions are convenient for dedicated screens:
    #   /ws/queues?token=...&station=CMO&floor=1&room=ROOM-101
    raw_station = websocket.query_params.get("station")
    if raw_station:
        try:
            station_value = Location(raw_station)
        except ValueError:
            await _send(
                connection,
                {"type": "error", "code": "INVALID_STATION", "message": "Unknown station."},
            )
        else:
            if _station_allowed(identity, station_value):
                target = f"station:{station_value.value}"
                if await _add_target(connection, target):
                    await _send_snapshot(connection, station_value)
            else:
                await _send(
                    connection,
                    {
                        "type": "error",
                        "code": "STATION_FORBIDDEN",
                        "message": "You cannot subscribe to that station.",
                    },
                )

    raw_floor = websocket.query_params.get("floor")
    if raw_floor:
        try:
            floor_number = int(raw_floor)
        except ValueError:
            floor_number = 0
        if floor_number > 0 and await _floor_allowed(identity, floor_number):
            await _add_target(connection, f"floor:{floor_number}")
        else:
            await _send(
                connection,
                {"type": "error", "code": "FLOOR_FORBIDDEN", "message": "Floor is not available."},
            )

    raw_room = websocket.query_params.get("room")
    if raw_room:
        room_code = raw_room.strip().upper()
        room = await _room_allowed(identity, room_code)
        if room is not None:
            await _add_target(connection, f"room:{room.code}")
        else:
            await _send(
                connection,
                {"type": "error", "code": "ROOM_FORBIDDEN", "message": "Room is not available."},
            )

    if connection.subscriptions:
        await _send(
            connection,
            {
                "type": "subscriptions.updated",
                "subscriptions": sorted(connection.subscriptions),
            },
        )

    try:
        while True:
            try:
                raw = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=settings.ws_receive_timeout_seconds,
                )
            except TimeoutError:
                await websocket.close(code=4408, reason="Heartbeat timeout")
                break
            except WebSocketDisconnect:
                break

            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                await _send(
                    connection,
                    {"type": "error", "code": "INVALID_JSON", "message": "Message must be JSON."},
                )
                continue
            if not isinstance(message, dict):
                await _send(
                    connection,
                    {"type": "error", "code": "INVALID_MESSAGE", "message": "Expected an object."},
                )
                continue

            action = str(message.get("action", "ping")).lower()
            if action == "ping":
                await _send(connection, {"type": "pong", "server_time": isoformat_utc(utcnow())})
                continue

            if action == "unsubscribe":
                remove: set[str] = set()
                if message.get("station"):
                    try:
                        remove.add(f"station:{Location(str(message['station'])).value}")
                    except ValueError:
                        pass
                if message.get("floor") is not None:
                    try:
                        remove.add(f"floor:{int(message['floor'])}")
                    except (TypeError, ValueError):
                        pass
                if message.get("room"):
                    remove.add(f"room:{str(message['room']).strip().upper()}")
                await connection_manager.update_subscriptions(connection, remove=remove)
                await _send(
                    connection,
                    {
                        "type": "subscriptions.updated",
                        "subscriptions": sorted(connection.subscriptions),
                    },
                )
                continue

            if action != "subscribe":
                await _send(
                    connection,
                    {
                        "type": "error",
                        "code": "UNKNOWN_ACTION",
                        "message": "Supported actions: subscribe, unsubscribe, ping.",
                    },
                )
                continue

            changed = False
            station_value: Location | None = None
            if message.get("station"):
                try:
                    station_value = Location(str(message["station"]))
                except ValueError:
                    await _send(
                        connection,
                        {
                            "type": "error",
                            "code": "INVALID_STATION",
                            "message": "Unknown station.",
                        },
                    )
                else:
                    if _station_allowed(identity, station_value):
                        changed = await _add_target(
                            connection, f"station:{station_value.value}"
                        ) or changed
                    else:
                        await _send(
                            connection,
                            {
                                "type": "error",
                                "code": "STATION_FORBIDDEN",
                                "message": "You cannot subscribe to that station.",
                            },
                        )

            if message.get("floor") is not None:
                try:
                    floor_number = int(message["floor"])
                except (TypeError, ValueError):
                    floor_number = 0
                if floor_number > 0 and await _floor_allowed(identity, floor_number):
                    changed = await _add_target(connection, f"floor:{floor_number}") or changed
                else:
                    await _send(
                        connection,
                        {
                            "type": "error",
                            "code": "FLOOR_FORBIDDEN",
                            "message": "Floor is not available.",
                        },
                    )

            if message.get("room"):
                room_obj = await _room_allowed(
                    identity, str(message["room"]).strip().upper()
                )
                if room_obj is not None:
                    changed = await _add_target(connection, f"room:{room_obj.code}") or changed
                else:
                    await _send(
                        connection,
                        {
                            "type": "error",
                            "code": "ROOM_FORBIDDEN",
                            "message": "Room is not available.",
                        },
                    )

            await _send(
                connection,
                {
                    "type": "subscriptions.updated",
                    "subscriptions": sorted(connection.subscriptions),
                },
            )
            if station_value is not None and changed:
                await _send_snapshot(connection, station_value)
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("WebSocket failure user_id=%s", identity.id)
    finally:
        await connection_manager.disconnect(websocket)
