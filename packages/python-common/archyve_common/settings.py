import json
from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Archyve AI"
    environment: str = Field(
        default="local",
        validation_alias=AliasChoices("APP_ENV", "ENVIRONMENT"),
    )
    database_url: str = Field(
        default="postgresql+psycopg://archyve:archyve@localhost:5432/archyve",
        validation_alias="DATABASE_URL",
    )
    database_url_direct: str | None = Field(
        default=None,
        validation_alias="DATABASE_URL_DIRECT",
    )
    storage_root: str = Field(
        default="./local-data/storage",
        validation_alias="STORAGE_ROOT",
    )
    r2_account_id: str | None = Field(default=None, validation_alias="R2_ACCOUNT_ID")
    r2_bucket: str | None = Field(default=None, validation_alias="R2_BUCKET")
    r2_access_key_id: str | None = Field(
        default=None,
        validation_alias="R2_ACCESS_KEY_ID",
    )
    r2_secret_access_key: str | None = Field(
        default=None,
        validation_alias="R2_SECRET_ACCESS_KEY",
    )
    r2_endpoint: str | None = Field(default=None, validation_alias="R2_ENDPOINT")
    cors_allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000"],
        validation_alias=AliasChoices("CORS_ALLOWED_ORIGINS", "API_CORS_ORIGINS"),
    )
    auth0_domain: str | None = Field(default=None, validation_alias="AUTH0_DOMAIN")
    auth0_audience: str | None = Field(
        default=None,
        validation_alias=AliasChoices("AUTH0_AUDIENCE", "API_AUDIENCE"),
    )
    auth0_issuer: str | None = Field(default=None, validation_alias="AUTH0_ISSUER")
    auth0_jwks_url: str | None = Field(default=None, validation_alias="AUTH0_JWKS_URL")
    default_company_name: str = Field(
        default="Local Workspace",
        validation_alias=AliasChoices(
            "DEFAULT_COMPANY_NAME",
            "DEFAULT_ORGANIZATION_NAME",
        ),
    )
    worker_poll_interval_seconds: int = Field(
        default=3,
        validation_alias="WORKER_POLL_INTERVAL_SECONDS",
    )
    worker_batch_size: int = Field(default=2, validation_alias="WORKER_BATCH_SIZE")
    worker_name: str = Field(default="local-worker", validation_alias="WORKER_NAME")

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, list):
            return value

        if value.startswith("["):
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]

        return [item.strip() for item in value.split(",") if item.strip()]

    @field_validator("database_url", "database_url_direct", mode="before")
    @classmethod
    def normalize_postgres_driver(cls, value: str | None) -> str | None:
        if value is None:
            return value

        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)

        return value

    @property
    def storage_root_path(self) -> Path:
        return Path(self.storage_root).resolve()

    @property
    def migration_database_url(self) -> str:
        return self.database_url_direct or self.database_url

    @property
    def r2_configured(self) -> bool:
        return all(
            [
                self.r2_bucket,
                self.r2_access_key_id,
                self.r2_secret_access_key,
                self.r2_endpoint,
            ]
        )

    @property
    def auth0_domain_host(self) -> str | None:
        if not self.auth0_domain:
            return None

        domain = self.auth0_domain.strip().rstrip("/")
        domain = domain.removeprefix("https://")
        domain = domain.removeprefix("http://")
        return domain or None

    @property
    def resolved_auth0_issuer(self) -> str | None:
        if self.auth0_issuer:
            issuer = self.auth0_issuer.strip()
            return issuer if issuer.endswith("/") else f"{issuer}/"

        if not self.auth0_domain_host:
            return None

        return f"https://{self.auth0_domain_host}/"

    @property
    def resolved_auth0_jwks_url(self) -> str | None:
        if self.auth0_jwks_url:
            return self.auth0_jwks_url.strip()

        if not self.resolved_auth0_issuer:
            return None

        return f"{self.resolved_auth0_issuer}.well-known/jwks.json"

    @property
    def auth0_configured(self) -> bool:
        return all(
            [
                self.auth0_domain_host,
                self.auth0_audience,
                self.resolved_auth0_issuer,
                self.resolved_auth0_jwks_url,
            ]
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

