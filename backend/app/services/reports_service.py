"""Attendance and activity PDF reporting."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from io import BytesIO
from typing import TYPE_CHECKING
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import func, select

from app.core.time import as_utc, facility_tz, local_day_bounds, utcnow
from app.models.employee_session import EmployeeSession
from app.models.enums import Location, TicketStatus, UserRole
from app.models.ticket import Ticket
from app.models.user import User

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(slots=True)
class AttendanceRow:
    user_id: int
    username: str
    full_name: str
    role: str
    station: Location | None
    session_count: int
    late_minutes: int
    served: int
    last_start: datetime | None
    last_end: datetime | None
    is_active: bool


@dataclass(slots=True)
class AttendanceReport:
    rows: list[AttendanceRow]
    start_date: date
    end_date: date
    station: Location | None
    total_sessions: int
    total_late_minutes: int
    total_served: int
    generated_at: datetime
    pdf: bytes


class ReportService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def attendance_report(
        self,
        *,
        start_date: date,
        end_date: date,
        station: Location | None = None,
        user_id: int | None = None,
    ) -> AttendanceReport:
        range_start, _ = local_day_bounds(start_date)
        _, range_end = local_day_bounds(end_date)

        user_filters = [User.role != UserRole.ADMIN]
        if station is not None:
            user_filters.append(User.assigned_station == station)
        if user_id is not None:
            user_filters.append(User.id == user_id)
        users = list(
            (
                await self.session.scalars(
                    select(User)
                    .where(*user_filters)
                    .order_by(User.assigned_station.asc(), User.full_name.asc())
                    .limit(1000)
                )
            ).all()
        )
        user_ids = [user.id for user in users]
        if not user_ids:
            return self._build_pdf(
                rows=[],
                start_date=start_date,
                end_date=end_date,
                station=station,
            )

        session_rows = list(
            (
                await self.session.scalars(
                    select(EmployeeSession)
                    .where(
                        EmployeeSession.user_id.in_(user_ids),
                        EmployeeSession.start_session_at >= range_start,
                        EmployeeSession.start_session_at < range_end,
                    )
                    .order_by(EmployeeSession.start_session_at.asc())
                )
            ).all()
        )

        served_rows = (
            await self.session.execute(
                select(Ticket.assigned_user_id, func.count(Ticket.id))
                .where(
                    Ticket.assigned_user_id.in_(user_ids),
                    Ticket.status == TicketStatus.DONE,
                    Ticket.completed_at >= range_start,
                    Ticket.completed_at < range_end,
                )
                .group_by(Ticket.assigned_user_id)
            )
        ).all()
        served_by_user = {int(user_id_): int(count) for user_id_, count in served_rows if user_id_}

        sessions_by_user: dict[int, list[EmployeeSession]] = {}
        for record in session_rows:
            sessions_by_user.setdefault(record.user_id, []).append(record)

        rows: list[AttendanceRow] = []
        for user in users:
            records = sessions_by_user.get(user.id, [])
            last = records[-1] if records else None
            rows.append(
                AttendanceRow(
                    user_id=user.id,
                    username=user.username,
                    full_name=user.full_name,
                    role=user.role.value,
                    station=user.assigned_station,
                    session_count=len(records),
                    late_minutes=sum(record.late_minutes for record in records),
                    served=served_by_user.get(user.id, 0),
                    last_start=last.start_session_at if last else None,
                    last_end=last.end_session_at if last else None,
                    is_active=user.is_active,
                )
            )

        return self._build_pdf(
            rows=rows,
            start_date=start_date,
            end_date=end_date,
            station=station,
        )

    def _build_pdf(
        self,
        *,
        rows: list[AttendanceRow],
        start_date: date,
        end_date: date,
        station: Location | None,
    ) -> AttendanceReport:
        generated_at = utcnow()
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            leftMargin=14 * mm,
            rightMargin=14 * mm,
            topMargin=16 * mm,
            bottomMargin=15 * mm,
            title="PFC Attendance & Activity Report",
            author="Patient Flow Controller",
        )
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "PFCTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=17,
            leading=21,
            textColor=colors.HexColor("#10233f"),
            alignment=0,
        )
        subtitle_style = ParagraphStyle(
            "PFCSubtitle",
            parent=styles["Normal"],
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#667085"),
        )
        cell_style = ParagraphStyle(
            "PFCCell",
            parent=styles["Normal"],
            fontSize=7.5,
            leading=9.5,
        )
        header_style = ParagraphStyle(
            "PFCHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=9.5,
            textColor=colors.white,
        )

        zone = facility_tz()

        def local_time(value: datetime | None) -> str:
            if value is None:
                return "—"
            return as_utc(value).astimezone(zone).strftime("%Y-%m-%d %H:%M")

        story = [
            Paragraph("PFC Attendance &amp; Activity Report", title_style),
            Paragraph(
                "Egypt Healthcare Authority · Patient Flow Controller",
                subtitle_style,
            ),
            Spacer(1, 2 * mm),
            Paragraph(
                f"Period: {start_date.isoformat()} to {end_date.isoformat()} · "
                f"Scope: {escape(station.value) if station else 'All departments'} · "
                f"Generated: {local_time(generated_at)}",
                subtitle_style,
            ),
            Spacer(1, 4 * mm),
        ]

        total_sessions = sum(row.session_count for row in rows)
        total_late = sum(row.late_minutes for row in rows)
        total_served = sum(row.served for row in rows)
        summary_data = [
            [
                Paragraph("<b>Employees</b>", cell_style),
                Paragraph("<b>Sessions</b>", cell_style),
                Paragraph("<b>Lateness</b>", cell_style),
                Paragraph("<b>Tickets served</b>", cell_style),
            ],
            [
                Paragraph(str(len(rows)), cell_style),
                Paragraph(str(total_sessions), cell_style),
                Paragraph(f"{total_late} min", cell_style),
                Paragraph(str(total_served), cell_style),
            ],
        ]
        summary = Table(summary_data, colWidths=[45 * mm] * 4, hAlign="LEFT")
        summary.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef4f7")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#dbe4ec")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#dbe4ec")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.extend([summary, Spacer(1, 5 * mm)])

        header = [
            Paragraph("Employee", header_style),
            Paragraph("Role / username", header_style),
            Paragraph("Station", header_style),
            Paragraph("Sessions", header_style),
            Paragraph("Late", header_style),
            Paragraph("Served", header_style),
            Paragraph("Last start", header_style),
            Paragraph("Last end", header_style),
            Paragraph("Status", header_style),
        ]
        data = [header]
        for row in rows:
            data.append(
                [
                    Paragraph(escape(row.full_name), cell_style),
                    Paragraph(f"{escape(row.role)}<br/>{escape(row.username)}", cell_style),
                    Paragraph(escape(row.station.value) if row.station else "—", cell_style),
                    Paragraph(str(row.session_count), cell_style),
                    Paragraph(f"{row.late_minutes} min", cell_style),
                    Paragraph(str(row.served), cell_style),
                    Paragraph(local_time(row.last_start), cell_style),
                    Paragraph(local_time(row.last_end) if row.last_end else "Active", cell_style),
                    Paragraph("Active" if row.is_active else "Disabled", cell_style),
                ]
            )
        if len(data) == 1:
            data.append(
                [
                    Paragraph("No employees matched the selected filters.", cell_style),
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                ]
            )

        table = Table(
            data,
            repeatRows=1,
            colWidths=[42 * mm, 35 * mm, 24 * mm, 17 * mm, 17 * mm, 18 * mm, 34 * mm, 34 * mm, 20 * mm],
            hAlign="LEFT",
        )
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#10233f")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#dbe4ec")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e5ebf1")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(table)

        def draw_footer(canvas, document) -> None:
            canvas.saveState()
            canvas.setStrokeColor(colors.HexColor("#dbe4ec"))
            canvas.line(14 * mm, 11 * mm, 283 * mm, 11 * mm)
            canvas.setFont("Helvetica", 7)
            canvas.setFillColor(colors.HexColor("#667085"))
            canvas.drawString(14 * mm, 7 * mm, "PFC · Confidential operational report")
            canvas.drawRightString(283 * mm, 7 * mm, f"Page {document.page}")
            canvas.restoreState()

        doc.build(story, onFirstPage=draw_footer, onLaterPages=draw_footer)
        pdf = buffer.getvalue()
        buffer.close()
        return AttendanceReport(
            rows=rows,
            start_date=start_date,
            end_date=end_date,
            station=station,
            total_sessions=total_sessions,
            total_late_minutes=total_late,
            total_served=total_served,
            generated_at=generated_at,
            pdf=pdf,
        )
