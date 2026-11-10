"""Application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_SECRET_MARKERS = (
    "change-me",
    "change_me",
    "changeme",
    "replace-me",
    "replace_me",
    "your-secret",
    "example",
)


class Settings(BaseSettings):
    """Typed settings for the on-premises PFC deployment."""

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "PFC Backend"
    app_version: str = "1.0.0"
    app_env: Literal["development", "staging", "production", "test"] = "production"
    debug: bool = False
    docs_enabled: bool = False
    api_prefix: str = "/api"
    log_level: str = "INFO"

    # Security
    jwt_secret_key: str = "change-me-in-env-with-at-least-32-characters"
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    jwt_issuer: str = "pfc-backend"
    jwt_audience: str = "pfc-clients"
    access_token_expire_minutes: int = Field(default=480, ge=5, le=10080)

    # Database
    database_url: str = "mysql+asyncmy://pfc_user:pfc_password@mysql_db:3306/pfc"
    database_echo: bool = False
    db_pool_size: int = Field(default=10, ge=1, le=100)
    db_max_overflow: int = Field(default=20, ge=0, le=200)
    db_pool_recycle_seconds: int = Field(default=3600, ge=60)

    # HTTP / realtime
    cors_origins: str = (
        "http://localhost:8000,http://127.0.0.1:8000,"
        "http://localhost:5500,http://127.0.0.1:5500"
    )
    ws_origins: str = ""
    ws_receive_timeout_seconds: int = Field(default=90, ge=30, le=600)
    max_ws_subscriptions: int = Field(default=20, ge=1, le=100)

    # Business rules
    facility_timezone: str = "Africa/Cairo"
    attendance_grace_minutes: int = Field(default=15, ge=0, le=120)
    doctor_daily_slot_limit: int = Field(default=20, ge=1, le=1000)

    # Seeding
    seed_admin_username: str = "admin"
    seed_admin_password: str = "ChangeMe123!"
    seed_admin_full_name: str = "System Administrator"
    seed_demo_password: str = "Demo12345!"

    @field_validator("database_url")
    @classmethod
    def normalise_database_url(cls, value: str) -> str:
        value = value.strip()
        # The async stack uses asyncmy. Accept the common PyMySQL URL so an
        # operator can copy a conventional MySQL DSN into .env by mistake.
        if value.startswith("mysql+pymysql://"):
            value = value.replace("mysql+pymysql://", "mysql+asyncmy://", 1)
        if value.startswith("mysql://"):
            value = value.replace("mysql://", "mysql+asyncmy://", 1)
        return value

    @field_validator("api_prefix")
    @classmethod
    def validate_prefix(cls, value: str) -> str:
        value = value.strip()
        if not value.startswith("/"):
            raise ValueError("API_PREFIX must start with '/'")
        return value.rstrip("/") or ""

    @property
    def cors_origins_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def ws_origins_list(self) -> list[str]:
        raw = self.ws_origins or self.cors_origins
        return [item.strip() for item in raw.split(",") if item.strip()]

    @model_validator(mode="after")
    def validate_runtime_configuration(self) -> "Settings":
        if len(self.jwt_secret_key) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters long.")
        if self.app_env in {"production", "staging"}:
            lowered = self.jwt_secret_key.lower()
            if any(marker in lowered for marker in _INSECURE_SECRET_MARKERS):
                raise ValueError(
                    "JWT_SECRET_KEY is using an insecure placeholder. "
                    "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(48))\""
                )
        try:
            ZoneInfo(self.facility_timezone)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(
                f"Unknown FACILITY_TIMEZONE '{self.facility_timezone}'. "
                "Install tzdata or use an IANA timezone such as Africa/Cairo."
            ) from exc
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
