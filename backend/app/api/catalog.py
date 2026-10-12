from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from backend.app.schemas.catalog import (
    CatalogSearchRequest,
    CatalogSearchResponse
)
from backend.app.geospatial.catalog import (
    execute_catalog_discovery,
    get_search_results
)

router = APIRouter()


@router.post("/search", response_model=CatalogSearchResponse)
def search_satellite_catalog(request: CatalogSearchRequest) -> CatalogSearchResponse:
    """Discover real Sentinel-1 and Sentinel-2 acquisitions from Copernicus Data Space.
    
    Notes:
    - Queries public catalog without requiring download credentials.
    - Checks footprint intersection against requested AOI polygon.
    - Calculates recommended 12-day repeat pass Sentinel-1 pairs.
    - Preserves complete query provenance.
    - Does NOT download raw image data.
    """
    try:
        response = execute_catalog_discovery(request)
        return response
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Satellite catalog discovery failed: {str(e)}"
        )


@router.get("/results/{search_id}", response_model=CatalogSearchResponse)
def get_cached_search_results(search_id: str) -> CatalogSearchResponse:
    """Retrieve previously executed catalog discovery results by search_id."""
    results = get_search_results(search_id)
    if not results:
        raise HTTPException(
            status_code=404,
            detail=f"No discovery results found for search_id: '{search_id}'."
        )
    return results


@router.get("/pilot", response_model=CatalogSearchResponse)
def get_pilot_catalog_discovery(
    pre_days: int = Query(15, ge=1, le=60),
    post_days: int = Query(15, ge=1, le=60)
) -> CatalogSearchResponse:
    """Preset discovery endpoint for the August 26, 2026 Trishuli Flood case study in Nepal."""
    request = CatalogSearchRequest(
        bbox=[85.10, 27.85, 85.25, 28.05],
        event_date="2026-08-26",
        pre_days=pre_days,
        post_days=post_days,
        include_sentinel_1=True,
        include_sentinel_2=True
    )
    return execute_catalog_discovery(request)
