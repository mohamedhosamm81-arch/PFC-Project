"""Import every model so Base.metadata is complete for Alembic/tests."""

from app.models.employee_session import EmployeeSession
from app.models.enums import Location, TicketStatus, TransferAction, UserRole
from app.models.room import Room
from app.models.ticket import Ticket
from app.models.ticket_sequence import TicketSequence
from app.models.ticket_transfer import TicketTransfer
from app.models.user import User

__all__ = [
    "EmployeeSession",
    "Location",
    "Room",
    "Ticket",
    "TicketSequence",
    "TicketStatus",
    "TicketTransfer",
    "TransferAction",
    "User",
    "UserRole",
]
