"""Business constants shared by services, routes and seeds."""

from __future__ import annotations

from app.models.enums import Location

# Cashier is deliberately excluded. It is reachable only through an explicit
# transfer after the patient has completed another service.
INITIAL_DESTINATIONS: tuple[Location, ...] = (
    Location.RECEPTION,
    Location.CMO,
    Location.PHARMACY,
    Location.LABORATORY,
    Location.RADIOLOGY,
)

TRANSFER_DESTINATIONS: tuple[Location, ...] = tuple(Location)

DEPARTMENT_LABELS: dict[Location, str] = {
    Location.RECEPTION: "Reception / Screening",
    Location.CMO: "Clinic (CMO)",
    Location.PHARMACY: "Pharmacy",
    Location.LABORATORY: "Laboratory",
    Location.RADIOLOGY: "Radiology",
    Location.CASHIER: "Cashier",
}

TICKET_MIN_CODE = 1
TICKET_MAX_CODE = 999
TICKET_SEQUENCE_ID = 1

# Physical door/floor screens. These are seeded idempotently and can be
# changed later without code changes.
DEFAULT_ROOMS: tuple[dict[str, object], ...] = (
    {"code": "RECEPTION-01", "name": "Reception Desk", "floor_number": 1, "station": Location.RECEPTION},
    {"code": "ROOM-101", "name": "Clinic Room 101", "floor_number": 1, "station": Location.CMO},
    {"code": "ROOM-102", "name": "Clinic Room 102", "floor_number": 1, "station": Location.CMO},
    {"code": "ROOM-103", "name": "Clinic Room 103", "floor_number": 1, "station": Location.CMO},
    {"code": "PHARMACY-01", "name": "Pharmacy Counter", "floor_number": 1, "station": Location.PHARMACY},
    {"code": "LAB-01", "name": "Laboratory Bench", "floor_number": 1, "station": Location.LABORATORY},
    {"code": "RAD-01", "name": "Radiology Suite", "floor_number": 1, "station": Location.RADIOLOGY},
    {"code": "CASHIER-01", "name": "Cashier Window", "floor_number": 1, "station": Location.CASHIER},
    {"code": "ROOM-201", "name": "Clinic Room 201", "floor_number": 2, "station": Location.CMO},
)
