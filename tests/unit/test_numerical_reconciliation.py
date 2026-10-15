import json
import struct
import numpy as np
import pytest
from pathlib import Path
import rasterio
from rasterio.features import shapes
from shapely.geometry import shape
from shapely.ops import unary_union

from backend.app.geospatial.validation import inspect_and_validate_raster
from backend.app.geospatial.sar import compute_wgs84_cell_metrics


@pytest.fixture
def sar_paths():
    data_dir = Path("D:/FloodScope-Data")
    raster_path = data_dir / "processed" / "sentinel1" / "s1_sar_flood_candidates_10m.tif"
    summary_path = data_dir / "processed" / "sentinel1" / "s1_sar_change_summary.json"
    geojson_path = data_dir / "processed" / "sentinel1" / "s1_sar_flood_candidates.geojson"
    dem_mosaic_path = data_dir / "processed" / "dem_mosaic_pilot_aoi.tif"
    dem_n27_path = data_dir / "raw" / "Copernicus_DSM_COG_10_N27_00_E085_00_DEM.tif"
    return {
        "raster": raster_path,
        "summary": summary_path,
        "geojson": geojson_path,
        "mosaic": dem_mosaic_path,
        "n27": dem_n27_path,
    }


def test_raster_class_counts_and_nodata(sar_paths):
    """Verify raster dimensions, NoData setting, and exact pixel counts across all classes."""
    raster_path = sar_paths["raster"]
    if not raster_path.exists():
        pytest.skip("SAR candidate raster artifact not present on disk")

    with rasterio.open(raster_path) as src:
        assert src.width == 1500
        assert src.height == 2000
        assert src.nodata == 0.0
        data = src.read(1)

    unique, counts = np.unique(data, return_counts=True)
    hist = dict(zip(unique.tolist(), counts.tolist()))

    assert hist[0] == 2969971, "Class 0 (Background) count must be exactly 2,969,971"
    assert hist[1] == 24294, "Class 1 (Permanent Water) count must be exactly 24,294"
    assert hist[2] == 5735, "Class 2 (Candidate Inundation) count must be exactly 5,735"
    assert sum(counts) == 3000000, "Sum of all classes must exactly equal 3,000,000 cells"


def test_summary_pixel_count_and_candidate_area_reconciliation(sar_paths):
    """Verify summary pixel count agrees with raster Class 2 and reconcile area calculations."""
    summary_path = sar_paths["summary"]
    raster_path = sar_paths["raster"]
    if not summary_path.exists() or not raster_path.exists():
        pytest.skip("SAR artifacts not present on disk")

    with open(summary_path, "r", encoding="utf-8") as f:
        summary = json.load(f)

    with rasterio.open(raster_path) as src:
        data = src.read(1)
        bounds = src.bounds
        width, height = src.width, src.height

    raster_class2_pixels = int(np.sum(data == 2))
    summary_pixel_count = summary["results"]["candidate_flood_pixel_count"]
    summary_area_km2 = summary["results"]["candidate_flood_area_km2"]

    # 1. Exact pixel count agreement
    assert raster_class2_pixels == 5735
    assert summary_pixel_count == 5735, "Summary pixel count must agree with raster Class 2 pixels"

    # 2. Reconcile spherical vs ellipsoidal area calculations
    # Spherical Earth projection (R = 6371 km, 111320 m/deg):
    lat_center = (bounds.bottom + bounds.top) / 2.0
    dx_spherical = (bounds.right - bounds.left) / width * 111320.0 * np.cos(np.radians(lat_center))
    dy_spherical = (bounds.top - bounds.bottom) / height * 111320.0
    cell_area_spherical_m2 = dx_spherical * dy_spherical
    area_spherical_km2 = round((raster_class2_pixels * cell_area_spherical_m2) / 1e6, 3)

    assert cell_area_spherical_m2 == pytest.approx(109.467, abs=1e-2)
    assert area_spherical_km2 == 0.628
    assert summary_area_km2 == area_spherical_km2, "Summary 0.628 km^2 is derived from spherical cell projection"

    # WGS84 Ellipsoidal geodesic integration:
    dx_wgs84, dy_wgs84, cell_area_wgs84_m2 = compute_wgs84_cell_metrics(
        bounds.left, bounds.bottom, bounds.right, bounds.top, width, height
    )
    area_wgs84_km2 = round((raster_class2_pixels * cell_area_wgs84_m2) / 1e6, 3)
    assert cell_area_wgs84_m2 == pytest.approx(109.0536, abs=1e-3)
    assert area_wgs84_km2 == 0.625

    # Difference between spherical and ellipsoidal projection is ~0.38% (0.0024 km^2)
    diff_km2 = abs(area_spherical_km2 - area_wgs84_km2)
    assert diff_km2 <= 0.005


