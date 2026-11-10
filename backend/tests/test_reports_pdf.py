"""PDF rendering smoke tests (no database required)."""

from __future__ import annotations

from datetime import date, datetime

from app.models.enums import Location
from app.services.reports_service import AttendanceRow, ReportService


def _rows() -> list[AttendanceRow]:
    return [
        AttendanceRow(
            user_id=1,
            username="doctor.layla",
            full_name="Dr. Layla Hassan",
            role="doctor",
            station=Location.CMO,
            session_count=2,
            late_minutes=12,
            served=9,
            last_start=datetime(2026, 1, 15, 8, 20),
            last_end=None,
            is_active=True,
        ),
        AttendanceRow(
            user_id=2,
            username="pharmacy.staff",
            full_name="Sara Youssef",
            role="branch_staff",
            station=Location.PHARMACY,
            session_count=1,
            late_minutes=0,
            served=4,
            last_start=datetime(2026, 1, 15, 8, 0),
            last_end=datetime(2026, 1, 15, 14, 0),
            is_active=True,
        ),
    ]


def test_report_builds_a_valid_pdf_and_totals():
    report = ReportService(None)._build_pdf(
        rows=_rows(),
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        station=None,
    )
    assert report.pdf.startswith(b"%PDF")
    assert len(report.pdf) > 1500
    assert report.total_sessions == 3
    assert report.total_late_minutes == 12
    assert report.total_served == 13
    assert len(report.rows) == 2


def test_report_handles_an_empty_scope():
    report = ReportService(None)._build_pdf(
        rows=[],
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 1),
        station=Location.CASHIER,
    )
    assert report.pdf.startswith(b"%PDF")
    assert report.rows == []
    assert report.total_sessions == 0
