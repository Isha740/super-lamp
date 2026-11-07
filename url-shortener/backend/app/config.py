from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Defaults match docker-compose's exposed ports, so local dev needs no .env
    database_url: str = "postgresql+psycopg2://shortener:shortener@localhost:5432/shortener"
    redis_url: str = "redis://localhost:6379/0"

    secret_key: str = "change-me-in-production-use-a-long-random-string"
    access_token_minutes: int = 60 * 24

    # Public base of short links, e.g. https://sho.rt  (used to build short_url)
    base_url: str = "http://localhost:8000"
    cors_origins: str = "http://localhost:5173"

    code_length: int = 7
    max_url_length: int = 2048

    cache_ttl_seconds: int = 3600          # redis cache for code -> long url
    enable_background_flush: bool = True   # move redis click counters into Postgres
    flush_interval_seconds: int = 5        # use ~120 on Upstash's free plan (command quota)
    rate_limit_per_minute: int = 30        # shorten requests per user per minute

    @field_validator("database_url")
    @classmethod
    def _use_psycopg2_driver(cls, v: str) -> str:
        """Neon / Render hand out postgres:// or postgresql:// URLs; SQLAlchemy needs a driver."""
        for prefix in ("postgres://", "postgresql://"):
            if v.startswith(prefix):
                return "postgresql+psycopg2://" + v[len(prefix):]
        return v


settings = Settings()
