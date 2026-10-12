import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import requests
from backend.app.main import app
from backend.app.schemas.catalog import CatalogSearchRequest, CatalogSearchResponse
from backend.app.geospatial.catalog import (
    check_footprint_intersection,
    normalize_product_record,
    match_candidate_sar_pairs,
    execute_catalog_discovery,
)
from datetime import datetime, timezone

client = TestClient(app)

# Sample mock CDSE Sentinel-1 response record (intersecting Trishuli)
MOCK_S1_PRE = {
    "Id": "s1-pre-uuid-1",
    "Name": "S1D_IW_GRDH_1SDV_20260816T122141_20260816T122206_004151_007980_C3AB.SAFE",
    "ContentLength": 1732890624,
    "ContentDate": {"Start": "2026-08-16T12:21:41.000Z", "End": "2026-08-16T12:22:06.000Z"},
    "GeoFootprint": {
        "type": "Polygon",
        "coordinates": [[[84.5, 27.5], [85.5, 27.5], [85.5, 28.5], [84.5, 28.5], [84.5, 27.5]]]
    },
    "Attributes": [
        {"Name": "orbitDirection", "Value": "ASCENDING"},
        {"Name": "relativeOrbitNumber", "Value": "85"},
        {"Name": "operationalMode", "Value": "IW"},
        {"Name": "polarisationChannels", "Value": "VV&VH"},
        {"Name": "productType", "Value": "IW_GRDH_1S"}
    ]
}

MOCK_S1_POST = {
    "Id": "s1-post-uuid-2",
    "Name": "S1D_IW_GRDH_1SDV_20260828T122141_20260828T122206_004326_007FA4_01B4.SAFE",
    "ContentLength": 1732890624,
    "ContentDate": {"Start": "2026-08-28T12:21:41.000Z", "End": "2026-08-28T12:22:06.000Z"},
    "GeoFootprint": {
        "type": "Polygon",
        "coordinates": [[[84.5, 27.5], [85.5, 27.5], [85.5, 28.5], [84.5, 28.5], [84.5, 27.5]]]
    },
    "Attributes": [
        {"Name": "orbitDirection", "Value": "ASCENDING"},
        {"Name": "relativeOrbitNumber", "Value": "85"},
        {"Name": "operationalMode", "Value": "IW"},
        {"Name": "polarisationChannels", "Value": "VV&VH"},
        {"Name": "productType", "Value": "IW_GRDH_1S"}
    ]
}

MOCK_S1_NON_INTERSECTING = {
    "Id": "s1-non-intersecting-3",
    "Name": "S1D_IW_GRDH_1SDV_20260820T000000_20260820T000025_000000_000000_0000.SAFE",
    "ContentLength": 1732890624,
    "ContentDate": {"Start": "2026-08-20T00:00:00.000Z"},
    "GeoFootprint": {
        "type": "Polygon",
        "coordinates": [[[10.0, 50.0], [11.0, 50.0], [11.0, 51.0], [10.0, 51.0], [10.0, 50.0]]]
    },
    "Attributes": [
        {"Name": "orbitDirection", "Value": "DESCENDING"},
        {"Name": "relativeOrbitNumber", "Value": "12"},
        {"Name": "operationalMode", "Value": "IW"},
        {"Name": "polarisationChannels", "Value": "VV&VH"},
    ]
}

MOCK_S2_RECORD = {
    "Id": "s2-opt-uuid-4",
    "Name": "S2B_MSIL2A_20260824T044659_N0512_R076_T45RUM_20260824T083447.SAFE",
    "ContentLength": 1150000000,
    "ContentDate": {"Start": "2026-08-24T04:46:59.000Z"},
    "GeoFootprint": {
        "type": "Polygon",
        "coordinates": [[[84.8, 27.6], [85.4, 27.6], [85.4, 28.2], [84.8, 28.2], [84.8, 27.6]]]
    },
    "Attributes": [
        {"Name": "cloudCover", "Value": "38.5"},
        {"Name": "productType", "Value": "S2MSI2A"},
        {"Name": "orbitDirection", "Value": "DESCENDING"}
    ]
}


def test_footprint_intersection_calculation():
    """Verify spatial intersection calculation between AOI and GeoJSON footprint."""
    aoi_bbox = [85.10, 27.85, 85.25, 28.05]
    # Completely containing polygon
    contained_fp = {
        "type": "Polygon",
        "coordinates": [[[85.0, 27.8], [85.3, 27.8], [85.3, 28.1], [85.0, 28.1], [85.0, 27.8]]]
    }
    intersects, pct = check_footprint_intersection(contained_fp, aoi_bbox)
    assert intersects is True
    assert pct == 100.0

    # Outside polygon (Germany)
    outside_fp = {
        "type": "Polygon",
        "coordinates": [[[10.0, 50.0], [11.0, 50.0], [11.0, 51.0], [10.0, 51.0], [10.0, 50.0]]]
    }
    intersects_out, pct_out = check_footprint_intersection(outside_fp, aoi_bbox)
    assert intersects_out is False
    assert pct_out == 0.0


def test_normalize_product_record_handling():
    """Verify that normalize_product_record extracts metadata correctly without error."""
    aoi_bbox = [85.10, 27.85, 85.25, 28.05]
    event_dt = datetime(2026, 8, 26, 0, 0, tzinfo=timezone.utc)
    retrieval_ts = datetime.now(timezone.utc).isoformat()

    norm = normalize_product_record(MOCK_S1_PRE, aoi_bbox, event_dt, retrieval_ts)
    assert norm.id == "s1-pre-uuid-1"
    assert norm.platform == "S1D"
    assert norm.collection == "SENTINEL-1"
    assert norm.relative_orbit == 85
    assert norm.orbit_direction == "ASCENDING"
    assert norm.timing == "pre-event"
    assert norm.intersects_aoi is True
    assert norm.data_downloaded is False


