import pytest
from pathlib import Path
import numpy as np
import rasterio
from rasterio.transform import from_bounds
from rasterio.crs import CRS

from backend.app.geospatial.validation import inspect_and_validate_raster


@pytest.fixture
def synthetic_measurement_geotiff(tmp_path) -> Path:
    """Create a synthetic 1-band float32 scientific measurement GeoTIFF intersecting Trishuli AOI."""
    file_path = tmp_path / "synthetic_measurement.tif"
    width, height = 100, 100
    # Geographic bounds: [85.0, 27.8, 85.3, 28.1] -> intersects Trishuli [85.10, 27.85, 85.25, 28.05]
    transform = from_bounds(85.0, 27.8, 85.3, 28.1, width, height)
    crs = CRS.from_epsg(4326)

    data = np.random.uniform(low=-25.0, high=0.0, size=(1, height, width)).astype(np.float32)
    # Set nodata value
    data[0, :10, :10] = -9999.0

    with rasterio.open(
        str(file_path),
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=1,
        dtype=data.dtype,
        crs=crs,
        transform=transform,
        nodata=-9999.0,
    ) as dst:
        dst.write(data)

    return file_path


@pytest.fixture
def synthetic_outside_geotiff(tmp_path) -> Path:
    """Create a synthetic GeoTIFF outside the pilot AOI (Germany)."""
    file_path = tmp_path / "synthetic_outside.tif"
    width, height = 50, 50
    transform = from_bounds(10.0, 50.0, 11.0, 51.0, width, height)
    crs = CRS.from_epsg(4326)
    data = np.ones((1, height, width), dtype=np.float32)

    with rasterio.open(
        str(file_path),
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=1,
        dtype=data.dtype,
        crs=crs,
        transform=transform,
    ) as dst:
        dst.write(data)

    return file_path


@pytest.fixture
def synthetic_rgb_preview_geotiff(tmp_path) -> Path:
    """Create a synthetic 3-band 8-bit RGB preview image."""
    file_path = tmp_path / "synthetic_preview.tif"
    width, height = 64, 64
    transform = from_bounds(85.0, 27.8, 85.3, 28.1, width, height)
    crs = CRS.from_epsg(4326)
    data = np.random.randint(0, 255, size=(3, height, width), dtype=np.uint8)

    with rasterio.open(
        str(file_path),
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=3,
        dtype=data.dtype,
        crs=crs,
        transform=transform,
    ) as dst:
        dst.write(data)

    return file_path


def test_validate_measurement_raster(synthetic_measurement_geotiff):
    """Verify that a valid float32 measurement raster passes all checks."""
    report = inspect_and_validate_raster(
        synthetic_measurement_geotiff,
        aoi_bbox=[85.10, 27.85, 85.25, 28.05]
    )
    assert report.is_readable is True
    assert report.driver == "GTiff"
    assert report.width == 100
    assert report.height == 100
    assert report.band_count == 1
    assert report.dtype == "float32"
    assert "4326" in report.crs
    assert report.nodata_value == -9999.0
    assert report.intersects_aoi is True
    assert report.is_measurement_data is True
    assert report.valid_data_percent > 80.0
    assert len(report.sha256_checksum) == 64


def test_validate_non_intersecting_raster(synthetic_outside_geotiff):
    """Verify that a raster located outside the AOI is flagged."""
    report = inspect_and_validate_raster(
        synthetic_outside_geotiff,
        aoi_bbox=[85.10, 27.85, 85.25, 28.05]
    )
    assert report.is_readable is True
    assert report.intersects_aoi is False
    assert any("do not intersect pilot AOI" in w for w in report.validation_warnings)


def test_validate_rgb_preview_flagged(synthetic_rgb_preview_geotiff):
    """Verify that an 8-bit RGB preview image is flagged as non-measurement data."""
    report = inspect_and_validate_raster(
        synthetic_rgb_preview_geotiff,
        aoi_bbox=[85.10, 27.85, 85.25, 28.05]
    )
    assert report.is_readable is True
    assert report.band_count == 3
    assert report.is_measurement_data is False
    assert any("visual quicklook/preview" in w for w in report.validation_warnings)


def test_nonexistent_raster_raises_file_not_found(tmp_path):
    """Verify that inspect_and_validate_raster raises FileNotFoundError for missing paths."""
    with pytest.raises(FileNotFoundError):
        inspect_and_validate_raster(tmp_path / "does_not_exist.tif")
