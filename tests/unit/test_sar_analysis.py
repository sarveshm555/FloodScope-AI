import json
import hashlib
import pytest
from pathlib import Path
from unittest.mock import patch, PropertyMock

import numpy as np
import rasterio
from rasterio.transform import from_bounds
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.config import AppSettings, settings, PROJECT_ROOT
import backend.app.geospatial.sar as sar_module
from backend.app.geospatial.manifest import load_manifest
from backend.app.schemas.downloads import DataManifest, AcquiredProductManifestEntry
from backend.app.geospatial.sar import (
    compute_wgs84_cell_metrics,
    calibrate_dn_to_sigma0_db,
    compute_dem_slope,
    apply_speckle_filter,
    classify_sar_change,
    validate_sar_inputs,
    run_sar_change_detection,
)


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    return TestClient(app)


@pytest.fixture
def synthetic_sar_bundle(tmp_path):
    """Sets up an isolated, temporary SAR directory with synthetic candidate artifacts."""
    sar_dir = tmp_path / "processed" / "sentinel1"
    sar_dir.mkdir(parents=True, exist_ok=True)

    summary_content = {
        "metadata": {
            "analysis_type": "Sentinel-1 SAR Bitemporal Change Detection",
            "study_area": "Trishuli River Basin, Nuwakot & Rasuwa, Nepal",
            "aoi_bbox": [85.10, 27.85, 85.25, 28.05],
            "pre_event_product": "S1D_IW_GRDH_1SDV_20260816T122141_TEST",
            "pre_event_date": "2026-08-16T12:21:41Z",
            "post_event_product": "S1D_IW_GRDH_1SDV_20260828T122141_TEST",
            "post_event_date": "2026-08-28T12:21:41Z",
            "polarization": "VV",
            "orbit": "Ascending Orbit Track 85",
            "temporal_baseline_days": 12.0,
            "grid_resolution_m": 10.0,
            "crs": "EPSG:4326",
            "calibration": "Radiometric sigma0 conversion (A=708.0)",
            "speckle_filter": "3x3 Median Spatial Filter",
            "dem_topographic_filter": "Copernicus GLO-30 Slope <= 10 deg, Elevation <= 1200m",
            "change_threshold_db": "<= -2.5 dB drop and post-event <= -14.5 dB",
            "permanent_water_exclusion": "Pre-event baseline <= -16.0 dB",
            "generated_at": "2026-10-15 06:00:00 UTC"
        },
        "results": {
            "candidate_flood_area_km2": 0.55,
            "permanent_water_area_km2": 2.45,
            "candidate_flood_pixel_count": 5100,
            "infrastructure_exposure": {
                "exposed_road_length_km": 1.10,
                "total_mapped_road_km": 210.00,
                "exposed_bridges_count": 0,
                "total_mapped_bridges": 55,
                "exposed_buildings_count": 320,
                "total_mapped_buildings": 54000,
                "exposed_clinics_count": 0,
                "total_mapped_clinics": 8
            }
        }
    }

    geojson_content = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": "s1_candidate_0",
                "properties": {
                    "source": "Sentinel-1 C-SAR (Ascending Track 85)",
                    "pre_event_date": "2026-08-16T12:21:41Z",
                    "post_event_date": "2026-08-28T12:21:41Z",
                    "area_km2": 0.0125,
                    "confidence": "Satellite Observation Candidate"
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [85.150, 27.900],
                            [85.155, 27.900],
                            [85.155, 27.905],
                            [85.150, 27.905],
                            [85.150, 27.900]
                        ]
                    ]
                }
            },
            {
                "type": "Feature",
                "id": "s1_candidate_1",
                "properties": {
                    "source": "Sentinel-1 C-SAR (Ascending Track 85)",
                    "pre_event_date": "2026-08-16T12:21:41Z",
                    "post_event_date": "2026-08-28T12:21:41Z",
                    "area_km2": 0.0080,
                    "confidence": "Satellite Observation Candidate"
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [85.180, 27.950],
                            [85.184, 27.950],
                            [85.184, 27.954],
                            [85.180, 27.954],
                            [85.180, 27.950]
                        ]
                    ]
                }
            }
        ]
    }

    summary_file = sar_dir / "s1_sar_change_summary.json"
    geojson_file = sar_dir / "s1_sar_flood_candidates.geojson"

    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary_content, f)

    with open(geojson_file, "w", encoding="utf-8") as f:
        json.dump(geojson_content, f)

    return tmp_path, summary_file, geojson_file


