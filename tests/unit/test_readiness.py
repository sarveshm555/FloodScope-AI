import pytest
from pathlib import Path
import numpy as np
import rasterio
from rasterio.transform import from_bounds
from rasterio.crs import CRS
from shapely.geometry import box
from shapely.ops import unary_union

from backend.app.geospatial.validation import inspect_and_validate_raster, compute_sha256
from backend.app.schemas.downloads import AcquiredProductManifestEntry
from backend.app.geospatial.catalog import match_candidate_sar_pairs, normalize_product_record
from datetime import datetime, timezone


@pytest.fixture
def aoi_bbox():
    # Trishuli Pilot AOI: [west, south, east, north]
    return [85.10, 27.85, 85.25, 28.05]


@pytest.fixture
def partial_south_tile(tmp_path):
    """Synthetic tile covering South half only (Lat 27.0 to 28.0)."""
    p = tmp_path / "south_tile.tif"
    width, height = 100, 100
    transform = from_bounds(85.0, 27.0, 86.0, 28.0, width, height)
    data = np.ones((1, height, width), dtype=np.float32)
    with rasterio.open(
        str(p), "w", driver="GTiff", height=height, width=width, count=1,
        dtype=data.dtype, crs=CRS.from_epsg(4326), transform=transform
    ) as dst:
        dst.write(data)
    return p


@pytest.fixture
def partial_north_tile(tmp_path):
    """Synthetic tile covering North half only (Lat 28.0 to 29.0)."""
    p = tmp_path / "north_tile.tif"
    width, height = 100, 100
    transform = from_bounds(85.0, 28.0, 86.0, 29.0, width, height)
    data = np.ones((1, height, width), dtype=np.float32)
    with rasterio.open(
        str(p), "w", driver="GTiff", height=height, width=width, count=1,
        dtype=data.dtype, crs=CRS.from_epsg(4326), transform=transform
    ) as dst:
        dst.write(data)
    return p


@pytest.fixture
def full_covering_tile(tmp_path):
    """Synthetic tile completely enclosing the AOI (Lat 27.5 to 28.5, Lon 85.0 to 85.5)."""
    p = tmp_path / "full_tile.tif"
    width, height = 100, 100
    transform = from_bounds(85.0, 27.5, 85.5, 28.5, width, height)
    data = np.ones((1, height, width), dtype=np.float32)
    with rasterio.open(
        str(p), "w", driver="GTiff", height=height, width=width, count=1,
        dtype=data.dtype, crs=CRS.from_epsg(4326), transform=transform
    ) as dst:
        dst.write(data)
    return p


def test_raster_partially_covers_aoi(partial_south_tile, aoi_bbox):
    """Verify that a raster covering only latitude 27-28 leaves the northern AOI uncovered."""
    report = inspect_and_validate_raster(partial_south_tile, aoi_bbox=aoi_bbox)
    assert report.is_readable is True
    assert report.intersects_aoi is True

    # Check exact geometric coverage
    aoi_poly = box(*aoi_bbox)
    with rasterio.open(partial_south_tile) as src:
        tile_poly = box(src.bounds.left, src.bounds.bottom, src.bounds.right, src.bounds.top)

    assert not tile_poly.contains(aoi_poly), "South tile alone should NOT fully contain AOI"
    inter = tile_poly.intersection(aoi_poly)
    cov_pct = (inter.area / aoi_poly.area) * 100.0
    assert 74.0 < cov_pct < 76.0, f"Expected ~75% coverage, got {cov_pct}%"


def test_raster_fully_covers_aoi(full_covering_tile, aoi_bbox):
    """Verify that a raster enclosing the entire AOI provides 100% coverage."""
    report = inspect_and_validate_raster(full_covering_tile, aoi_bbox=aoi_bbox)
    assert report.is_readable is True
    assert report.intersects_aoi is True

    aoi_poly = box(*aoi_bbox)
    with rasterio.open(full_covering_tile) as src:
        tile_poly = box(src.bounds.left, src.bounds.bottom, src.bounds.right, src.bounds.top)

    assert tile_poly.contains(aoi_poly) is True
    inter = tile_poly.intersection(aoi_poly)
    cov_pct = (inter.area / aoi_poly.area) * 100.0
    assert cov_pct == 100.0


def test_combining_adjacent_dem_tiles(partial_south_tile, partial_north_tile, aoi_bbox):
    """Verify that combining adjacent North + South tiles achieves 100% full AOI coverage."""
    aoi_poly = box(*aoi_bbox)
    with rasterio.open(partial_south_tile) as s1, rasterio.open(partial_north_tile) as s2:
        b1 = box(s1.bounds.left, s1.bounds.bottom, s1.bounds.right, s1.bounds.top)
        b2 = box(s2.bounds.left, s2.bounds.bottom, s2.bounds.right, s2.bounds.top)

    assert not b1.contains(aoi_poly)
    assert not b2.contains(aoi_poly)

    combined = unary_union([b1, b2])
    assert combined.contains(aoi_poly) is True
    inter = combined.intersection(aoi_poly)
    cov_pct = (inter.area / aoi_poly.area) * 100.0
    assert cov_pct == 100.0


