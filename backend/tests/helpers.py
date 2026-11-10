"""Factories shared by the integration tests."""

from __future__ import annotations

from datetime import time
from functools import lru_cache
from typing import TYPE_CHECKING

from app.core.security import hash_password
from app.models.enums import Location, UserRole
from app.models.user import User

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

DEFAULT_TEST_PASSWORD = "TestPass123!"


@lru_cache(maxsize=4)
def _hash(password: str) -> str:
    return hash_password(password)


async def create_user(
    session: AsyncSession,
    username: str,
    role: UserRole,
    station: Location | None,
    *,
    password: str = DEFAULT_TEST_PASSWORD,
    full_name: str | None = None,
    shift_start: time = time(8, 0),
) -> User:
    user = User(
        username=username,
        password_hash=_hash(password),
        full_name=full_name or f"Test {username}",
        role=role,
        assigned_station=station,
        default_shift_start=shift_start,
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


def detached_user(role: UserRole, station: Location | None) -> User:
    """A transient User for code paths that never persist the actor."""
    return User(
        id=9999,
        username=f"detached.{role.value}",
        password_hash="not-a-real-hash",
        full_name="Detached Actor",
        role=role,
        assigned_station=station,
        is_active=True,
    )