def test_sar_candidates_live_endpoint_when_artifacts_exist(client):
    """Verify live endpoint response if real project artifacts exist on disk."""
    summary_path = settings.data_dir / "processed" / "sentinel1" / "s1_sar_change_summary.json"
    geojson_path = settings.data_dir / "processed" / "sentinel1" / "s1_sar_flood_candidates.geojson"

    if not summary_path.exists() or not geojson_path.exists():
        pytest.skip("Live SAR artifacts not present on this machine; skipping live test.")

    response = client.get("/api/analysis/sar-flood-candidates")
    assert response.status_code == 200
    data = response.json()
    assert data.get("available") is True
    assert "summary" in data
    assert "geojson" in data
    assert data["geojson"].get("type") == "FeatureCollection"
    assert len(data["geojson"].get("features", [])) > 0


def test_sar_candidates_isolated_synthetic_response(client, synthetic_sar_bundle):
    """Verify endpoint successfully returns synthetic artifacts from an isolated test directory."""
    tmp_path, _, _ = synthetic_sar_bundle
    with patch.object(AppSettings, "data_dir", new_callable=PropertyMock, return_value=tmp_path):
        response = client.get("/api/analysis/sar-flood-candidates")
        assert response.status_code == 200
        data = response.json()
        assert data.get("available") is True
        assert "summary" in data
        assert "geojson" in data


def test_sar_candidates_schema_and_metadata_integrity(client, synthetic_sar_bundle):
    """Verify response schema, required metadata, and non-empty result values."""
    tmp_path, _, _ = synthetic_sar_bundle
    with patch.object(AppSettings, "data_dir", new_callable=PropertyMock, return_value=tmp_path):
        response = client.get("/api/analysis/sar-flood-candidates")
        assert response.status_code == 200
        data = response.json()

        summary = data["summary"]
        assert "metadata" in summary
        assert "results" in summary

        meta = summary["metadata"]
        required_meta_keys = [
            "analysis_type",
            "study_area",
            "aoi_bbox",
            "pre_event_product",
            "pre_event_date",
            "post_event_product",
            "post_event_date",
            "polarization",
            "orbit",
            "grid_resolution_m",
            "crs",
            "calibration",
            "speckle_filter",
            "dem_topographic_filter",
            "change_threshold_db",
            "permanent_water_exclusion",
        ]
        for key in required_meta_keys:
            assert key in meta, f"Missing required metadata key: {key}"

        bbox = meta["aoi_bbox"]
        assert isinstance(bbox, list) and len(bbox) == 4
        assert bbox[0] < bbox[2], "BBox min_lon must be less than max_lon"
        assert bbox[1] < bbox[3], "BBox min_lat must be less than max_lat"

        results = summary["results"]
        assert isinstance(results["candidate_flood_area_km2"], (int, float))
        assert results["candidate_flood_area_km2"] >= 0.0
        assert isinstance(results["permanent_water_area_km2"], (int, float))
        assert results["permanent_water_area_km2"] >= 0.0
        assert isinstance(results["candidate_flood_pixel_count"], int)
        assert results["candidate_flood_pixel_count"] >= 0

        exposure = results["infrastructure_exposure"]
        assert "exposed_road_length_km" in exposure
        assert "total_mapped_road_km" in exposure
        assert "exposed_bridges_count" in exposure
        assert "exposed_buildings_count" in exposure


def test_sar_candidates_geojson_feature_validation(client, synthetic_sar_bundle):
    """Verify GeoJSON validity, feature geometries, closed coordinate rings, and property schema."""
    tmp_path, _, _ = synthetic_sar_bundle
    with patch.object(AppSettings, "data_dir", new_callable=PropertyMock, return_value=tmp_path):
        response = client.get("/api/analysis/sar-flood-candidates")
        assert response.status_code == 200
        fc = response.json()["geojson"]

        assert fc.get("type") == "FeatureCollection"
        features = fc.get("features", [])
        assert len(features) > 0

        for feat in features:
            assert feat.get("type") == "Feature"
            assert "geometry" in feat
            assert "properties" in feat

            geom = feat["geometry"]
            assert geom.get("type") in ("Polygon", "MultiPolygon")
            coords = geom.get("coordinates", [])
            assert len(coords) > 0

            if geom["type"] == "Polygon":
                for ring in coords:
                    assert len(ring) >= 4, "A polygon linear ring must contain at least 4 coordinate positions"
                    assert ring[0] == ring[-1], "Polygon linear ring must be closed (start == end)"
                    for pt in ring:
                        assert isinstance(pt[0], (int, float))
                        assert isinstance(pt[1], (int, float))
                        assert -180.0 <= pt[0] <= 180.0
                        assert -90.0 <= pt[1] <= 90.0


