import pytest
import numpy as np
import rasterio
from rasterio.transform import from_bounds
from rasterio.crs import CRS
from pathlib import Path
from shapely.geometry import box

from backend.app.schemas.analysis import (
    TerrainAnalysisRequest,
    FloodScenarioRequest,
)
from backend.app.geospatial.terrain import (
    compute_terrain_and_slope,
    generate_hypothetical_flood_scenario,
)
from backend.app.geospatial.osm import parse_osm_geojson
from backend.app.geospatial.exposure import assess_infrastructure_exposure, calculate_line_length_km
from backend.app.reporting.copilot import generate_situation_report


@pytest.fixture
def aoi_bbox():
    return [85.10, 27.85, 85.25, 28.05]


def test_terrain_analysis_calculation(aoi_bbox):
    """Verify that real DEM terrain and slope analysis executes and computes valid statistics."""
    req = TerrainAnalysisRequest(bbox=aoi_bbox, slope_threshold_deg=5.0, elevation_threshold_m=800.0)
    res = compute_terrain_and_slope(req)

    assert res.statistics.elevation_min_m > 400.0
    assert res.statistics.elevation_max_m > 3000.0
    assert res.statistics.slope_mean_deg > 10.0
    assert res.statistics.valley_candidate_area_km2 > 0.0
    assert res.geojson_layer is not None
    assert "FeatureCollection" == res.geojson_layer["type"]
    assert "NOT satellite flood detection" in res.disclaimer


def test_terrain_analysis_non_intersecting_aoi_raises():
    """Verify that requesting an AOI outside DEM coverage raises ValueError."""
    # AOI in central Pacific Ocean
    req = TerrainAnalysisRequest(bbox=[-140.0, 0.0, -139.0, 1.0])
    with pytest.raises(ValueError) as exc:
        compute_terrain_and_slope(req)
    assert "does not intersect" in str(exc.value)


def test_hypothetical_flood_scenario_generation(aoi_bbox):
    """Verify that hypothetical flood scenario generates valid extent and explicit caveat."""
    req = FloodScenarioRequest(water_level_m=500.0, max_slope_deg=8.0, aoi_bbox=aoi_bbox)
    res = generate_hypothetical_flood_scenario(req)

    assert res.is_hypothetical is True
    assert res.extent_area_km2 > 0.0
    assert res.geojson["type"] == "FeatureCollection"
    assert "FOR PLANNING & SIMULATION DEMONSTRATION ONLY" in res.disclaimer
    for feat in res.geojson["features"]:
        assert feat["properties"]["is_satellite_observation"] is False


def test_osm_parsing_and_geojson_conversion():
    """Verify that Overpass elements are parsed accurately into categorized GeoJSON."""
    mock_osm = {
        "elements": [
            {"type": "node", "id": 1, "lat": 27.9, "lon": 85.15, "tags": {"amenity": "hospital", "name": "Trishuli Hospital"}},
            {"type": "node", "id": 2, "lat": 27.91, "lon": 85.16, "tags": {"place": "village", "name": "Bidur"}},
            {"type": "node", "id": 10, "lat": 27.90, "lon": 85.15},
            {"type": "node", "id": 11, "lat": 27.92, "lon": 85.15},
            {"type": "way", "id": 100, "nodes": [10, 11], "tags": {"highway": "primary", "bridge": "yes"}},
            {"type": "node", "id": 20, "lat": 27.90, "lon": 85.15},
            {"type": "node", "id": 21, "lat": 27.901, "lon": 85.15},
            {"type": "node", "id": 22, "lat": 27.901, "lon": 85.151},
            {"type": "node", "id": 23, "lat": 27.90, "lon": 85.151},
            {"type": "way", "id": 200, "nodes": [20, 21, 22, 23, 20], "tags": {"building": "yes"}},
        ]
    }
    parsed = parse_osm_geojson(mock_osm)
    assert len(parsed["amenities"]["features"]) == 1
    assert len(parsed["places"]["features"]) == 1
    assert len(parsed["roads"]["features"]) == 1
    assert len(parsed["bridges"]["features"]) == 1
    assert len(parsed["buildings"]["features"]) == 1


