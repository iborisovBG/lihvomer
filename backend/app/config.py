from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    database_url: str = "postgresql+psycopg://ecb_loans:ecb_loans_dev@127.0.0.1:5432/ecb_loans"
    redis_url: str = "redis://127.0.0.1:6379/0"

    jwt_secret: str = Field(min_length=16)
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 60 * 24 * 7

    http_timeout_seconds: float = 60.0
    http_user_agent: str = "ecb-loans-monitor/1.0 (+public-data-research)"

    cors_origins: str = "http://localhost:3000"

    # Доставка на известия. Празен smtp_host изключва изпращането — известията
    # пак се записват и се виждат в приложението.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_use_tls: bool = True
    smtp_use_ssl: bool = False

    # Официалният неотменим фиксинг на БНБ при въвеждането на еврото.
    bgn_per_eur: float = 1.95583

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