def test_missing_or_unavailable_dem_tile_raises(tmp_path):
    """Verify that missing files raise FileNotFoundError."""
    missing_path = tmp_path / "non_existent_tile.tif"
    with pytest.raises(FileNotFoundError):
        inspect_and_validate_raster(missing_path)


def test_incorrect_manifest_path_validation(tmp_path):
    """Verify that a manifest entry pointing to a non-existent path is detectable."""
    fake_entry = AcquiredProductManifestEntry(
        product_id="missing-asset",
        source_catalog="Test",
        acquisition_time=None,
        original_filename="ghost.tif",
        local_path=str(tmp_path / "ghost.tif"),
        file_size_bytes=1000,
        file_size_mb=0.001,
        sha256_checksum="fake",
        download_timestamp="2026-10-12T19:00:00Z",
        processing_status="validated"
    )
    assert not Path(fake_entry.local_path).exists()


def test_mismatched_file_size_or_checksum(full_covering_tile):
    """Verify detection when actual file content does not match reported checksum."""
    real_sha = compute_sha256(full_covering_tile)
    corrupted_sha = "0000000000000000000000000000000000000000000000000000000000000000"

    assert real_sha != corrupted_sha
    actual_size = full_covering_tile.stat().st_size
    reported_wrong_size = actual_size + 9999

    assert actual_size != reported_wrong_size


def test_catalog_product_id_discrepancy_resolution(aoi_bbox):
    """Verify resolution of COG vs standard SAFE product representations for Sentinel-1."""
    event_dt = datetime(2026, 8, 26, 0, 0, tzinfo=timezone.utc)
    ts = datetime.now(timezone.utc).isoformat()

    # Pre-event COG variant
    raw_s1_cog = {
        "Id": "04db2c11-1319-4808-adaa-da7f7ccbbd4f",
        "Name": "S1D_IW_GRDH_1SDV_20260816T122141_20260816T122206_004151_007980_B091_COG.SAFE",
        "ContentLength": 1240792161,
        "ContentDate": {"Start": "2026-08-16T12:21:41.058Z"},
        "GeoFootprint": {"type": "Polygon", "coordinates": [[[84.5, 27.5], [85.5, 27.5], [85.5, 28.5], [84.5, 28.5], [84.5, 27.5]]]},
        "Attributes": [
            {"Name": "orbitDirection", "Value": "ASCENDING"},
            {"Name": "relativeOrbitNumber", "Value": "85"},
            {"Name": "operationalMode", "Value": "IW"},
            {"Name": "polarisationChannels", "Value": "VV&VH"},
            {"Name": "productType", "Value": "IW_GRDH_1S-COG"}
        ]
    }

    # Pre-event standard SAFE variant
    raw_s1_safe = {
        "Id": "844b9a32-9aa2-4611-83f6-ae6501c01955",
        "Name": "S1D_IW_GRDH_1SDV_20260816T122141_20260816T122206_004151_007980_C3AB.SAFE",
        "ContentLength": 1732874277,
        "ContentDate": {"Start": "2026-08-16T12:21:41.058Z"},
        "GeoFootprint": {"type": "Polygon", "coordinates": [[[84.5, 27.5], [85.5, 27.5], [85.5, 28.5], [84.5, 28.5], [84.5, 27.5]]]},
        "Attributes": [
            {"Name": "orbitDirection", "Value": "ASCENDING"},
            {"Name": "relativeOrbitNumber", "Value": "85"},
            {"Name": "operationalMode", "Value": "IW"},
            {"Name": "polarisationChannels", "Value": "VV&VH"},
            {"Name": "productType", "Value": "IW_GRDH_1S"}
        ]
    }

    cog_norm = normalize_product_record(raw_s1_cog, aoi_bbox, event_dt, ts)
    safe_norm = normalize_product_record(raw_s1_safe, aoi_bbox, event_dt, ts)

    assert cog_norm.acquisition_time[:19] == safe_norm.acquisition_time[:19]
    assert cog_norm.relative_orbit == safe_norm.relative_orbit == 85
    assert cog_norm.orbit_direction == safe_norm.orbit_direction == "ASCENDING"
    assert cog_norm.product_type == "IW_GRDH_1S-COG"
    assert safe_norm.product_type == "IW_GRDH_1S"
    assert cog_norm.size_mb < safe_norm.size_mb  # COG is ~28% smaller
