"""PDF attendance and activity report download."""

from __future__ import annotations

from datetime import date
from io import BytesIO

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_roles
from app.core.exceptions import ValidationError
from app.core.time import facility_today
from app.db.session import get_db_session
from app.models.enums import Location, UserRole
from app.services.reports_service import ReportService

router = APIRouter(
    prefix="/admin/reports",
    tags=["Reports"],
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)


@router.get(
    "/attendance.pdf",
    response_class=StreamingResponse,
    responses={200: {"content": {"application/pdf": {}}}},
    summary="Download an attendance and activity PDF report",
)
async def attendance_pdf(
    start_date: date | None = Query(default=None, description="Inclusive local date"),
    end_date: date | None = Query(default=None, description="Inclusive local date"),
    station: Location | None = None,
    user_id: int | None = Query(default=None, ge=1),
    session: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
    today = facility_today()
    start = start_date or today.replace(day=1)
    end = end_date or today
    if start > end:
        raise ValidationError("INVALID_DATE_RANGE", "start_date must be on or before end_date.")
    if (end - start).days > 366:
        raise ValidationError(
            "REPORT_RANGE_TOO_LARGE",
            "Reports are limited to a maximum range of 366 days.",
        )

    report = await ReportService(session).attendance_report(
        start_date=start,
        end_date=end,
        station=station,
        user_id=user_id,
    )
    filename = f"pfc-attendance-{start.isoformat()}-to-{end.isoformat()}.pdf"
    return StreamingResponse(
        BytesIO(report.pdf),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Report-Rows": str(len(report.rows)),
            "Cache-Control": "no-store",
        },
    )
