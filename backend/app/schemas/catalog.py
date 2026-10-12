from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class CatalogSearchRequest(BaseModel):
    """User-configurable query parameters for satellite data discovery."""
    bbox: List[float] = Field(
        default=[85.10, 27.85, 85.25, 28.05],
        description="Bounding box [west, south, east, north] in EPSG:4326.",
        examples=[[85.10, 27.85, 85.25, 28.05]]
    )
    event_date: str = Field(
        default="2026-08-26",
        description="ISO date string for the flood disaster event (YYYY-MM-DD).",
        examples=["2026-08-26"]
    )
    pre_days: int = Field(
        default=15,
        ge=1,
        le=60,
        description="Search window in days prior to the event date."
    )
    post_days: int = Field(
        default=15,
        ge=1,
        le=60,
        description="Search window in days following the event date."
    )
    include_sentinel_1: bool = Field(
        default=True,
        description="Whether to discover Sentinel-1 SAR GRD acquisitions."
    )
    include_sentinel_2: bool = Field(
        default=True,
        description="Whether to discover Sentinel-2 optical MSI acquisitions."
    )
    orbit_direction: Optional[str] = Field(
        default=None,
        description="Optional filter for Sentinel-1 orbit direction ('ASCENDING' or 'DESCENDING')."
    )

    @field_validator("bbox")
    @classmethod
    def validate_bbox(cls, v: List[float]) -> List[float]:
        if len(v) != 4:
            raise ValueError("Bounding box must contain exactly 4 coordinates: [west, south, east, north]")
        west, south, east, north = v
        if not (-180.0 <= west <= 180.0 and -180.0 <= east <= 180.0):
            raise ValueError("Longitudes must be within [-180, 180]")
        if not (-90.0 <= south <= 90.0 and -90.0 <= north <= 90.0):
            raise ValueError("Latitudes must be within [-90, 90]")
        if west >= east:
            raise ValueError("west (min longitude) must be less than east (max longitude)")
        if south >= north:
            raise ValueError("south (min latitude) must be less than north (max latitude)")
        return v


class SatelliteProductMetadata(BaseModel):
    """Normalized metadata for a discovered satellite acquisition with full provenance."""
    id: str = Field(..., description="Unique product UUID from Copernicus Data Space.")
    name: str = Field(..., description="SAFE archive or COG product name.")
    collection: str = Field(..., description="'SENTINEL-1' or 'SENTINEL-2'")
    platform: str = Field(..., description="Satellite platform (e.g. S1A, S1D, S2A, S2C).")
    acquisition_time: str = Field(..., description="UTC ISO8601 acquisition start timestamp.")
    product_type: str = Field(..., description="Product level (e.g. IW_GRDH_1S, S2MSI2A, S2MSI1C).")
    orbit_direction: Optional[str] = Field(None, description="ASCENDING or DESCENDING.")
    relative_orbit: Optional[int] = Field(None, description="Track / relative orbit number.")
    operational_mode: Optional[str] = Field(None, description="Acquisition mode (e.g. IW, EW, SM).")
    polarization: Optional[str] = Field(None, description="Radar polarization channels (e.g. VV&VH).")
    cloud_cover_percentage: Optional[float] = Field(None, description="Scene-wide cloud coverage % (optical only).")
    size_mb: Optional[float] = Field(None, description="Reported archive size in Megabytes.")
    size_bytes: Optional[int] = Field(None, description="Reported archive size in bytes.")
    footprint_geojson: Optional[Dict[str, Any]] = Field(None, description="GeoJSON polygon of product footprint.")
    
    # Validation & Provenance
    intersects_aoi: bool = Field(..., description="Verified spatial intersection between footprint and AOI.")
    aoi_intersection_percent: float = Field(..., description="Percentage of requested AOI covered by this footprint.")
    timing: str = Field(..., description="'pre-event', 'post-event', or 'event-day'.")
    delta_days_from_event: float = Field(..., description="Signed days relative to event date (+/-).")
    selection_status: str = Field(
        ...,
        description="'recommended_pair', 'compatible_candidate', 'alternate_orbit', 'cloud_risk', 'rejected_no_intersection'"
    )
    selection_reason: str = Field(..., description="Detailed technical justification for selection or rejection.")
    
    # Audit trail
    retrieval_timestamp: str = Field(..., description="Timestamp when this catalog record was queried.")
    metadata_source: str = Field(default="Copernicus Data Space Ecosystem (CDSE) OData Catalogue")
    data_downloaded: bool = Field(default=False, description="Explicit confirmation that this product is discovered metadata only, not yet downloaded.")


class CandidatePairSummary(BaseModel):
    """Pair of compatible pre- and post-event SAR acquisitions for change detection."""
    pre_event_product_id: str
    pre_event_product_name: str
    pre_event_date: str
    post_event_product_id: str
    post_event_product_name: str
    post_event_date: str
    relative_orbit: int
    orbit_direction: str
    polarization: str
    temporal_baseline_days: float
    suitability_score: float = Field(..., description="Match quality score (0.0 to 1.0).")
    recommendation_reason: str


class CatalogSearchResponse(BaseModel):
    """Structured response for satellite catalog discovery."""
    search_id: str
    query_parameters: Dict[str, Any]
    retrieval_timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    total_discovered: int
    sentinel_1_count: int
    sentinel_2_count: int
    sentinel_1_candidates: List[SatelliteProductMetadata]
    sentinel_2_candidates: List[SatelliteProductMetadata]
    recommended_sar_pairs: List[CandidatePairSummary]
    warnings: List[str]
    metadata_source: str = "Copernicus Data Space Ecosystem (CDSE) OData Catalogue"
    data_downloaded: bool = Field(
        default=False,
        description="Affirmation that no raw satellite scene payloads were downloaded during discovery."
    )
