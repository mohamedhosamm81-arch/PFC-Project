"""Authentication and role dependencies for HTTP routes."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.core.security import decode_access_token
from app.db.session import get_db_session
from app.models.enums import UserRole
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False, description="PFC bearer access token")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise AuthenticationError()
    claims = decode_access_token(credentials.credentials)
    try:
        user_id = int(claims["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise AuthenticationError("The access token is invalid.", "INVALID_TOKEN") from exc

    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise AuthenticationError("The account is no longer active.", "INVALID_TOKEN")
    return user


def require_roles(*roles: UserRole) -> Callable[..., Coroutine[Any, Any, User]]:
    allowed = frozenset(roles)

    async def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise PermissionDeniedError(
                "This action requires one of the following roles: "
                + ", ".join(sorted(role.value for role in allowed))
            )
        return user

    return dependency
