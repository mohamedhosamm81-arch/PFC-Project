"""Schema invariants and role/station queue rules."""

from __future__ import annotations

import pytest
from sqlalchemy import CheckConstraint, select
from sqlalchemy.dialects import mysql

import app.models  # noqa: F401  (register all tables)
from app.core.constants import INITIAL_DESTINATIONS
from app.core.exceptions import PermissionDeniedError, ValidationError
from app.db.base import Base
from app.models.enums import Location, UserRole
from app.models.ticket import Ticket
from app.services.ticket_service import TicketService, _queue_order
from tests.helpers import detached_user


def test_all_required_tables_are_registered():
    tables = set(Base.metadata.tables)
    assert {
        "users",
        "employee_sessions",
        "tickets",
        "ticket_transfers",
        "ticket_sequence",
        "rooms",
    }.issubset(tables)


def test_tickets_have_the_required_composite_index():
    index = next(
        item
        for item in Base.metadata.tables["tickets"].indexes
        if item.name == "ix_tickets_current_location_status"
    )
    assert [column.name for column in index.columns] == ["current_location", "status"]


def test_active_code_and_active_session_uniqueness_are_enforced_by_generated_columns():
    tickets = Base.metadata.tables["tickets"]
    sessions = Base.metadata.tables["employee_sessions"]

    ticket_index = next(
        item
        for item in tickets.indexes
        if item.name == "uq_tickets_active_ticket_code"
    )
    session_index = next(
        item
        for item in sessions.indexes
        if item.name == "uq_employee_sessions_active_user"
    )
    assert ticket_index.unique is True
    assert session_index.unique is True
    assert tickets.columns["active_ticket_code"].computed is not None
    assert sessions.columns["active_user_id"].computed is not None


def test_cashier_is_not_an_initial_destination():
    assert Location.CASHIER not in INITIAL_DESTINATIONS
    assert {
        Location.RECEPTION,
        Location.PHARMACY,
        Location.LABORATORY,
        Location.RADIOLOGY,
    }.issubset(INITIAL_DESTINATIONS)


def test_ticket_check_constraints_include_code_range_and_cashier_block():
    constraints = {
        constraint.name: str(constraint.sqltext)
        for constraint in Base.metadata.tables["tickets"].constraints
        if isinstance(constraint, CheckConstraint) and constraint.name
    }
    assert "BETWEEN 1 AND 999" in constraints["ck_tickets_code_range"]
    assert "Cashier" in constraints["ck_tickets_cashier_not_initial"]


def test_queue_order_puts_serving_then_waiting_then_late():
    statement = select(Ticket).order_by(*_queue_order())
    compiled = str(
        statement.compile(
            dialect=mysql.dialect(), compile_kwargs={"literal_binds": True}
        )
    )
    assert "CASE" in compiled
    assert "SERVING" in compiled
    assert "WAITING" in compiled
    assert "LATE" in compiled
    assert "late_at" in compiled


def test_station_access_rules():
    doctor = detached_user(UserRole.DOCTOR, Location.CMO)
    cashier_staff = detached_user(UserRole.BRANCH_STAFF, Location.CASHIER)
    admin = detached_user(UserRole.ADMIN, None)
    reception = detached_user(UserRole.RECEPTION, Location.RECEPTION)

    TicketService._assert_station_access(admin, Location.CASHIER)
    TicketService._assert_station_access(reception, Location.LABORATORY)
    TicketService._assert_station_access(doctor, Location.CMO)
    TicketService._assert_station_access(cashier_staff, Location.CASHIER)

    with pytest.raises(PermissionDeniedError):
        TicketService._assert_station_access(doctor, Location.PHARMACY)
    with pytest.raises(PermissionDeniedError):
        TicketService._assert_station_access(cashier_staff, Location.CMO)


def test_resolve_station_rules():
    doctor = detached_user(UserRole.DOCTOR, Location.CMO)
    admin = detached_user(UserRole.ADMIN, None)

    assert TicketService._resolve_station(doctor, None) == Location.CMO
    assert TicketService._resolve_station(doctor, Location.CMO) == Location.CMO
    assert TicketService._resolve_station(admin, Location.RADIOLOGY) == Location.RADIOLOGY

    with pytest.raises(PermissionDeniedError):
        TicketService._resolve_station(doctor, Location.PHARMACY)
    with pytest.raises(ValidationError):
        TicketService._resolve_station(admin, None)


async def test_cashier_issue_is_rejected_before_any_database_work():
    service = TicketService(None)  # the rejection happens before the session is used
    with pytest.raises(ValidationError) as exc:
        await service.issue(detached_user(UserRole.RECEPTION, Location.RECEPTION), Location.CASHIER)
    assert exc.value.code == "CASHIER_NOT_INITIAL_DESTINATION"
