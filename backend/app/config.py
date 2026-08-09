from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
RUNBOOKS_DIR = DATA_DIR / "runbooks"
DB_PATH = DATA_DIR / "sentinel.db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Sentinel Ops Copilot"
    secret_key: str = "dev-secret-change-me"
    access_token_expire_minutes: int = 60 * 24
    database_url: str = f"sqlite:///{DB_PATH.as_posix()}"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    demo_mode: bool = True

    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
DATA_DIR.mkdir(parents=True, exist_ok=True)
RUNBOOKS_DIR.mkdir(parents=True, exist_ok=True)
