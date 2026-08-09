from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
RUNBOOKS_DIR = DATA_DIR / "runbooks"
DB_PATH = DATA_DIR / "sentinel.db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Sentinel Ops Copilot"
    secret_key: str = "dev-secret-change-me"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    database_url: str = f"sqlite:///{DB_PATH.as_posix()}"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000,http://127.0.0.1:8000"
    demo_mode: bool = True
    webhook_token: str = "sentinel-webhook-dev-token"
    public_base_url: str = "http://127.0.0.1:8000"

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        if not isinstance(value, str):
            return value
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+psycopg2://", 1)
        if value.startswith("postgresql://") and "+psycopg2" not in value:
            return value.replace("postgresql://", "postgresql+psycopg2://", 1)
        return value

    @property
    def origins(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
DATA_DIR.mkdir(parents=True, exist_ok=True)
RUNBOOKS_DIR.mkdir(parents=True, exist_ok=True)
