from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class TerrainAnalysisRequest(BaseModel):
    """Request parameters for real DEM terrain and slope analysis."""
    bbox: List[float] = Field(
        default=[85.10, 27.85, 85.25, 28.05],
        description="Bounding box [west, south, east, north] in EPSG:4326."
    )
    slope_threshold_deg: float = Field(
        default=5.0,
        description="Slope threshold in degrees to identify low-slope valley/basin floors."
    )
    elevation_threshold_m: Optional[float] = Field(
        default=800.0,
        description="Optional upper elevation limit (meters) for valley floor candidate identification."
    )


class TerrainStatistics(BaseModel):
    """Verified topographic statistics derived directly from DEM raster."""
    elevation_min_m: float
    elevation_max_m: float
    elevation_mean_m: float
    slope_min_deg: float
    slope_max_deg: float
    slope_mean_deg: float
    total_pixels: int
    low_slope_pixels: int
    low_slope_area_km2: float
    valley_candidate_pixels: int
    valley_candidate_area_km2: float


class TerrainAnalysisResponse(BaseModel):
    """Validated terrain and slope analysis response."""
    source_dem: str
    crs: str
    pixel_resolution_m: List[float]
    bounds: List[float]
    statistics: TerrainStatistics
    limitations: List[str]
    disclaimer: str
    geojson_layer: Optional[Dict[str, Any]] = None


class FloodScenarioRequest(BaseModel):
    """Request parameters for an explicitly labeled hypothetical flood scenario."""
    water_level_m: float = Field(
        default=500.0,
        ge=454.0,
        le=1200.0,
        description="Hypothetical stage elevation threshold in meters (Trishuli gorge base is ~455m)."
    )
    max_slope_deg: float = Field(
        default=8.0,
        description="Maximum slope to prevent steep hill slopes from being treated as water retention."
    )
    aoi_bbox: List[float] = Field(
        default=[85.10, 27.85, 85.25, 28.05]
    )


class FloodScenarioResponse(BaseModel):
    """Detailed output of a hypothetical terrain-based flood scenario."""
    is_hypothetical: bool = True
    scenario_name: str
    hypothesis_statement: str
    water_level_threshold_m: float
    max_slope_deg: float
    extent_area_km2: float
    geojson: Dict[str, Any]
    limitations: List[str]
    disclaimer: str


class InfrastructureExposureSummary(BaseModel):
    """Exposure statistics calculated strictly from spatial intersections."""
    is_confirmed_damage: bool = False
    flood_scenario_name: str
    total_buildings_mapped: int
    exposed_buildings_count: int
    exposed_buildings_percent: float
    total_road_length_km: float
    exposed_road_length_km: float
    exposed_road_percent: float
    total_bridges_mapped: int
    exposed_bridges_count: int
    health_facilities_mapped: int
    exposed_health_facilities_count: int
    isolated_settlements: List[str] = Field(default_factory=list)
    limitations: List[str]
    disclaimer: str
    geojson_layers: Dict[str, Any] = Field(default_factory=dict)


class SituationReportResponse(BaseModel):
    """Bilingual, verifiable situation report grounded strictly in computed metrics."""
    analysis_timestamp: str
    aoi_name: str
    data_sources: List[str]
    is_hypothetical_scenario: bool
    summary_metrics: Dict[str, Any]
    english_report: str
    nepali_report: str
    uncertainty_statement: str
