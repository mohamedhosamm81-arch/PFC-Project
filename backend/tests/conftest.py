"""Shared test configuration.

Environment variables are set before any application module is imported so the
cached Settings object always points at the test database and a test-only JWT
secret. Integration tests are skipped automatically when greenlet (required by
SQLAlchemy's asyncio bridge) is unavailable.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import pytest_asyncio

os.environ["APP_ENV"] = "test"
os.environ["DEBUG"] = "false"
os.environ["DOCS_ENABLED"] = "false"
os.environ["LOG_LEVEL"] = "WARNING"
os.environ["JWT_SECRET_KEY"] = "pfc-test-secret-key-that-is-long-enough-1234567890"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "60"
os.environ["FACILITY_TIMEZONE"] = "Africa/Cairo"
os.environ["ATTENDANCE_GRACE_MINUTES"] = "15"
os.environ["DOCTOR_DAILY_SLOT_LIMIT"] = "20"
os.environ["SEED_ADMIN_PASSWORD"] = "TestAdmin123!"
os.environ["SEED_DEMO_PASSWORD"] = "TestDemo123!"

# Allow the suite to target a real MySQL instance in CI:
#   PFC_TEST_DATABASE_URL=mysql+asyncmy://... pytest -m integration
os.environ["DATABASE_URL"] = os.environ.get(
    "PFC_TEST_DATABASE_URL",
    "sqlite+aiosqlite:///./.pytest-pfc.db",
)

TEST_DB_FILE = Path(__file__).resolve().parents[1] / ".pytest-pfc.db"


@pytest_asyncio.fixture
async def database():
    """Recreate a clean schema and seed the reference rows every test needs."""
    pytest.importorskip("greenlet")

    import app.models  # noqa: F401  (register metadata)
    from app.core.constants import DEFAULT_ROOMS, TICKET_SEQUENCE_ID
    from app.db.base import Base
    from app.db.session import SessionFactory, engine
    from app.models.room import Room
    from app.models.ticket_sequence import TicketSequence

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)

    async with SessionFactory() as session:
        session.add(TicketSequence(id=TICKET_SEQUENCE_ID, next_ticket_code=1))
        session.add_all(
            [
                Room(
                    code=str(definition["code"]),
                    name=str(definition["name"]),
                    floor_number=int(definition["floor_number"]),
                    station=definition["station"],
                    is_active=True,
                )
                for definition in DEFAULT_ROOMS
            ]
        )
        await session.commit()

    yield

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="session", autouse=True)
def _cleanup_sqlite_file():
    """Remove the throwaway SQLite file after the whole suite finishes."""
    yield
    if os.environ["DATABASE_URL"].startswith("sqlite") and TEST_DB_FILE.exists():
        TEST_DB_FILE.unlink(missing_ok=True)
