"""FastAPI application factory and process entrypoint."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.router import api_router
from app.api.routes import health, ws
from app.core.config import settings
from app.core.exceptions import AppError
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.db.session import check_database, dispose_engine

logger = logging.getLogger("pfc")


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    logger.info(
        "Starting %s %s env=%s timezone=%s",
        settings.app_name,
        settings.app_version,
        settings.app_env,
        settings.facility_timezone,
    )
    await check_database()
    yield
    await dispose_engine()
    logger.info("PFC backend stopped")


def create_app() -> FastAPI:
    app = FastAPI(
        title="PFC — Patient Flow Controller API",
        description=(
            "On-premises queue, routing, attendance and display-synchronisation API "
            "for the Patient Flow Controller."
        ),
        version=settings.app_version,
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url="/redoc" if settings.docs_enabled else None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
        lifespan=lifespan,
    )

    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID", "Content-Disposition", "X-Report-Rows"],
        max_age=600,
    )

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": jsonable_encoder(exc.details) if exc.details is not None else None,
                }
            },
            headers={"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "The request could not be validated.",
                    "details": jsonable_encoder(exc.errors()),
                }
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": f"HTTP_{exc.status_code}",
                    "message": str(exc.detail),
                    "details": None,
                }
            },
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        logger.exception("Unhandled error request_id=%s", request_id)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred.",
                    "details": {"request_id": request_id} if request_id else None,
                }
            },
        )

    app.include_router(health.router)
    app.include_router(api_router, prefix=settings.api_prefix)
    app.include_router(ws.router)

    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, str]:
        return {
            "service": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs" if settings.docs_enabled else "disabled",
            "health": "/health/ready",
        }

    return app


app = create_app()