def test_candidate_inundation_not_labeled_as_confirmed_damage(client, synthetic_sar_bundle):
    """Verify candidate inundation is explicitly distinguished from confirmed structural damage."""
    tmp_path, _, _ = synthetic_sar_bundle
    with patch.object(AppSettings, "data_dir", new_callable=PropertyMock, return_value=tmp_path):
        response = client.get("/api/analysis/sar-flood-candidates")
        assert response.status_code == 200
        data = response.json()

        for feat in data["geojson"].get("features", []):
            props = feat.get("properties", {})
            confidence = props.get("confidence", "")
            assert "Candidate" in confidence or "Observation" in confidence
            assert "confirmed damage" not in confidence.lower()
            assert "confirmed destruction" not in confidence.lower()

        raw_text = response.text.lower()
        assert "confirmed structural damage" not in raw_text
        assert "confirmed building collapse" not in raw_text


def test_sar_candidates_missing_artifacts_returns_unavailable(client, tmp_path):
    """Verify endpoint returns available=False when artifacts do not exist on disk."""
    empty_dir = tmp_path / "empty_dir"
    empty_dir.mkdir()
    with patch.object(AppSettings, "data_dir", new_callable=PropertyMock, return_value=empty_dir):
        response = client.get("/api/analysis/sar-flood-candidates")
        assert response.status_code == 200
        data = response.json()
        assert data.get("available") is False
        assert "message" in data
        assert "not yet generated" in data["message"].lower()


def test_sar_candidates_partial_artifacts_returns_unavailable(client, tmp_path):
    """Verify endpoint returns available=False if only one of summary or geojson is present."""
    sar_dir = tmp_path / "processed" / "sentinel1"
    sar_dir.mkdir(parents=True)

    summary_file = sar_dir / "s1_sar_change_summary.json"
    geojson_file = sar_dir / "s1_sar_flood_candidates.geojson"

    # Subcase A: summary exists, geojson missing
    summary_file.write_text('{"metadata": {}}', encoding="utf-8")
    with patch.object(AppSettings, "data_dir", new_callable=PropertyMock, return_value=tmp_path):
        res_a = client.get("/api/analysis/sar-flood-candidates")
        assert res_a.status_code == 200
        assert res_a.json().get("available") is False

    # Subcase B: geojson exists, summary missing
    summary_file.unlink()
    geojson_file.write_text('{"type": "FeatureCollection", "features": []}', encoding="utf-8")
    with patch.object(AppSettings, "data_dir", new_callable=PropertyMock, return_value=tmp_path):
        res_b = client.get("/api/analysis/sar-flood-candidates")
        assert res_b.status_code == 200
        assert res_b.json().get("available") is False


def test_sar_candidates_malformed_json_returns_500(client, tmp_path):
    """Verify endpoint returns HTTP 500 when artifacts are corrupted or malformed."""
    sar_dir = tmp_path / "processed" / "sentinel1"
    sar_dir.mkdir(parents=True)

    # Corrupt JSON syntax in summary file
    (sar_dir / "s1_sar_change_summary.json").write_text("{corrupt_json: true,", encoding="utf-8")
    (sar_dir / "s1_sar_flood_candidates.geojson").write_text("{}", encoding="utf-8")

    with patch.object(AppSettings, "data_dir", new_callable=PropertyMock, return_value=tmp_path):
        response = client.get("/api/analysis/sar-flood-candidates")
        assert response.status_code == 500
        assert "Failed to read SAR flood candidates" in response.json().get("detail", "")


def test_no_expensive_pipeline_or_network_invoked(client, synthetic_sar_bundle):
    """Verify GET /api/analysis/sar-flood-candidates performs fast I/O without triggering raster warping or network downloads."""
    tmp_path, _, _ = synthetic_sar_bundle
    with patch("requests.get") as mock_http, patch("rasterio.open") as mock_raster:
        with patch.object(AppSettings, "data_dir", new_callable=PropertyMock, return_value=tmp_path):
            response = client.get("/api/analysis/sar-flood-candidates")
            assert response.status_code == 200
            mock_http.assert_not_called()
            mock_raster.assert_not_called()


