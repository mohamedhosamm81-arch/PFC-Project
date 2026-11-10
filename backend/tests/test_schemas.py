"""Request validation and response serialisation contracts."""

from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError as PydanticValidationError

from app.models.enums import Location, TicketStatus, UserRole
from app.schemas.ticket import IssueTicketRequest, TicketLocator, TicketRead
from app.schemas.user import UserCreate


def test_ticket_locator_requires_at_least_one_identifier():
    with pytest.raises(PydanticValidationError):
        TicketLocator()


def test_ticket_locator_accepts_a_code():
    locator = TicketLocator(ticket_code=345)
    assert locator.ticket_code == 345


def test_ticket_code_must_be_in_circular_range():
    with pytest.raises(PydanticValidationError):
        TicketLocator(ticket_code=1000)


def test_user_creation_enforces_password_strength_and_username_rules():
    with pytest.raises(PydanticValidationError):
        UserCreate(
            username="reception",
            password="short",
            full_name="Reception Desk",
            role=UserRole.RECEPTION,
            assigned_station=Location.RECEPTION,
        )
    with pytest.raises(PydanticValidationError):
        UserCreate(
            username="bad user!",
            password="GoodPass123",
            full_name="Bad User",
            role=UserRole.RECEPTION,
            assigned_station=Location.RECEPTION,
        )


def test_issue_request_rejects_unknown_destination():
    with pytest.raises(PydanticValidationError):
        IssueTicketRequest(initial_destination="Emergency")


def test_ticket_read_serialises_utc_timestamps_with_z_suffix():
    ticket = TicketRead(
        id=1,
        ticket_code=17,
        initial_destination=Location.RECEPTION,
        current_location=Location.CASHIER,
        status=TicketStatus.WAITING,
        is_overbooked=False,
        assigned_user_id=None,
        late_at=None,
        created_at=datetime(2026, 1, 15, 10, 30, 0),
        completed_at=None,
    )
    payload = ticket.model_dump(mode="json")
    assert payload["created_at"] == "2026-01-15T10:30:00Z"
    assert payload["current_location"] == "Cashier"
    assert payload["status"] == "WAITING"
