from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "backend" / ".data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Hackstrom Vendor Onboarding API"
    app_env: Literal["local", "dev", "staging", "prod"] = "local"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000
    api_prefix: str = "/api/v1"
    frontend_url: str = "http://localhost:5173"

    data_backend: Literal["json", "supabase"] = "supabase"
    data_file: Path = DATA_DIR / "dev_store.json"

    supabase_url: str | None = Field(default=None, alias="SUPABASE_URL")
    supabase_key: str | None = Field(default=None, alias="SUPABASE_KEY")
    supabase_service_role_key: str | None = Field(
        default=None,
        alias="SUPABASE_SERVICE_ROLE_KEY",
    )

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    redis_url: str = Field(default="redis://redis:6379", alias="REDIS_URL")
    celery_broker_url: str = Field(
        default="redis://redis:6379/0",
        alias="CELERY_BROKER_URL",
    )
    celery_result_backend: str = Field(
        default="redis://redis:6379/1",
        alias="CELERY_RESULT_BACKEND",
    )
    celery_task_always_eager: bool = True

    sendgrid_api_key: str | None = Field(default=None, alias="SENDGRID_API_KEY")
    signzy_api_key: str | None = Field(default=None, alias="SIGNZY_API_KEY")
    surepass_api_key: str | None = Field(default=None, alias="SUREPASS_API_KEY")
    decentro_api_key: str | None = Field(default=None, alias="DECENTRO_API_KEY")
    complyadvantage_api_key: str | None = Field(
        default=None,
        alias="COMPLYADVANTAGE_API_KEY",
    )
    oig_api_url: str = Field(
        default="https://oig.hhs.gov/exclusions/api",
        alias="OIG_API_URL",
    )

    jwt_public_key: str | None = None
    jwt_secret: str | None = None
    jwt_algorithm: str = "HS256"
    allow_dev_auth_bypass: bool = True

    prometheus_port: int = Field(default=9090, alias="PROMETHEUS_PORT")
    grafana_port: int = Field(default=3000, alias="GRAFANA_PORT")
    loki_port: int = Field(default=3100, alias="LOKI_PORT")
    jaeger_port: int = 16686

    pii_mask_fields: tuple[str, ...] = (
        "pan",
        "gst",
        "bank_account",
        "ephi_types",
    )

    embedding_dimensions: int = 1536
    oig_auto_reject_enabled: bool = True
    approval_deadline_tier_3_days: int = 7
    approval_deadline_tier_1_2_days: int = 14


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return Settings()
