"""Password hashing and JWT access-token helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import settings
from app.core.exceptions import AuthenticationError

# OWASP-recommended Argon2id defaults. Each hash embeds its own parameters,
# so these can be raised later without invalidating existing passwords.
_password_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)

# Used to keep invalid-username logins roughly as expensive as valid ones.
_DUMMY_HASH = _password_hasher.hash("pfc-dummy-password-not-used")


def hash_password(password: str) -> str:
    if not password or len(password) > 128:
        raise ValueError("Password must contain between 1 and 128 characters.")
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def verify_against_dummy(password: str) -> None:
    """Burn comparable CPU time when the username does not exist."""
    try:
        _password_hasher.verify(_DUMMY_HASH, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        pass


def password_needs_rehash(password_hash: str) -> bool:
    try:
        return _password_hasher.check_needs_rehash(password_hash)
    except InvalidHashError:
        return True


def create_access_token(
    *,
    user_id: int,
    username: str,
    role: str,
    station: str | None,
) -> tuple[str, datetime]:
    issued_at = datetime.now(timezone.utc)
    expires_at = issued_at + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "station": station,
        "type": "access",
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": issued_at,
        "nbf": issued_at,
        "exp": expires_at,
        "jti": str(uuid4()),
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, expires_at


def decode_access_token(token: str) -> dict:
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options={"require": ["sub", "exp", "iat", "iss", "aud"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationError("The access token has expired.", "TOKEN_EXPIRED") from exc
    except jwt.PyJWTError as exc:
        raise AuthenticationError("The access token is invalid.", "INVALID_TOKEN") from exc

    if claims.get("type") != "access":
        raise AuthenticationError("The access token is invalid.", "INVALID_TOKEN")
    return claims