def test_compute_wgs84_cell_metrics_validates_and_computes():
    """Verify geodesic ellipsoidal cell dimensions and area calculation in EPSG:4326."""
    west, south, east, north = 85.10, 27.85, 85.25, 28.05
    dx, dy, area_m2 = compute_wgs84_cell_metrics(west, south, east, north, width=1500, height=2000)

    # In Himalayan latitudes (~28 N), longitudinal degree spacing is narrower than latitudinal spacing
    assert dx > 0.0
    assert dy > 0.0
    assert dx < dy, "At latitude ~28 N, longitudinal spacing dx must be smaller than latitudinal dy"
    assert 9.0 <= dx <= 11.0
    assert 10.0 <= dy <= 12.0
    assert 90.0 <= area_m2 <= 130.0

    # Validation errors on inverted or degenerate bounding boxes
    with pytest.raises(ValueError) as exc1:
        compute_wgs84_cell_metrics(85.25, 27.85, 85.10, 28.05, 100, 100)
    assert "Invalid bounding box" in str(exc1.value)

    with pytest.raises(ValueError) as exc2:
        compute_wgs84_cell_metrics(west, south, east, north, width=0, height=100)
    assert "width and height must be positive" in str(exc2.value)


def test_calibrate_dn_to_sigma0_db_formula():
    """Verify radiometric calibration formula sigma0_dB = 20*log10(DN) - 20*log10(A)."""
    # When DN == A (708.0), sigma0_dB should be exactly 0.0 dB
    dn_unit = np.array([708.0], dtype=np.float32)
    sigma0_unit = calibrate_dn_to_sigma0_db(dn_unit, calibration_constant=708.0)
    assert np.isclose(sigma0_unit[0], 0.0, atol=1e-4)

    # When DN == 70.8 (10x smaller), sigma0_dB should be -20.0 dB
    dn_tenth = np.array([70.8], dtype=np.float32)
    sigma0_tenth = calibrate_dn_to_sigma0_db(dn_tenth, calibration_constant=708.0)
    assert np.isclose(sigma0_tenth[0], -20.0, atol=1e-3)

    # Safe handling of 0.0 DN (must not produce NaN or -inf)
    dn_zero = np.array([0.0], dtype=np.float32)
    sigma0_zero = calibrate_dn_to_sigma0_db(dn_zero, calibration_constant=708.0)
    assert not np.isnan(sigma0_zero[0])
    assert not np.isinf(sigma0_zero[0])

    # Error on invalid calibration constant
    with pytest.raises(ValueError) as exc:
        calibrate_dn_to_sigma0_db(dn_unit, calibration_constant=-1.0)
    assert "Calibration constant A must be positive" in str(exc.value)


def test_compute_dem_slope_gradient():
    """Verify topographic surface slope computation from elevation array and metric spacing."""
    dx_m = 10.0
    dy_m = 10.0

    # Flat elevation grid should produce 0.0 degree slope everywhere
    flat_dem = np.full((10, 10), 500.0, dtype=np.float32)
    flat_slope = compute_dem_slope(flat_dem, dx_m, dy_m)
    assert np.allclose(flat_slope, 0.0, atol=1e-5)

    # Uniform 45-degree ramp along x: dz/dx = 1.0 (10m rise per 10m run)
    ramp_x = np.tile(np.arange(10, dtype=np.float32) * 10.0, (10, 1))
    ramp_slope = compute_dem_slope(ramp_x, dx_m, dy_m)
    # Interior pixels should be exactly 45.0 degrees
    assert np.isclose(ramp_slope[2:8, 2:8], 45.0, atol=1e-3).all()

    # Invalid metric spacing raises ValueError
    with pytest.raises(ValueError) as exc:
        compute_dem_slope(flat_dem, dx_m=0.0, dy_m=10.0)
    assert "Grid metric spacing" in str(exc.value)


def test_apply_speckle_filter_suppresses_noise():
    """Verify median filter suppresses isolated impulsive noise spikes."""
    grid = np.full((7, 7), 10.0, dtype=np.float32)
    grid[3, 3] = 1000.0  # single-pixel spike
    filtered = apply_speckle_filter(grid, filter_size=3)
    assert filtered[3, 3] == 10.0, "Median filter should suppress isolated speckle spike"


