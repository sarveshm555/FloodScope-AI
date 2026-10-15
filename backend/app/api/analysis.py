import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query

from backend.app.core.config import settings

from backend.app.schemas.analysis import (
    TerrainAnalysisRequest,
    TerrainAnalysisResponse,
    FloodScenarioRequest,
    FloodScenarioResponse,
    InfrastructureExposureSummary,
    SituationReportResponse,
)
from backend.app.geospatial.terrain import (
    compute_terrain_and_slope,
    generate_hypothetical_flood_scenario,
)
from backend.app.geospatial.osm import fetch_osm_infrastructure, parse_osm_geojson, get_parsed_osm_infrastructure
from backend.app.geospatial.exposure import assess_infrastructure_exposure
from backend.app.geospatial.sar import load_cached_sar_flood_candidates
from backend.app.reporting.copilot import generate_situation_report

logger = logging.getLogger("floodscope.api.analysis")
router = APIRouter()


@router.post("/terrain", response_model=TerrainAnalysisResponse)
def analyze_terrain(request: TerrainAnalysisRequest) -> TerrainAnalysisResponse:
    """Analyze real DEM terrain, slope, and valley basin geometry."""
    try:
        return compute_terrain_and_slope(request)
    except Exception as e:
        logger.error(f"Terrain analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Terrain analysis failed: {str(e)}")


@router.post("/scenario", response_model=FloodScenarioResponse)
def compute_flood_scenario(request: FloodScenarioRequest) -> FloodScenarioResponse:
    """Generate an explicitly labeled, user-tunable hypothetical flood scenario from real DEM."""
    try:
        return generate_hypothetical_flood_scenario(request)
    except Exception as e:
        logger.error(f"Flood scenario generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Flood scenario failed: {str(e)}")


@router.get("/osm-infrastructure")
def get_osm_infrastructure(
    w: float = Query(85.10), s: float = Query(27.85),
    e: float = Query(85.25), n: float = Query(28.05)
):
    """Retrieve and parse real OpenStreetMap infrastructure (roads, bridges, buildings, clinics)."""
    try:
        raw_osm = fetch_osm_infrastructure([w, s, e, n])
        parsed = parse_osm_geojson(raw_osm)
        return parsed
    except Exception as exc:
        logger.error(f"OSM infrastructure retrieval failed: {exc}")
        raise HTTPException(status_code=500, detail=f"OSM retrieval failed: {str(exc)}")


@router.post("/exposure", response_model=InfrastructureExposureSummary)
def calculate_exposure(
    water_level_m: float = Query(500.0, ge=454.0, le=1200.0),
    max_slope_deg: float = Query(8.0, ge=1.0, le=45.0)
) -> InfrastructureExposureSummary:
    """Calculate infrastructure exposure by intersecting flood scenario with real OSM layers."""
    try:
        scenario_req = FloodScenarioRequest(water_level_m=water_level_m, max_slope_deg=max_slope_deg)
        scenario_res = generate_hypothetical_flood_scenario(scenario_req)
        parsed_osm = get_parsed_osm_infrastructure()
        exposure = assess_infrastructure_exposure(scenario_res.geojson, parsed_osm, scenario_res.scenario_name)
        return exposure
    except Exception as e:
        logger.error(f"Exposure calculation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Exposure calculation failed: {str(e)}")


@router.post("/situation-report", response_model=SituationReportResponse)
def create_situation_report(
    water_level_m: float = Query(500.0, ge=454.0, le=1200.0),
    max_slope_deg: float = Query(8.0, ge=1.0, le=45.0)
) -> SituationReportResponse:
    """Generate bilingual (English/Nepali) situation report grounded strictly in computed metrics."""
    try:
        terrain_res = compute_terrain_and_slope(TerrainAnalysisRequest())
        scenario_req = FloodScenarioRequest(water_level_m=water_level_m, max_slope_deg=max_slope_deg)
        scenario_res = generate_hypothetical_flood_scenario(scenario_req)
        parsed_osm = get_parsed_osm_infrastructure()
        exposure = assess_infrastructure_exposure(scenario_res.geojson, parsed_osm, scenario_res.scenario_name)

        report = generate_situation_report(
            terrain_stats=terrain_res.statistics.model_dump(),
            exposure_summary=exposure.model_dump(),
            scenario_info=scenario_res.model_dump(),
            aoi_name="Trishuli River Basin, Nuwakot District, Nepal"
        )
        return report
    except Exception as e:
        logger.error(f"Situation report generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Situation report failed: {str(e)}")


@router.get("/sar-flood-candidates")
def get_sar_flood_candidates():
    """Retrieve verified Sentinel-1 SAR bitemporal candidate flood polygons and exposure metrics."""
    try:
        return load_cached_sar_flood_candidates(settings.data_dir)
    except Exception as exc:
        logger.error(f"Failed to read SAR flood candidates: {exc}")
        raise HTTPException(status_code=500, detail=f"Failed to read SAR flood candidates: {str(exc)}")