def test_valid_data_percentage_and_nodata_handling(sar_paths):
    """Verify block-streaming full-raster valid data coverage calculation and explain center sampling bias."""
    raster_path = sar_paths["raster"]
    if not raster_path.exists():
        pytest.skip("Raster not present on disk")

    report = inspect_and_validate_raster(raster_path)
    # Full raster has 30,029 non-zero cells out of 3,000,000 -> 1.00097%
    assert report.valid_data_percent == 1.0, f"Expected 1.0% valid data, got {report.valid_data_percent}%"

    with rasterio.open(raster_path) as src:
        total_cells = src.width * src.height
        data = src.read(1)
        valid_count = int(np.sum(data != src.nodata))

    expected_pct = round((valid_count / total_cells) * 100.0, 2)
    assert expected_pct == 1.0
    assert valid_count == 30029


def test_raster_to_geojson_component_filtering_and_area(sar_paths):
    """Verify component extraction, 50 m^2 filtering, and reconcile GeoJSON area difference."""
    raster_path = sar_paths["raster"]
    geojson_path = sar_paths["geojson"]
    if not raster_path.exists() or not geojson_path.exists():
        pytest.skip("Artifacts not present on disk")

    with rasterio.open(raster_path) as src:
        data = src.read(1)
        transform = src.transform

    # The original script generate_sar_outputs.py used `if poly.area > 0.00000005` (5e-8 deg^2 = 5 pixels)
    min_area_deg = 5e-8

    mask = (data == 2)
    extracted = list(shapes(np.uint8(mask), mask=mask, transform=transform))
    assert len(extracted) == 498, "Expected 498 connected components from rasterio.shapes"

    retained = [shape(g) for g, v in extracted if v == 1 and shape(g).area > min_area_deg]
    discarded = [shape(g) for g, v in extracted if v == 1 and shape(g).area <= min_area_deg]

    assert len(retained) == 295, "Expected exactly 295 retained components exceeding 50 m^2 (> 5 pixels)"
    assert len(discarded) == 203, "Expected exactly 203 discarded noise components <= 50 m^2 (<= 5 pixels)"

    # Area accounting (in spherical projection matching original generation)
    deg_to_m2 = 111320.0 * 111320.0 * np.cos(np.radians(27.95))
    retained_km2 = sum(p.area for p in retained) * deg_to_m2 / 1e6
    discarded_km2 = sum(p.area for p in discarded) * deg_to_m2 / 1e6
    total_km2 = (retained_km2 + discarded_km2)

    assert retained_km2 == pytest.approx(0.5389, abs=1e-3)
    assert discarded_km2 == pytest.approx(0.0889, abs=1e-3)
    assert total_km2 == pytest.approx(0.6278, abs=1e-3)

    # Reconcile GeoJSON area property rounding
    with open(geojson_path, "r", encoding="utf-8") as f:
        gj = json.load(f)

    assert len(gj["features"]) == 295
    sum_rounded_properties = sum(float(f["properties"]["area_km2"]) for f in gj["features"])
    assert sum_rounded_properties == pytest.approx(0.5434, abs=1e-3)

    # Rounding delta
    rounding_delta = sum_rounded_properties - retained_km2
    assert rounding_delta == pytest.approx(0.0045, abs=1e-3)


def test_cog_conformance_and_ifd_linearization(sar_paths):
    """Verify COG IFD header linearization check distinguishing strict COGs from tail-IFD GeoTIFFs."""
    n27_path = sar_paths["n27"]
    mosaic_path = sar_paths["mosaic"]
    raster_path = sar_paths["raster"]

    if n27_path.exists():
        rep_n27 = inspect_and_validate_raster(n27_path)
        assert rep_n27.is_valid_cog is True, "Copernicus DSM tile must pass strict COG validation"

    if mosaic_path.exists():
        rep_mosaic = inspect_and_validate_raster(mosaic_path)
        assert rep_mosaic.is_valid_cog is False, "Mosaic has tail IFD; must not be claimed as strict COG"
        assert any("tail of the file" in w for w in rep_mosaic.validation_warnings)

    if raster_path.exists():
        rep_raster = inspect_and_validate_raster(raster_path)
        assert rep_raster.is_valid_cog is False, "SAR candidate raster is standard stripped GeoTIFF"
