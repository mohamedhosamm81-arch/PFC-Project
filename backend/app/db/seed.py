"""Idempotent database seed: admin, circular sequence, rooms and demo staff."""

from __future__ import annotations

import argparse
import asyncio
import logging
from datetime import time

from sqlalchemy import func, select

from app.core.config import settings
from app.core.constants import DEFAULT_ROOMS, TICKET_SEQUENCE_ID
from app.core.security import hash_password
from app.db.session import SessionFactory, dispose_engine
from app.models.enums import Location, UserRole
from app.models.room import Room
from app.models.ticket_sequence import TicketSequence
from app.models.user import User

logger = logging.getLogger("pfc.seed")


async def ensure_sequence() -> None:
    async with SessionFactory() as session:
        sequence = await session.get(TicketSequence, TICKET_SEQUENCE_ID)
        if sequence is None:
            session.add(TicketSequence(id=TICKET_SEQUENCE_ID, next_ticket_code=1))
            await session.commit()
            logger.info("Created ticket sequence row")


async def ensure_rooms() -> None:
    async with SessionFactory() as session:
        created = 0
        for definition in DEFAULT_ROOMS:
            code = str(definition["code"])
            exists = await session.scalar(select(Room.id).where(Room.code == code))
            if exists is not None:
                continue
            session.add(
                Room(
                    code=code,
                    name=str(definition["name"]),
                    floor_number=int(definition["floor_number"]),
                    station=definition["station"],
                    is_active=True,
                )
            )
            created += 1
        if created:
            await session.commit()
            logger.info("Created %s default room(s)", created)


async def ensure_user(
    *,
    username: str,
    password: str,
    full_name: str,
    role: UserRole,
    station: Location | None,
    shift: time = time(8, 0),
) -> bool:
    async with SessionFactory() as session:
        exists = await session.scalar(
            select(User.id).where(func.lower(User.username) == username.lower())
        )
        if exists is not None:
            return False
        session.add(
            User(
                username=username,
                password_hash=hash_password(password),
                full_name=full_name,
                role=role,
                assigned_station=station,
                default_shift_start=shift,
                is_active=True,
            )
        )
        await session.commit()
        logger.info("Created %s account '%s'", role.value, username)
        return True


async def run_seed(include_demo: bool = False) -> None:
    logger.info("Seeding PFC database...")
    await ensure_sequence()
    await ensure_rooms()

    created = await ensure_user(
        username=settings.seed_admin_username,
        password=settings.seed_admin_password,
        full_name=settings.seed_admin_full_name,
        role=UserRole.ADMIN,
        station=None,
    )
    insecure_seed_password = settings.seed_admin_password == "ChangeMe123!" or any(
        marker in settings.seed_admin_password.lower()
        for marker in ("change_me", "change-me", "changeme", "example")
    )
    if created and settings.app_env == "production" and insecure_seed_password:
        logger.warning(
            "The seeded admin is using an example password. Change it immediately "
            "via PATCH /api/admin/users/{id} or SEED_ADMIN_PASSWORD."
        )

    if include_demo:
        await ensure_user(
            username="reception",
            password=settings.seed_demo_password,
            full_name="Reception Desk",
            role=UserRole.RECEPTION,
            station=Location.RECEPTION,
        )
        await ensure_user(
            username="doctor.layla",
            password=settings.seed_demo_password,
            full_name="Dr. Layla Hassan",
            role=UserRole.DOCTOR,
            station=Location.CMO,
        )
        await ensure_user(
            username="doctor.omar",
            password=settings.seed_demo_password,
            full_name="Dr. Omar Nasser",
            role=UserRole.DOCTOR,
            station=Location.CMO,
        )
        await ensure_user(
            username="pharmacy.staff",
            password=settings.seed_demo_password,
            full_name="Sara Youssef",
            role=UserRole.BRANCH_STAFF,
            station=Location.PHARMACY,
        )
        await ensure_user(
            username="cashier.staff",
            password=settings.seed_demo_password,
            full_name="Cashier Window",
            role=UserRole.BRANCH_STAFF,
            station=Location.CASHIER,
        )

    logger.info("Seed complete.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the PFC MySQL database")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Also create demo reception, doctor, pharmacy and cashier accounts.",
    )
    args = parser.parse_args()
    logging.basicConfig(level=settings.log_level.upper())

    async def _run() -> None:
        try:
            await run_seed(include_demo=args.demo)
        finally:
            await dispose_engine()

    asyncio.run(_run())


if __name__ == "__main__":
    main()
