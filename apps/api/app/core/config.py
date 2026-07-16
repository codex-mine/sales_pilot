from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
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
    # Plain strings, not AnyHttpUrl: CORSMiddleware matches a request's
    # `Origin` header (which never has a trailing slash or path) against
    # this list with an exact string comparison. AnyHttpUrl normalizes
    # "http://localhost:3000" to "http://localhost:3000/" when stringified,
    # which then silently fails to match every real browser Origin header.
    cors_origins: list[str] | str = []
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

    # ─── Frontend / email ──────────────────────────────────────────────────────
    # Used to build links in transactional emails (verify-email, reset-password).
    frontend_url: str = "http://localhost:3000"

    # SMTP is optional: when smtp_host is unset, EmailService logs and no-ops
    # instead of sending, so registration/reset flows keep working in local
    # dev without real mail credentials configured.
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = True
    smtp_from_email: str = "no-reply@salespilot.app"
    smtp_from_name: str = "SalesPilot"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_origins(cls, value):
        if isinstance(value, str):
            value = [origin.strip() for origin in value.split(",")]
        return [origin.rstrip("/") for origin in value]



@lru_cache
def get_settings() -> Settings:
    return Settings()
