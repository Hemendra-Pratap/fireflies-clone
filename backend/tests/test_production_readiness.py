from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.services.storage_service import LocalStorageService


def test_liveness_probe(unauth_client: TestClient):
    res = unauth_client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_readiness_probe_connected(unauth_client: TestClient):
    res = unauth_client.get("/api/v1/health/ready")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ready"
    assert data["database"] == "connected"


def test_production_config_validation_default_jwt_secret():
    prod_settings = Settings(
        environment="production",
        database_url="postgresql://user:pass@localhost:5432/db",
        jwt_secret_key="dev_secret_key_change_in_production_123456789",
    )
    with pytest.raises(RuntimeError) as exc_info:
        prod_settings.validate_production_config()
    assert "JWT_SECRET_KEY must be set" in str(exc_info.value)


def test_production_config_validation_sqlite_rejection():
    prod_settings = Settings(
        environment="production",
        database_url="sqlite:///fireflies.db",
        jwt_secret_key="a_very_secure_production_secret_key_123456789",
    )
    with pytest.raises(RuntimeError) as exc_info:
        prod_settings.validate_production_config()
    assert "DATABASE_URL must be configured to PostgreSQL" in str(exc_info.value)


def test_production_config_validation_cors_wildcard_rejection():
    with patch.dict("os.environ", {"CORS_ORIGINS": "http://localhost,*"}):
        prod_settings = Settings(
            environment="production",
            database_url="postgresql://user:pass@localhost:5432/db",
            jwt_secret_key="a_very_secure_production_secret_key_123456789",
        )
        with pytest.raises(RuntimeError) as exc_info:
            prod_settings.validate_production_config()
        assert "Wildcard '*' in CORS_ORIGINS is not allowed" in str(exc_info.value)


def test_storage_service_path_traversal_prevention(tmp_path: Path):
    storage = LocalStorageService(storage_dir=tmp_path)
    with pytest.raises(ValueError) as exc_info:
        storage.get_full_path("../../../etc/passwd")
    assert "Path traversal" in str(exc_info.value)


def test_secret_leakage_prevention(unauth_client: TestClient):
    res = unauth_client.get("/api/v1/health")
    content_str = res.text
    assert "jwt_secret" not in content_str.lower()
    assert "gemini_api_key" not in content_str.lower()
    assert "password_hash" not in content_str.lower()
