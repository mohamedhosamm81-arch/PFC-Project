"""Authentication service."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import func, select

from app.core.config import settings
from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.core.security import (
    create_access_token,
    hash_password,
    password_needs_rehash,
    verify_against_dummy,
    verify_password,
)
from app.models.user import User

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def authenticate(self, username: str, password: str) -> User:
        normalised = username.strip().lower()
        user = await self.session.scalar(
            select(User).where(func.lower(User.username) == normalised)
        )

        if user is None:
            verify_against_dummy(password)
            raise AuthenticationError("Invalid username or password.", "INVALID_CREDENTIALS")

        if not verify_password(password, user.password_hash):
            raise AuthenticationError("Invalid username or password.", "INVALID_CREDENTIALS")

        if not user.is_active:
            raise PermissionDeniedError("This account is disabled.")

        if password_needs_rehash(user.password_hash):
            user.password_hash = hash_password(password)
            await self.session.commit()

        return user

    async def login(self, username: str, password: str) -> tuple[User, str, int]:
        user = await self.authenticate(username, password)
        token, expires_at = create_access_token(
            user_id=user.id,
            username=user.username,
            role=user.role.value,
            station=user.assigned_station.value if user.assigned_station else None,
        )
        expires_in = max(
            0,
            int((expires_at - datetime.now(timezone.utc)).total_seconds()),
        )
        return user, token, expires_in

    async def get_active_user(self, user_id: int) -> User:
        user = await self.session.get(User, user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("The account is no longer active.", "INVALID_TOKEN")
        return user

    @property
    def token_ttl_seconds(self) -> int:
        return settings.access_token_expire_minutes * 60
