import secrets
from pathlib import Path
from typing import Annotated, Any, Literal, Optional

from pydantic import AnyUrl, BeforeValidator, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


def parse_cors(v: Any) -> list[str] | str:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",")]
    elif isinstance(v, list | str):
        return v
    raise ValueError(v)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Use top level .env file (one level above ./backend/)
        env_file="../.env",
        env_ignore_empty=True,
        extra="ignore",
    )
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    # 60 minutes * 24 hours * 8 days = 8 days
    FRONTEND_HOST: str = "http://localhost:5173"
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"

    BACKEND_CORS_ORIGINS: Annotated[
        list[AnyUrl] | str, BeforeValidator(parse_cors)
    ] = []

    @computed_field  # type: ignore[prop-decorator]
    @property
    def all_cors_origins(self) -> list[str]:
        origins = [str(origin).rstrip("/") for origin in self.BACKEND_CORS_ORIGINS]
        # Always include the frontend host
        if self.FRONTEND_HOST not in origins:
            origins.append(self.FRONTEND_HOST)
        # For local development with Vite's default port
        if "http://localhost:5173" not in origins:
            origins.append("http://localhost:5173")
        if "http://127.0.0.1:5173" not in origins:
            origins.append("http://127.0.0.1:5173")
        return origins

    PROJECT_NAME: str = "NexusNote"
    MONGO_DATABASE: str = "nexusnote"
    MONGO_DATABASE_URI: str = "mongodb://localhost:27017"

    # Orthanc settings
    ORTHANC_URL: str = "http://localhost:8042"
    ORTHANC_USERNAME: Optional[str] = None
    ORTHANC_PASSWORD: Optional[str] = None

    # Label directory
    LABEL_DIR_PATH: Path = Path(__file__).parent.parent.parent.parent / "data" / "label"


settings = Settings()  # type: ignore
