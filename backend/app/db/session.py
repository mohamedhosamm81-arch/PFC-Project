"""Async database engine and request-scoped session dependency."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings

_engine_options: dict[str, Any] = {
    "echo": settings.database_echo,
    "pool_pre_ping": True,
}
# SQLite (used by the test suite) is served by StaticPool/NullPool, which do
# not accept queue-pool sizing arguments.
if settings.database_url.startswith("sqlite"):
    # NullPool keeps test connections from being reused across pytest event
    # loops and avoids file-lock contention on the throwaway test database.
    _engine_options["poolclass"] = NullPool
else:
    _engine_options.update(
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_recycle=settings.db_pool_recycle_seconds,
    )

engine = create_async_engine(settings.database_url, **_engine_options)

SessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autoflush=False,
    expire_on_commit=False,
)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Yield one session per request and always roll back failed work."""
    async with SessionFactory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def check_database() -> None:
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))


async def dispose_engine() -> None:
    await engine.dispose()
