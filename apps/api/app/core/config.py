from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed settings fail fast so insecure deployments do not silently start."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: Literal["development", "staging", "production"] = "development"
    app_name: str = "SalesPilot API"
    api_v1_prefix: str = "/api/v1"

    database_url: str
    redis_url: str

    # ─── JWT ──────────────────────────────────────────────────────────────────
    jwt_secret_key: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 30
    jwt_refresh_token_remember_me_expire_days: int = 90
    jwt_issuer: str = "salespilot-api"

    # ─── Cookies ──────────────────────────────────────────────────────────────
    # The frontend's Next.js middleware gates protected routes by reading a
    # plain-name "access_token" cookie, so the cookie name is a public contract.
    access_token_cookie_name: str = "access_token"
    refresh_token_cookie_name: str = "refresh_token"
    csrf_cookie_name: str = "csrf_token"
    cors_origins: list[AnyHttpUrl] | str = []
    secure_cookies: bool = False

    # ─── Password policy ──────────────────────────────────────────────────────
    password_min_length: int = 8
    password_max_length: int = 128

    # ─── Rate limiting / brute force protection (Redis-backed) ────────────────
    login_rate_limit_attempts: int = 10
    login_rate_limit_window_seconds: int = 900  # 15 minutes, per IP
    account_lockout_threshold: int = 5
    account_lockout_window_seconds: int = 900  # 15 minutes to accumulate failures
    account_lockout_duration_seconds: int = 900  # 15 minutes locked out

    # ─── Tokens (reset / verification) ─────────────────────────────────────────
    password_reset_token_expire_minutes: int = 30
    email_verification_token_expire_hours: int = 24
    invitation_token_expire_days: int = 7

    # ─── Sessions ───────────────────────────────────────────────────────────────
    session_expire_days: int = 1
    session_remember_me_expire_days: int = 30
    max_active_sessions_per_user: int = 10

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_origins(cls, value: object) -> object:
        return value.split(",") if isinstance(value, str) else value


@lru_cache
def get_settings() -> Settings:
    return Settings()
