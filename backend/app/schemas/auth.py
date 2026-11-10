"""Authentication schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.schemas.common import ORMModel
from app.schemas.user import UserRead


class LoginRequest(ORMModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(ORMModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    user: UserRead