def test_classify_sar_change_multi_criteria_logic():
    """Verify multi-criteria classification: change threshold, post threshold, slope filter, elevation filter, and speckle opening."""
    # Setup 10x10 synthetic arrays
    pre_db = np.full((10, 10), -10.0, dtype=np.float32)
    post_db = np.full((10, 10), -10.0, dtype=np.float32)
    slope = np.full((10, 10), 2.0, dtype=np.float32)
    elev = np.full((10, 10), 600.0, dtype=np.float32)

    # 1. Candidate flood block (3x3 block): drop from -10 to -18 dB (diff = -8 dB <= -2.5 dB, post = -18 <= -14.5 dB)
    post_db[2:5, 2:5] = -18.0

    # 2. Steep slope block (3x3): steep valley wall slope = 25 deg > 10 deg (should be excluded as radar shadow)
    slope[2:5, 6:9] = 25.0
    post_db[2:5, 6:9] = -18.0

    # 3. High elevation block: elev = 1500m > 1200m (should be excluded)
    elev[6:9, 2:5] = 1500.0
    post_db[6:9, 2:5] = -18.0

    # 4. Permanent water: pre-event already low backscatter <= -16 dB
    pre_db[6:9, 6:9] = -18.0
    post_db[6:9, 6:9] = -18.0

    # 5. Single isolated candidate pixel (should be removed by 2x2 binary opening)
    post_db[0, 0] = -18.0

    candidate_mask, perm_water_mask = classify_sar_change(
        pre_sigma_db=pre_db,
        post_sigma_db=post_db,
        slope_deg=slope,
        dem_elevation_m=elev,
        slope_threshold_deg=10.0,
        elevation_threshold_m=1200.0,
        change_threshold_db=-2.5,
        post_water_threshold_db=-14.5,
        permanent_water_threshold_db=-16.0,
    )

    # Block 1 should be candidate flood
    assert candidate_mask[3, 3] is True or candidate_mask[3, 3] == 1
    # Block 2 (steep slope) must be rejected
    assert not candidate_mask[3, 7]
    # Block 3 (high elevation) must be rejected
    assert not candidate_mask[7, 3]
    # Block 4 (permanent water) must be marked permanent water, not candidate flood
    assert perm_water_mask[7, 7] is True or perm_water_mask[7, 7] == 1
    assert not candidate_mask[7, 7]
    # Single isolated pixel at (0, 0) should be removed by opening
    assert not candidate_mask[0, 0]


def test_validate_sar_inputs_failure_modes(tmp_path):
    """Verify validate_sar_inputs raises appropriate exceptions on missing files or invalid bounds."""
    w, s, e, n = 85.10, 27.85, 85.25, 28.05
    transform = from_bounds(w, s, e, n, 10, 10)

    pre_file = tmp_path / "valid_pre.tif"
    with rasterio.open(pre_file, "w", driver="GTiff", width=10, height=10, count=1, dtype=np.float32, crs="EPSG:4326", transform=transform) as dst:
        dst.write(np.ones((10, 10), dtype=np.float32), 1)

    # 1. Missing file raises FileNotFoundError
    with pytest.raises(FileNotFoundError) as exc1:
        validate_sar_inputs(pre_file, tmp_path / "nonexistent.tif", pre_file, [w, s, e, n])
    assert "does not exist" in str(exc1.value)

    # 2. Inverted bounding box raises ValueError
    with pytest.raises(ValueError) as exc2:
        validate_sar_inputs(pre_file, pre_file, pre_file, [e, s, w, n])
    assert "Invalid aoi_bbox" in str(exc2.value)


