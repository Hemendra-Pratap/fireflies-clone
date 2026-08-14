from dataclasses import dataclass
import os
from pathlib import Path

# Use an absolute path to the backend directory so behavior is consistent
BACKEND_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_PATH = BACKEND_DIR / "fireflies.db"
DEFAULT_DATABASE_URL = f"sqlite:///{DEFAULT_DATABASE_PATH.as_posix()}"


def _get_normalized_db_url() -> str:
    raw_url = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
    # Fix Heroku/legacy postgres:// scheme for SQLAlchemy 2.0+
    if raw_url.startswith("postgres://"):
        return raw_url.replace("postgres://", "postgresql://", 1)
    return raw_url


def _get_normalized_api_prefix() -> str:
    raw_prefix = os.getenv("API_PREFIX", "/api").strip().rstrip("/")
    if raw_prefix.endswith("/v1"):
        raw_prefix = raw_prefix[:-3].rstrip("/")
    return raw_prefix or "/api"


@dataclass(frozen=True, slots=True)
class Settings:
    environment: str = os.getenv("ENVIRONMENT", "development").lower()
    app_name: str = os.getenv("APP_NAME", "FireFlies Clone API")
    app_version: str = os.getenv("APP_VERSION", "0.1.0")
    api_prefix: str = _get_normalized_api_prefix()
    database_url: str = _get_normalized_db_url()
    backend_dir: Path = BACKEND_DIR
    audio_storage_path: Path = Path(
        os.getenv("AUDIO_STORAGE_PATH", str(BACKEND_DIR / "storage" / "audio"))
    )
    gemini_api_key: str | None = os.getenv("GEMINI_API_KEY")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    transcription_provider: str = os.getenv("TRANSCRIPTION_PROVIDER", "mock")
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "dev_secret_key_change_in_production_123456789")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    jwt_access_token_expire_minutes: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    google_client_id: str | None = os.getenv("GOOGLE_CLIENT_ID")
    google_client_secret: str | None = os.getenv("GOOGLE_CLIENT_SECRET")
    google_redirect_uri: str = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:5173/calendar/callback")

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def cors_origins(self) -> list[str]:
        origins_str = os.getenv(
            "CORS_ORIGINS",
            "https://fireflies-frontend-lzld.onrender.com,http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://localhost:80,http://localhost",
        )
        return [origin.strip() for origin in origins_str.split(",") if origin.strip()]

    def validate_production_config(self) -> None:
        """Validate production configuration security constraints.
        
        Raises RuntimeError if required production secrets or configs are invalid.
        """
        if not self.is_production:
            return

        if self.jwt_secret_key == "dev_secret_key_change_in_production_123456789":
            raise RuntimeError("Production security violation: JWT_SECRET_KEY must be set to a secure secret.")

        if self.database_url.startswith("sqlite"):
            raise RuntimeError("Production configuration error: DATABASE_URL must be configured to PostgreSQL in production mode.")

        if self.transcription_provider == "gemini" and not self.gemini_api_key:
            import logging
            logging.getLogger(__name__).warning("GEMINI_API_KEY is unconfigured; audio transcription and AI analysis require GEMINI_API_KEY.")

        if "*" in self.cors_origins:
            raise RuntimeError("Production security violation: Wildcard '*' in CORS_ORIGINS is not allowed in production mode.")


settings = Settings()
