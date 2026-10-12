from fastapi import APIRouter
from backend.app.core.config import settings
from backend.app.schemas.health import HealthResponse, HealthServicesStatus

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """Return backend health, environment status, and configuration availability.
    
    Notes:
    - Never exposes secret values or API tokens.
    - Accurately reports whether external credentials are provided.
    - Confirms data directory accessibility without triggering heavy disk operations.
    """
    data_dir_exists = settings.data_dir.exists()
    
    services_status = HealthServicesStatus(
        copernicus_catalog_available=True,
        cdse_download_credentials_configured=settings.has_cdse_credentials,
        llm_provider_configured=settings.has_llm_credentials,
        llm_provider_name=settings.active_llm_provider,
        ohsome_osm_api_available=True
    )
    
    return HealthResponse(
        application_name=settings.app_name,
        status="operational",
        backend_version=settings.version,
        environment=settings.environment,
        config_available=True,
        data_directory=str(settings.data_dir),
        data_directory_exists=data_dir_exists,
        services=services_status
    )
