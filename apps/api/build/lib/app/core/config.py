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
    jwt_secret_key: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 30
    cors_origins: list[AnyHttpUrl] | str = []
    secure_cookies: bool = False
    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_origins(cls, value: object) -> object:
        return value.split(",") if isinstance(value, str) else value

@lru_cache
def get_settings() -> Settings: return Settings()
