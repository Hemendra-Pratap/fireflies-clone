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


settings = Settings()
