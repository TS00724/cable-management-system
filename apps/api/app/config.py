from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    app_name: str = "Structured Infrastructure Manager"
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite+pysqlite:///./sim.db"
    platform_database_url: str | None = None
    migration_database_url: str | None = None
    cors_origins: list[str] | str = ["http://localhost:8000"]
    platform_bootstrap_key: str = "replace-this-secret"
    demo_mode: bool = True
    oidc_issuer_url: str = "http://keycloak:8080/realms/sim"
    oidc_audience: str = "sim-api"
    object_storage_backend: str = "local"
    object_storage_path: Path = Path("./storage")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
