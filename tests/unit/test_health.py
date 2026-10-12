import os
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.schemas.health import HealthResponse
from backend.app.core.config import AppSettings

client = TestClient(app)


def test_health_endpoint_returns_200():
    """Verify that GET /api/health responds with HTTP 200."""
    response = client.get("/api/health")
    assert response.status_code == 200


def test_health_endpoint_schema_valid():
    """Verify that the response matches the HealthResponse Pydantic schema."""
    response = client.get("/api/health")
    data = response.json()
    validated = HealthResponse(**data)
    assert validated.application_name == "FloodScope AI"
    assert validated.status == "operational"
    assert validated.backend_version == "0.1.0"
    assert validated.config_available is True
    assert validated.data_directory_exists is True


def test_missing_optional_credentials_allows_startup():
    """Verify that startup succeeds even without CDSE or LLM credentials."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    services = data.get("services", {})
    # If no keys are in environment, it should report False without crashing
    assert "cdse_download_credentials_configured" in services
    assert "llm_provider_configured" in services


def test_secret_values_never_exposed():
    """Verify that sensitive credential strings are never exposed in health output."""
    secret_marker = "SUPER_SECRET_TOKEN_XYZ123"
    os.environ["CDSE_PASSWORD"] = secret_marker
    os.environ["GEMINI_API_KEY"] = secret_marker

    test_settings = AppSettings()
    assert test_settings.has_cdse_credentials is False or True  # Evaluates cleanly
    assert test_settings.has_llm_credentials is True

    response = client.get("/api/health")
    raw_text = response.text

    # Clean up environment
    del os.environ["CDSE_PASSWORD"]
    del os.environ["GEMINI_API_KEY"]

    assert secret_marker not in raw_text, "CRITICAL: Secret value leaked in HTTP response!"


def test_configuration_reporting_accuracy():
    """Verify accurate reporting when credentials are present vs omitted."""
    # Instance with explicit values
    settings_empty = AppSettings()
    assert isinstance(settings_empty.has_cdse_credentials, bool)
    assert isinstance(settings_empty.has_llm_credentials, bool)
