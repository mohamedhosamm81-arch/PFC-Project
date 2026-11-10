"""Wait until MySQL accepts connections before running migrations."""

from __future__ import annotations

import asyncio
import logging
import sys

from sqlalchemy import text

from app.core.config import settings
from app.db.session import dispose_engine, engine

logger = logging.getLogger("pfc.wait")


async def wait_for_database(attempts: int = 40, delay_seconds: float = 2.0) -> None:
    for attempt in range(1, attempts + 1):
        try:
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
                logger.info("MySQL is ready (attempt %s/%s)", attempt, attempts)
                return
        except Exception as exc:
            logger.info(
                "Waiting for MySQL %s/%s (%s)",
                attempt,
                attempts,
                exc.__class__.__name__,
            )
            await asyncio.sleep(delay_seconds)
    raise RuntimeError("MySQL did not become ready in time.")


def main() -> None:
    logging.basicConfig(level=settings.log_level.upper())

    async def _run() -> None:
        try:
            await wait_for_database()
        finally:
            await dispose_engine()

    try:
        asyncio.run(_run())
    except Exception:
        logger.exception("Database readiness check failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
