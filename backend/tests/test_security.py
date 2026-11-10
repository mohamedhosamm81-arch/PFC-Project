"""Password hashing and JWT guarantees."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.core.config import settings
from app.core.exceptions import AuthenticationError
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    password_needs_rehash,
    verify_password,
)


def test_argon2id_round_trip_and_rejection():
    digest = hash_password("CorrectHorse123!")
    assert digest.startswith("$argon2id$")
    assert verify_password("CorrectHorse123!", digest) is True
    assert verify_password("wrong-password", digest) is False
    assert password_needs_rehash(digest) is False


def test_hashes_are_salted():
    assert hash_password("SamePassword1") != hash_password("SamePassword1")


def test_access_token_contains_expected_claims():
    token, expires_at = create_access_token(
        user_id=42, username="doctor.omar", role="doctor", station="CMO"
    )
    claims = decode_access_token(token)
    assert claims["sub"] == "42"
    assert claims["username"] == "doctor.omar"
    assert claims["role"] == "doctor"
    assert claims["station"] == "CMO"
    assert claims["iss"] == settings.jwt_issuer
    assert claims["aud"] == settings.jwt_audience
    assert claims["type"] == "access"
    assert expires_at > datetime.now(timezone.utc)


def test_token_signed_with_another_secret_is_rejected(monkeypatch):
    token, _ = create_access_token(
        user_id=1, username="admin", role="admin", station=None
    )
    monkeypatch.setattr(settings, "jwt_secret_key", "a-different-secret-" * 3)
    with pytest.raises(AuthenticationError) as exc:
        decode_access_token(token)
    assert exc.value.code == "INVALID_TOKEN"


def test_expired_token_is_rejected():
    now = datetime.now(timezone.utc)
    payload = {
        "sub": "1",
        "username": "admin",
        "role": "admin",
        "station": None,
        "type": "access",
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": now - timedelta(hours=2),
        "nbf": now - timedelta(hours=2),
        "exp": now - timedelta(hours=1),
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    with pytest.raises(AuthenticationError) as exc:
        decode_access_token(token)
    assert exc.value.code == "TOKEN_EXPIRED"


def test_non_access_token_type_is_rejected():
    now = datetime.now(timezone.utc)
    payload = {
        "sub": "1",
        "username": "admin",
        "role": "admin",
        "station": None,
        "type": "refresh",
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(minutes=5),
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    with pytest.raises(AuthenticationError):
        decode_access_token(token)
