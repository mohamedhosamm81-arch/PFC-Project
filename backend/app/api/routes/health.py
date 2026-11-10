"""Server health endpoints (not part of the /api surface)."""

from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.db.session import check_database

router = APIRouter(tags=["Health"])
logger = logging.getLogger("pfc.health")


@router.get("/health/live", summary="Liveness probe")
async def live() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name, "version": settings.app_version}


@router.get("/health/ready", summary="Readiness probe including MySQL")
async def ready() -> JSONResponse:
    try:
        await check_database()
    except Exception:
        logger.exception("Readiness check failed")
        return JSONResponse(status_code=503, content={"status": "unavailable", "database": "down"})
    return JSONResponse(content={"status": "ok", "database": "up"})
