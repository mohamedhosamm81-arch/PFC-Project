"""User request/response schemas."""

from __future__ import annotations

import re
from datetime import time
from typing import Annotated

from pydantic import Field, field_serializer, field_validator

from app.models.enums import Location, UserRole
from app.schemas.common import ORMModel, UtcDateTime

USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,63}$")


def validate_password_strength(value: str) -> str:
    if len(value) < 8:
        raise ValueError("Password must contain at least 8 characters.")
    if len(value) > 128:
        raise ValueError("Password must contain at most 128 characters.")
    if not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
        raise ValueError("Password must contain at least one letter and one digit.")
    return value


class UserRead(ORMModel):
    id: int
    username: str
    full_name: str
    role: UserRole
    assigned_station: Location | None
    default_shift_start: time
    is_active: bool
    created_at: UtcDateTime

    @field_serializer("default_shift_start")
    def serialise_shift(self, value: time) -> str:
        return value.strftime("%H:%M")


class UserBrief(ORMModel):
    id: int
    username: str
    full_name: str
    role: UserRole


class UserCreate(ORMModel):
    username: Annotated[str, Field(min_length=3, max_length=64)]
    password: Annotated[str, Field(min_length=8, max_length=128)]
    full_name: Annotated[str, Field(min_length=2, max_length=160)]
    role: UserRole
    assigned_station: Location | None = None
    default_shift_start: time = time(8, 0)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        value = value.strip()
        if not USERNAME_PATTERN.fullmatch(value):
            raise ValueError(
                "Username must be 3-64 characters and use only letters, digits, '.', '_' or '-'."
            )
        return value

    @field_validator("full_name")
    @classmethod
    def clean_full_name(cls, value: str) -> str:
        value = " ".join(value.split())
        if len(value) < 2:
            raise ValueError("Full name is too short.")
        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return validate_password_strength(value)


class UserUpdate(ORMModel):
    full_name: Annotated[str, Field(min_length=2, max_length=160)] | None = None
    role: UserRole | None = None
    assigned_station: Location | None = None
    default_shift_start: time | None = None
    is_active: bool | None = None
    password: Annotated[str, Field(min_length=8, max_length=128)] | None = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str | None) -> str | None:
        return validate_password_strength(value) if value is not None else None
