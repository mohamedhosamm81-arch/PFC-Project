"""API router composition."""

from fastapi import APIRouter

from app.api.routes import admin, auth, meta, queues, reports, sessions, tickets

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(sessions.router)
api_router.include_router(tickets.router)
api_router.include_router(queues.router)
api_router.include_router(meta.router)
api_router.include_router(admin.router)
api_router.include_router(reports.router)