def test_exposure_assessment_with_intersections():
    """Verify infrastructure exposure spatial intersection, bridge cut detection, and metric calculation."""
    # Create synthetic flood polygon encompassing lat 27.89 to 27.91, lon 85.14 to 85.16
    flood_fc = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[85.14, 27.89], [85.16, 27.89], [85.16, 27.91], [85.14, 27.91], [85.14, 27.89]]]
                },
                "properties": {}
            }
        ]
    }

    mock_osm = {
        "amenities": {"type": "FeatureCollection", "features": [
            {"type": "Feature", "geometry": {"type": "Point", "coordinates": [85.15, 27.90]}, "properties": {"name": "Flooded Clinic"}},
            {"type": "Feature", "geometry": {"type": "Point", "coordinates": [85.20, 28.00]}, "properties": {"name": "Safe Hospital"}},
        ]},
        "places": {"type": "FeatureCollection", "features": [
            {"type": "Feature", "geometry": {"type": "Point", "coordinates": [85.15, 27.90]}, "properties": {"name": "River Village"}},
            {"type": "Feature", "geometry": {"type": "Point", "coordinates": [85.24, 28.04]}, "properties": {"name": "Hillside Village"}},
        ]},
        "roads": {"type": "FeatureCollection", "features": [
            {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[85.13, 27.90], [85.17, 27.90]]}, "properties": {"osm_id": 1, "name": "Highway 1"}},
            {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[85.20, 28.00], [85.22, 28.00]]}, "properties": {"osm_id": 2, "name": "Safe Road"}},
        ]},
        "bridges": {"type": "FeatureCollection", "features": [
            {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[85.145, 27.90], [85.155, 27.90]]}, "properties": {"osm_id": 101}},
        ]},
        "buildings": {"type": "FeatureCollection", "features": [
            {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [[[85.149, 27.899], [85.151, 27.899], [85.151, 27.901], [85.149, 27.901], [85.149, 27.899]]]}, "properties": {"osm_id": 201}},
            {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [[[85.20, 28.00], [85.21, 28.00], [85.21, 28.01], [85.20, 28.01], [85.20, 28.00]]]}, "properties": {"osm_id": 202}},
        ]},
    }

    exposure = assess_infrastructure_exposure(flood_fc, mock_osm, "Test Scenario")
    assert exposure.is_confirmed_damage is False
    assert exposure.exposed_buildings_count == 1
    assert exposure.total_buildings_mapped == 2
    assert exposure.exposed_bridges_count == 1
    assert exposure.exposed_health_facilities_count == 1
    assert exposure.exposed_road_length_km > 0.0
    assert any("River Village" in s for s in exposure.isolated_settlements)


def test_exposure_assessment_empty_flood_geojson():
    """Verify that empty flood extent returns zero exposures safely."""
    empty_fc = {"type": "FeatureCollection", "features": []}
    mock_osm = {"roads": {"features": []}, "bridges": {"features": []}, "buildings": {"features": []}, "amenities": {"features": []}, "places": {"features": []}}
    exp = assess_infrastructure_exposure(empty_fc, mock_osm)
    assert exp.exposed_buildings_count == 0
    assert exp.exposed_road_length_km == 0.0


def test_situation_report_generation_traceability():
    """Verify that situation report generates bilingual output traceable to computed values."""
    stats = {
        "elevation_min_m": 454.5,
        "elevation_max_m": 3378.8,
        "elevation_mean_m": 1106.6,
        "slope_mean_deg": 24.6,
        "valley_candidate_area_km2": 24.8,
    }
    exposure = {
        "exposed_road_length_km": 5.2,
        "total_road_length_km": 40.0,
        "exposed_buildings_count": 85,
        "total_buildings_mapped": 1200,
        "exposed_bridges_count": 3,
        "total_bridges_mapped": 10,
        "exposed_health_facilities_count": 1,
        "health_facilities_mapped": 4,
        "isolated_settlements": ["Tarkeshwar (direct flood zone overlap)"],
    }
    scenario = {
        "is_hypothetical": True,
        "water_level_m": 500.0,
        "max_slope_deg": 8.0,
        "extent_area_km2": 3.2,
    }

    rep = generate_situation_report(stats, exposure, scenario)
    assert rep.is_hypothetical_scenario is True
    assert "454.5" in rep.english_report
    assert "5.20 km" in rep.english_report
    assert "85 of 1200" in rep.english_report
    assert "Tarkeshwar" in rep.english_report
    # Nepali report verification
    assert "बाढीस्कोप एआई स्थिति प्रतिवेदन" in rep.nepali_report
    assert "454.5" in rep.nepali_report
    assert "85 घर/भवनहरू" in rep.nepali_report
