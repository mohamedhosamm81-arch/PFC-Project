"""Service-level integration tests against a real SQL schema.

These exercise transactions, generated-column uniqueness and queue ordering.
Run with:  pytest -m integration
"""

from __future__ import annotations

from datetime import timedelta

import pytest

pytest.importorskip("greenlet")

from sqlalchemy import select  # noqa: E402

from app.core.exceptions import (  # noqa: E402
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from app.core.time import facility_today, utcnow  # noqa: E402
from app.db.session import SessionFactory  # noqa: E402
from app.models.employee_session import EmployeeSession  # noqa: E402
from app.models.enums import Location, TicketStatus, TransferAction, UserRole  # noqa: E402
from app.models.ticket import Ticket  # noqa: E402
from app.models.ticket_sequence import TicketSequence  # noqa: E402
from app.models.ticket_transfer import TicketTransfer  # noqa: E402
from app.schemas.session import SessionStartRequest  # noqa: E402
from app.services.reports_service import ReportService  # noqa: E402
from app.services.session_service import SessionService  # noqa: E402
from app.services.ticket_service import TicketService  # noqa: E402
from tests.helpers import create_user  # noqa: E402

pytestmark = pytest.mark.integration


async def test_codes_roll_over_from_999_and_skip_active_codes(database):
    async with SessionFactory() as session:
        reception = await create_user(
            session, "reception", UserRole.RECEPTION, Location.RECEPTION
        )
        sequence = await session.get(TicketSequence, 1)
        sequence.next_ticket_code = 999
        await session.commit()

        service = TicketService(session)
        first = await service.issue(reception, Location.RECEPTION)
        second = await service.issue(reception, Location.RECEPTION)
        third = await service.issue(reception, Location.RECEPTION)

        assert [first.ticket.ticket_code, second.ticket.ticket_code, third.ticket.ticket_code] == [
            999,
            1,
            2,
        ]
        sequence = await session.get(TicketSequence, 1)
        assert sequence.next_ticket_code == 3


async def test_issue_with_every_initial_destination(database):
    async with SessionFactory() as session:
        reception = await create_user(
            session, "reception", UserRole.RECEPTION, Location.RECEPTION
        )
        service = TicketService(session)
        issued = [
            (await service.issue(reception, destination)).ticket
            for destination in (
                Location.RECEPTION,
                Location.CMO,
                Location.PHARMACY,
                Location.LABORATORY,
                Location.RADIOLOGY,
            )
        ]
        assert {ticket.initial_destination for ticket in issued} == {
            Location.RECEPTION,
            Location.CMO,
            Location.PHARMACY,
            Location.LABORATORY,
            Location.RADIOLOGY,
        }
        assert all(ticket.status == TicketStatus.WAITING for ticket in issued)


async def test_cashier_ticket_cannot_be_issued_at_the_kiosk(database):
    async with SessionFactory() as session:
        reception = await create_user(
            session, "reception", UserRole.RECEPTION, Location.RECEPTION
        )
        with pytest.raises(ValidationError) as exc:
            await TicketService(session).issue(reception, Location.CASHIER)
        assert exc.value.code == "CASHIER_NOT_INITIAL_DESTINATION"


async def test_transfer_to_cashier_records_audit_and_blocks_closed_tickets(database):
    async with SessionFactory() as session:
        reception = await create_user(
            session, "reception", UserRole.RECEPTION, Location.RECEPTION
        )
        service = TicketService(session)
        ticket = (await service.issue(reception, Location.RECEPTION)).ticket

        mutation = await service.transfer(
            reception,
            ticket_id=ticket.id,
            ticket_code=None,
            to_location=Location.CASHIER,
            note="Patient pays after consultation",
        )
        assert mutation.ticket.current_location == Location.CASHIER
        assert mutation.ticket.status == TicketStatus.WAITING
        assert mutation.previous_location == Location.RECEPTION

        with pytest.raises(ValidationError) as exc:
            await service.transfer(
                reception,
                ticket_id=ticket.id,
                ticket_code=None,
                to_location=Location.CASHIER,
            )
        assert exc.value.code == "SAME_DESTINATION"

        completed = await service.complete(reception, ticket_id=ticket.id, ticket_code=None)
        assert completed.ticket.status == TicketStatus.DONE
        assert completed.ticket.completed_at is not None

        with pytest.raises(ConflictError) as exc:
            await service.transfer(
                reception,
                ticket_id=ticket.id,
                ticket_code=None,
                to_location=Location.PHARMACY,
            )
        assert exc.value.code == "TICKET_CLOSED"

        actions = (
            await session.scalars(
                select(TicketTransfer.action_type)
                .where(TicketTransfer.ticket_id == ticket.id)
                .order_by(TicketTransfer.id.asc())
            )
        ).all()
        assert actions == [
            TransferAction.ISSUED,
            TransferAction.TRANSFER,
            TransferAction.DONE,
        ]


async def test_late_tickets_queue_behind_on_time_patients(database):
    async with SessionFactory() as session:
        reception = await create_user(
            session, "reception", UserRole.RECEPTION, Location.RECEPTION
        )
        service = TicketService(session)
        first = (await service.issue(reception, Location.RECEPTION)).ticket
        second = (await service.issue(reception, Location.RECEPTION)).ticket

        late = await service.mark_late(reception, ticket_id=first.id, ticket_code=None)
        assert late.ticket.status == TicketStatus.LATE
        assert late.ticket.late_at is not None

        # The on-time ticket created later is still called first.
        served = await service.serve_next(reception)
        assert served.ticket.id == second.id
        assert served.ticket.status == TicketStatus.SERVING

        await service.complete(reception, ticket_id=second.id, ticket_code=None)
        recalled = await service.serve_next(reception)
        assert recalled.ticket.id == first.id
        assert recalled.ticket.status == TicketStatus.SERVING


async def test_late_ticket_can_be_recalled_to_the_normal_queue(database):
    async with SessionFactory() as session:
        reception = await create_user(
            session, "reception", UserRole.RECEPTION, Location.RECEPTION
        )
        service = TicketService(session)
        ticket = (await service.issue(reception, Location.RECEPTION)).ticket
        await service.mark_late(reception, ticket_id=ticket.id, ticket_code=None)

        recalled = await service.recall(reception, ticket_id=ticket.id, ticket_code=None)
        assert recalled.ticket.status == TicketStatus.WAITING
        assert recalled.ticket.late_at is None
        assert recalled.event == "ticket.recalled"


async def test_completed_ticket_codes_are_reusable(database):
    async with SessionFactory() as session:
        reception = await create_user(
            session, "reception", UserRole.RECEPTION, Location.RECEPTION
        )
        service = TicketService(session)
        first = (await service.issue(reception, Location.RECEPTION)).ticket
        assert first.ticket_code == 1
        await service.complete(reception, ticket_id=first.id, ticket_code=None)

        sequence = await session.get(TicketSequence, 1)
        sequence.next_ticket_code = 1
        await session.commit()

        reused = (await service.issue(reception, Location.RECEPTION)).ticket
        assert reused.ticket_code == 1
        assert reused.id != first.id
        assert reused.status == TicketStatus.WAITING


async def test_serve_next_ignores_done_tickets(database):
    async with SessionFactory() as session:
        reception = await create_user(
            session, "reception", UserRole.RECEPTION, Location.RECEPTION
        )
        service = TicketService(session)
        ticket = (await service.issue(reception, Location.RECEPTION)).ticket
        await service.complete(reception, ticket_id=ticket.id, ticket_code=None)

        with pytest.raises(NotFoundError) as exc:
            await service.serve_next(reception)
        assert exc.value.code == "NO_WAITING_TICKETS"


async def test_session_lateness_and_single_open_session(database):
    async with SessionFactory() as session:
        admin = await create_user(session, "admin", UserRole.ADMIN, None)
        doctor = await create_user(session, "doctor", UserRole.DOCTOR, Location.CMO)
        service = SessionService(session)

        scheduled = utcnow() - timedelta(minutes=40)
        record = await service.start(
            admin,
            SessionStartRequest(
                station=Location.CMO, shift_start_scheduled=scheduled
            ),
        )
        assert record.is_late_start is True
        assert record.late_minutes == 25

        with pytest.raises(ConflictError) as exc:
            await service.start(admin, SessionStartRequest(station=Location.CMO))
        assert exc.value.code == "ACTIVE_SESSION_EXISTS"

        # A non-admin may not backdate the scheduled start to erase lateness.
        with pytest.raises(PermissionDeniedError):
            await service.start(
                doctor,
                SessionStartRequest(
                    station=Location.CMO,
                    shift_start_scheduled=utcnow() - timedelta(minutes=120),
                ),
            )

        ended = await service.end(admin)
        assert ended.end_session_at is not None

        within_grace = await service.start(
            admin,
            SessionStartRequest(
                station=Location.CMO,
                shift_start_scheduled=utcnow() - timedelta(minutes=10),
            ),
        )
        assert within_grace.is_late_start is False
        assert within_grace.late_minutes == 0


async def test_attendance_report_aggregates_sessions_and_served_tickets(database):
    async with SessionFactory() as session:
        staff = await create_user(
            session, "pharmacy.staff", UserRole.BRANCH_STAFF, Location.PHARMACY
        )
        now = utcnow()
        session.add(
            EmployeeSession(
                user_id=staff.id,
                station=Location.PHARMACY,
                shift_start_scheduled=now - timedelta(minutes=30),
                start_session_at=now - timedelta(minutes=20),
                end_session_at=now - timedelta(minutes=5),
                is_late_start=True,
                late_minutes=5,
            )
        )
        session.add(
            Ticket(
                ticket_code=1,
                initial_destination=Location.PHARMACY,
                current_location=Location.PHARMACY,
                status=TicketStatus.DONE,
                is_overbooked=False,
                assigned_user_id=staff.id,
                created_at=now - timedelta(minutes=25),
                updated_at=now - timedelta(minutes=1),
                completed_at=now - timedelta(minutes=1),
            )
        )
        await session.commit()

        report = await ReportService(session).attendance_report(
            start_date=facility_today(),
            end_date=facility_today(),
            station=Location.PHARMACY,
        )

        assert len(report.rows) == 1
        row = report.rows[0]
        assert row.session_count == 1
        assert row.late_minutes == 5
        assert row.served == 1
        assert report.total_sessions == 1
        assert report.total_late_minutes == 5
        assert report.total_served == 1
        assert report.pdf.startswith(b"%PDF")
