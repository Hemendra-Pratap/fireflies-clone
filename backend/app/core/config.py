from dataclasses import dataclass
import os
from pathlib import Path

# Use an absolute path to the backend SQLite file so behavior is consistent
# regardless of the current working directory when the app or Alembic runs.
BACKEND_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_PATH = BACKEND_DIR / "fireflies.db"
DEFAULT_DATABASE_URL = f"sqlite:///{DEFAULT_DATABASE_PATH.as_posix()}"


@dataclass(frozen=True, slots=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "FireFlies Clone API")
    app_version: str = os.getenv("APP_VERSION", "0.1.0")
    api_prefix: str = os.getenv("API_PREFIX", "/api")
    database_url: str = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
    backend_dir: Path = BACKEND_DIR
    gemini_api_key: str | None = os.getenv("GEMINI_API_KEY")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "dev_secret_key_change_in_production_123456789")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    jwt_access_token_expire_minutes: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

    @property
    def cors_origins(self) -> list[str]:
        origins_str = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://172.22.44.26:5173")
        return [origin.strip() for origin in origins_str.split(",") if origin.strip()]


settings = Settings()
