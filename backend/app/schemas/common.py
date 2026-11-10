"""Shared response helpers and UTC datetime serialisation."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, PlainSerializer


def _serialise_utc_datetime(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


UtcDateTime = Annotated[
    datetime,
    PlainSerializer(_serialise_utc_datetime, return_type=str, when_used="json"),
]

T = TypeVar("T")


class ErrorBody(BaseModel):
    code: str
    message: str
    details: object | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody


class MessageResponse(BaseModel):
    message: str


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
