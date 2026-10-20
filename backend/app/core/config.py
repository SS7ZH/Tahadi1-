from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_SECRETS = {"change-me-access-secret", "change-me-refresh-secret", "dev-access-secret", "dev-refresh-secret"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ENVIRONMENT: str = "development"

    DATABASE_URL: str = "postgresql://tahadi:tahadi@localhost:5432/tahadi"
    MIGRATIONS_DATABASE_URL: str | None = None
    DB_NULLPOOL: bool | None = None

    JWT_SECRET: str = "dev-access-secret"
    JWT_REFRESH_SECRET: str = "dev-refresh-secret"
    ACCESS_TOKEN_MINUTES: int = 30
    REFRESH_TOKEN_DAYS: int = 14

    LOGIN_RATE_LIMIT: int = 10
    LOGIN_RATE_WINDOW_SECONDS: int = 60

    CORS_ORIGINS: str = "http://localhost:5173"
    CORS_ORIGIN_REGEX: str | None = None

    SEED_ADMIN_EMAIL: str = "admin@tahadi.app"
    SEED_ADMIN_PASSWORD: str | None = None
    SEED_DEMO_PASSWORD: str | None = None

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip().rstrip("/") for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def migrations_url(self) -> str:
        return self.MIGRATIONS_DATABASE_URL or self.DATABASE_URL

    @model_validator(mode="after")
    def _check_production_secrets(self) -> "Settings":
        if self.is_production:
            if self.JWT_SECRET in _DEFAULT_SECRETS or self.JWT_REFRESH_SECRET in _DEFAULT_SECRETS:
                raise ValueError("JWT_SECRET and JWT_REFRESH_SECRET must be set in production")
            if self.JWT_SECRET == self.JWT_REFRESH_SECRET:
                raise ValueError("JWT_SECRET and JWT_REFRESH_SECRET must differ")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