def test_run_sar_change_detection_synthetic_pipeline_end_to_end(tmp_path):
    """Verify service function run_sar_change_detection produces valid GeoTIFF, GeoJSON, and summary outputs."""
    w, s, e, n = 85.10, 27.85, 85.25, 28.05
    transform = from_bounds(w, s, e, n, 12, 12)

    pre_file = tmp_path / "pre.tif"
    with rasterio.open(pre_file, "w", driver="GTiff", width=12, height=12, count=1, dtype=np.float32, crs="EPSG:4326", transform=transform) as dst:
        dst.write(np.full((12, 12), 1000.0, dtype=np.float32), 1)

    post_file = tmp_path / "post.tif"
    post_data = np.full((12, 12), 1000.0, dtype=np.float32)
    post_data[4:8, 4:8] = 50.0  # Significant backscatter drop block
    with rasterio.open(post_file, "w", driver="GTiff", width=12, height=12, count=1, dtype=np.float32, crs="EPSG:4326", transform=transform) as dst:
        dst.write(post_data, 1)

    dem_file = tmp_path / "dem.tif"
    with rasterio.open(dem_file, "w", driver="GTiff", width=12, height=12, count=1, dtype=np.float32, crs="EPSG:4326", transform=transform) as dst:
        dst.write(np.full((12, 12), 500.0, dtype=np.float32), 1)

    out_dir = tmp_path / "output_sar"
    result = run_sar_change_detection(
        pre_vv_path=pre_file,
        post_vv_path=post_file,
        dem_path=dem_file,
        output_dir=out_dir,
        aoi_bbox=[w, s, e, n],
        width=12,
        height=12,
    )

    # 1. Result dictionary contract
    assert "summary" in result
    assert "geojson" in result

    # 2. Output files existence
    expected_files = [
        out_dir / "s1_sar_flood_candidates_10m.tif",
        out_dir / "s1_sar_flood_candidates.geojson",
        out_dir / "s1_sar_change_summary.json",
    ]
    for ef in expected_files:
        assert ef.exists(), f"Expected artifact missing: {ef}"

    # 3. GeoTIFF properties
    with rasterio.open(out_dir / "s1_sar_flood_candidates_10m.tif") as tif:
        assert tif.width == 12
        assert tif.height == 12
        assert str(tif.crs) == "EPSG:4326"
        arr = tif.read(1)
        # Class 2 is flood candidate
        assert 2 in arr

    # 4. GeoJSON structure
    fc = result["geojson"]
    assert fc["type"] == "FeatureCollection"
    assert len(fc["features"]) > 0
    assert fc["features"][0]["properties"]["confidence"] == "Satellite Observation Candidate"


def test_sar_summary_metadata_includes_version_and_geodesic_method(tmp_path):
    """Verify newly generated SAR summaries include pipeline_version and area_calculation_method."""
    w, s, e, n = 85.10, 27.85, 85.25, 28.05
    transform = from_bounds(w, s, e, n, 10, 10)

    pre_file = tmp_path / "pre.tif"
    with rasterio.open(pre_file, "w", driver="GTiff", width=10, height=10, count=1, dtype=np.float32, crs="EPSG:4326", transform=transform) as dst:
        dst.write(np.full((10, 10), 1000.0, dtype=np.float32), 1)

    post_file = tmp_path / "post.tif"
    with rasterio.open(post_file, "w", driver="GTiff", width=10, height=10, count=1, dtype=np.float32, crs="EPSG:4326", transform=transform) as dst:
        dst.write(np.full((10, 10), 1000.0, dtype=np.float32), 1)

    dem_file = tmp_path / "dem.tif"
    with rasterio.open(dem_file, "w", driver="GTiff", width=10, height=10, count=1, dtype=np.float32, crs="EPSG:4326", transform=transform) as dst:
        dst.write(np.full((10, 10), 500.0, dtype=np.float32), 1)

    out_dir = tmp_path / "out"
    result = run_sar_change_detection(pre_file, post_file, dem_file, out_dir, aoi_bbox=[w, s, e, n], width=10, height=10)

    meta = result["summary"]["metadata"]
    assert "pipeline_version" in meta
    assert meta["pipeline_version"] == "0.1.0"
    assert "area_calculation_method" in meta
    assert "WGS84 ellipsoidal geodesic" in meta["area_calculation_method"]


def test_sar_calibration_caveat_documentation():
    """Verify that module and calibration docstrings document the scalar calibration approximation."""
    mod_doc = sar_module.__doc__
    func_doc = sar_module.calibrate_dn_to_sigma0_db.__doc__

    assert "scalar calibration approximation" in mod_doc.lower()
    assert "708.0" in mod_doc
    assert "649.79" in mod_doc
    assert "0.75" in mod_doc
    assert "cancels" in mod_doc.lower()

    assert "scalar approximation" in func_doc.lower()
    assert "708.0" in func_doc
    assert "649.79" in func_doc


