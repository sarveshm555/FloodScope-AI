from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


class HealthServicesStatus(BaseModel):
    """Detailed external service configuration flags."""
    copernicus_catalog_available: bool = Field(
        default=True,
        description="Public Copernicus Data Space catalog API is accessible without authentication."
    )
    cdse_download_credentials_configured: bool = Field(
        ...,
        description="Whether optional CDSE download credentials (username/password or OAuth client) are set in environment."
    )
    llm_provider_configured: bool = Field(
        ...,
        description="Whether an external LLM API key (Gemini/OpenAI) is set for the Situation-Report Copilot."
    )
    llm_provider_name: Optional[str] = Field(
        default=None,
        description="Name of configured LLM provider or null if using deterministic report generator."
    )
    ohsome_osm_api_available: bool = Field(
        default=True,
        description="Heidelberg ohsome OpenStreetMap historical API is accessible."
    )


class HealthResponse(BaseModel):
    """Structured response schema for GET /api/health."""
    application_name: str = Field(..., examples=["FloodScope AI"])
    status: str = Field(..., examples=["operational"])
    backend_version: str = Field(..., examples=["0.1.0"])
    environment: str = Field(..., examples=["development"])
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="UTC ISO8601 timestamp of health evaluation."
    )
    config_available: bool = Field(
        ...,
        description="Indicates whether mandatory local configuration is loaded successfully."
    )
    data_directory: str = Field(
        ...,
        description="Current resolved path for local data and cache storage."
    )
    data_directory_exists: bool = Field(
        ...,
        description="Whether the designated data directory currently exists on the filesystem."
    )
    services: HealthServicesStatus = Field(
        ...,
        description="Status of service configurations and public catalog endpoints."
    )