def test_sar_pair_matching():
    """Verify that pre- and post-event observations with matched orbits are paired."""
    aoi_bbox = [85.10, 27.85, 85.25, 28.05]
    event_dt = datetime(2026, 8, 26, 0, 0, tzinfo=timezone.utc)
    ts = datetime.now(timezone.utc).isoformat()

    c1 = normalize_product_record(MOCK_S1_PRE, aoi_bbox, event_dt, ts)
    c2 = normalize_product_record(MOCK_S1_POST, aoi_bbox, event_dt, ts)
    c3 = normalize_product_record(MOCK_S1_NON_INTERSECTING, aoi_bbox, event_dt, ts)

    updated, pairs = match_candidate_sar_pairs([c1, c2, c3])
    assert len(pairs) == 1
    pair = pairs[0]
    assert pair.relative_orbit == 85
    assert pair.orbit_direction == "ASCENDING"
    assert pair.temporal_baseline_days == 12.0
    assert pair.suitability_score == 1.0

    # Recommended products should have updated selection_status
    recs = [c for c in updated if c.selection_status == "recommended_pair"]
    assert len(recs) == 2


@patch("backend.app.geospatial.catalog.requests.Session.get")
def test_successful_catalog_search(mock_get):
    """Verify that execute_catalog_discovery parses responses and creates matched pairs."""
    # Mocking CDSE OData responses: first for S1, second for S2
    mock_resp1 = MagicMock()
    mock_resp1.status_code = 200
    mock_resp1.json.return_value = {"value": [MOCK_S1_PRE, MOCK_S1_POST, MOCK_S1_NON_INTERSECTING]}

    mock_resp2 = MagicMock()
    mock_resp2.status_code = 200
    mock_resp2.json.return_value = {"value": [MOCK_S2_RECORD]}

    mock_get.side_effect = [mock_resp1, mock_resp2]

    req = CatalogSearchRequest(
        bbox=[85.10, 27.85, 85.25, 28.05],
        event_date="2026-08-26",
        pre_days=15,
        post_days=15
    )
    result = execute_catalog_discovery(req)
    assert result.total_discovered == 4
    assert result.sentinel_1_count == 3
    assert result.sentinel_2_count == 1
    assert len(result.recommended_sar_pairs) == 1
    assert result.data_downloaded is False
    assert result.metadata_source == "Copernicus Data Space Ecosystem (CDSE) OData Catalogue"


@patch("backend.app.geospatial.catalog.requests.Session.get")
def test_catalog_search_endpoint_api(mock_get):
    """Verify POST /api/catalog/search API endpoint."""
    mock_resp1 = MagicMock()
    mock_resp1.status_code = 200
    mock_resp1.json.return_value = {"value": [MOCK_S1_PRE, MOCK_S1_POST]}

    mock_resp2 = MagicMock()
    mock_resp2.status_code = 200
    mock_resp2.json.return_value = {"value": []}

    mock_get.side_effect = [mock_resp1, mock_resp2]

    response = client.post(
        "/api/catalog/search",
        json={
            "bbox": [85.10, 27.85, 85.25, 28.05],
            "event_date": "2026-08-26",
            "pre_days": 10,
            "post_days": 10
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "search_id" in data
    assert data["sentinel_1_count"] == 2
    assert len(data["recommended_sar_pairs"]) == 1
    assert data["data_downloaded"] is False

    # Test retrieval by search_id
    search_id = data["search_id"]
    get_res = client.get(f"/api/catalog/results/{search_id}")
    assert get_res.status_code == 200
    assert get_res.json()["search_id"] == search_id


@patch("backend.app.geospatial.catalog.requests.Session.get")
def test_timeout_and_error_handling(mock_get):
    """Verify that HTTP timeouts in CDSE catalog produce clean warnings without crashing."""
    mock_get.side_effect = requests.exceptions.Timeout("Connection timed out")

    req = CatalogSearchRequest(
        bbox=[85.10, 27.85, 85.25, 28.05],
        event_date="2026-08-26"
    )
    result = execute_catalog_discovery(req)
    assert result.total_discovered == 0
    assert len(result.warnings) > 0
    assert result.data_downloaded is False


@patch("backend.app.geospatial.catalog.requests.Session.get")
def test_empty_catalog_results(mock_get):
    """Verify that an empty response from CDSE produces valid schema and 0 candidates."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"value": []}
    mock_get.return_value = mock_resp

    req = CatalogSearchRequest(
        bbox=[85.10, 27.85, 85.25, 28.05],
        event_date="2026-08-26"
    )
    result = execute_catalog_discovery(req)
    assert result.total_discovered == 0
    assert len(result.sentinel_1_candidates) == 0
    assert len(result.recommended_sar_pairs) == 0


def test_catalog_missing_search_id_returns_404():
    """Verify that querying a nonexistent search_id returns 404."""
    resp = client.get("/api/catalog/results/non-existent-uuid-999")
    assert resp.status_code == 404


def test_health_endpoint_regression():
    """Ensure GET /api/health continues to function after catalog router addition."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "operational"
    assert data["services"]["copernicus_catalog_available"] is True