def test_manifest_derived_products_registration_and_hashes():
    """Verify that the manifest records all three derived SAR products and valid SHA-256 hashes."""
    manifest = load_manifest()
    derived_ids = [
        "S1_SAR_Flood_Candidates_Raster_10m",
        "S1_SAR_Flood_Candidates_Vector_GeoJSON",
        "S1_SAR_Change_Summary_Report",
    ]

    for did in derived_ids:
        assert did in manifest.products, f"Product {did} missing from data manifest!"
        prod = manifest.products[did]
        assert prod.processing_status == "derived_product"
        assert len(prod.sha256_checksum) == 64, "SHA-256 checksum must be a 64-character hex string"

        # If file is physically present, verify cryptographic hash match
        file_path = Path(prod.local_path)
        if file_path.exists():
            h = hashlib.sha256()
            with open(file_path, "rb") as f:
                while chunk := f.read(1024 * 1024):
                    h.update(chunk)
            assert h.hexdigest() == prod.sha256_checksum, f"Hash mismatch for {did}!"


def test_manifest_schema_derived_product_validation():
    """Verify that AcquiredProductManifestEntry validates derived products without requiring raw satellite fields."""
    entry = AcquiredProductManifestEntry(
        product_id="test_derived_artifact",
        source_catalog="Sentinel-1 Differential Change",
        acquisition_time="2026-08-16 / 2026-08-28",
        original_filename="test.geojson",
        local_path="processed/test.geojson",
        file_size_bytes=1024,
        file_size_mb=0.001,
        sha256_checksum="a" * 64,
        download_timestamp="2026-10-15T06:00:00+00:00",
        processing_status="derived_product",
        validation=None,
        known_limitations=["Synthetic test artifact"],
    )
    assert entry.product_id == "test_derived_artifact"
    assert entry.processing_status == "derived_product"


def test_sar_candidates_from_deployment_data_directory(client):
    """Verify that the backend endpoint successfully discovers the three artifacts from repository data/ directory."""
    repo_data_dir = (PROJECT_ROOT / "data").resolve()
    assert (repo_data_dir / "processed" / "sentinel1" / "s1_sar_flood_candidates_10m.tif").exists()
    assert (repo_data_dir / "processed" / "sentinel1" / "s1_sar_flood_candidates.geojson").exists()
    assert (repo_data_dir / "processed" / "sentinel1" / "s1_sar_change_summary.json").exists()

    with patch.object(AppSettings, "data_dir", new_callable=PropertyMock, return_value=repo_data_dir):
        response = client.get("/api/analysis/sar-flood-candidates")
        assert response.status_code == 200
        data = response.json()
        assert data.get("available") is True
        assert "summary" in data
        assert "geojson" in data
        assert data["summary"]["results"]["candidate_flood_pixel_count"] == 5735
        assert data["summary"]["results"]["candidate_flood_area_km2"] == 0.625
        assert len(data["geojson"]["features"]) == 295


def test_sar_candidates_fallback_to_repo_when_configured_path_missing(client):
    """Verify that when configured data directory does not exist (e.g. Render without D: drive), backend falls back to repository data/ directory."""
    with patch.object(settings, "data_dir_str", "/nonexistent/cloud/path/data"):
        assert settings.data_dir == (PROJECT_ROOT / "data").resolve()
        response = client.get("/api/analysis/sar-flood-candidates")
        assert response.status_code == 200
        data = response.json()
        assert data.get("available") is True
        assert data["summary"]["results"]["candidate_flood_pixel_count"] == 5735


def test_repo_manifest_contains_deployment_sar_products():
    """Verify that data/manifest.json records the three derived SAR products with valid hashes and sizes."""
    repo_manifest_file = (PROJECT_ROOT / "data" / "manifest.json").resolve()
    assert repo_manifest_file.exists()
    with open(repo_manifest_file, "r", encoding="utf-8") as f:
        mf = json.load(f)

    assert mf["data_directory"] == "data"
    for did in [
        "S1_SAR_Flood_Candidates_Raster_10m",
        "S1_SAR_Flood_Candidates_Vector_GeoJSON",
        "S1_SAR_Change_Summary_Report",
    ]:
        assert did in mf["products"]
        prod = mf["products"][did]
        assert prod["processing_status"] == "derived_product"
        rel_p = Path(prod["local_path"])
        assert (PROJECT_ROOT / rel_p).exists()



