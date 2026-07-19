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

    # ─── AI providers (platform-level fallback keys) ───────────────────────────
    # Per-organization keys live encrypted on Integration rows and take
    # precedence; these env keys are the fallback so a fresh deploy can run AI
    # jobs before any org has connected its own key. Ollama has no API key —
    # it's a local/self-hosted server addressed by base URL.
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    groq_api_key: str | None = None
    gemini_api_key: str | None = None
    ollama_base_url: str | None = None

    ai_default_provider: str = "groq"
    ai_default_model: str = "llama-3.1-8b-instant"
    ai_default_temperature: float = 0.7
    ai_default_max_tokens: int = 2048
    ai_max_retries: int = 3
    ai_job_timeout_seconds: int = 120
    # Development/testing escape hatch: execute AI jobs inline in the request
    # process instead of dispatching to Celery, so `docker compose up` without
    # a worker container still produces results. Never enable in production —
    # it blocks API workers on LLM latency.
    ai_execute_jobs_eagerly: bool = False

    # Fernet key for encrypting third-party credentials (AI provider API keys)
    # at rest on Integration rows. Generate with:
    #   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    # Falls back to a key derived from jwt_secret_key when unset (fine for
    # development; set explicitly in production so JWT secret rotation doesn't
    # orphan stored credentials).
    credentials_encryption_key: str | None = None

    # ─── Outreach sending (Communication -> Email Sending) ─────────────────────
    # Deliberately separate from smtp_* above (transactional auth email) —
    # mixing transactional and cold-outreach traffic on one sending domain
    # damages deliverability for both. Org-level Integration rows (integration_type
    # "smtp") take precedence when connected; these are the platform fallback.
    outreach_smtp_host: str | None = None
    outreach_smtp_port: int = 587
    outreach_smtp_username: str | None = None
    outreach_smtp_password: str | None = None
    outreach_smtp_use_tls: bool = True
    outreach_daily_send_limit_default: int = 100
    outreach_send_max_retries: int = 3
    # Default sending window for ad hoc (non-campaign) sends, in the
    # organization's own timezone — protects deliverability reputation even
    # for one-off sends the same way a campaign's send_days/hours would.
    outreach_default_send_start_hour: int = 9
    outreach_default_send_end_hour: int = 17

    # ─── Company Research (AI -> Research & Prospect Analysis) ─────────────────
    # How long a CompanyResearch row is considered fresh before a trigger without
    # force=True is a no-op that just returns the existing AIJob.
    research_staleness_days: int = 30
    research_website_fetch_timeout_seconds: int = 8
    research_website_max_bytes: int = 500_000

    # ─── File uploads (organization logo) ──────────────────────────────────────
    # Local disk storage — no cloud storage credentials exist in this project
    # yet. `upload_dir` is relative to the app's working directory and must be
    # a Docker volume (not container-ephemeral storage) to survive rebuilds.
    upload_dir: str = "uploads"
    max_logo_size_mb: int = 5
    max_attachment_size_mb: int = 25
    # Used to build the absolute `logo_url` returned to clients — the browser
    # requests media directly from the API origin, same as NEXT_PUBLIC_API_URL
    # on the frontend points there for JSON endpoints.
    api_base_url: str = "http://localhost:8000"

    # ─── Email Tracking (Communication -> Open/Click Tracking & Delivery Events) ─
    # Shared secret for verifying the "generic" HMAC-SHA256 webhook signature
    # scheme (X-Webhook-Signature header over the raw body). Falls back to a
    # key derived from jwt_secret_key when unset, same dev-convenience pattern
    # as CREDENTIALS_ENCRYPTION_KEY in app/security/crypto.py — a real
    # deployment wiring an actual ESP's webhook should set this explicitly.
    email_webhook_signing_secret: str | None = None
    # A pixel fetch this soon after send is treated as a possible bot/prefetch
    # (Apple Mail Privacy Protection, corporate scanners) rather than a human
    # open — see email_tracking_service.py.
    email_open_bot_window_seconds: int = 5
    # Repeated pixel fires for the same email within this window are treated
    # as one open (mail clients re-fetch on scroll/re-render).
    email_open_dedupe_window_seconds: int = 300

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_origins(cls, value):
        if isinstance(value, str):
            value = [origin.strip() for origin in value.split(",")]
        return [origin.rstrip("/") for origin in value]



@lru_cache
def get_settings() -> Settings:
    return Settings()
