"""String-backed enums persisted as MySQL ENUM columns."""

from __future__ import annotations

from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    RECEPTION = "reception"
    DOCTOR = "doctor"
    BRANCH_STAFF = "branch_staff"


class Location(str, Enum):
    RECEPTION = "Reception"
    CMO = "CMO"
    PHARMACY = "Pharmacy"
    LABORATORY = "Laboratory"
    RADIOLOGY = "Radiology"
    CASHIER = "Cashier"


class TicketStatus(str, Enum):
    WAITING = "WAITING"
    SERVING = "SERVING"
    LATE = "LATE"
    DONE = "DONE"


class TransferAction(str, Enum):
    ISSUED = "ISSUED"
    SERVING = "SERVING"
    TRANSFER = "TRANSFER"
    LATE = "LATE"
    RECALL = "RECALL"
    DONE = "DONE"


def enum_values(enum_class: type[Enum]) -> list[str]:
    return [member.value for member in enum_class]
