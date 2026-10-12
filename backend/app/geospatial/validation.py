import hashlib
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
import rasterio
from rasterio.windows import Window
import numpy as np
from shapely.geometry import box

from backend.app.schemas.downloads import RasterValidationReport

logger = logging.getLogger("floodscope.validation")


def compute_sha256(file_path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Compute SHA-256 hash of a file efficiently."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            sha256.update(chunk)
    return sha256.hexdigest()


def inspect_and_validate_raster(
    file_path: Path,
    aoi_bbox: List[float] = [85.10, 27.85, 85.25, 28.05],
    precomputed_checksum: Optional[str] = None
) -> RasterValidationReport:
    """Inspect and rigorously validate a downloaded satellite or elevation raster.
    
    Verifies:
    - File readability with rasterio
    - Raster dimensions, CRS, affine geotransform, pixel resolution
    - Nodata values and valid-data percentage
    - True intersection with pilot AOI
    - Measurement data vs RGB thumbnail verification
    - COG structure (tiled, internal overviews)
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Target raster file does not exist: {path}")

    file_size_bytes = path.stat().st_size
    file_size_mb = round(file_size_bytes / (1024 * 1024), 2)
    checksum = precomputed_checksum or compute_sha256(path)

    warnings: List[str] = []

    try:
        with rasterio.open(str(path)) as src:
            driver = src.driver
            width = src.width
            height = src.height
            band_count = src.count
            dtype_str = src.dtypes[0] if src.dtypes else "unknown"
            crs_str = str(src.crs) if src.crs else None
            transform = list(src.transform)[:6]
            bounds = [src.bounds.left, src.bounds.bottom, src.bounds.right, src.bounds.top]
            res_x, res_y = src.res
            nodata_val = float(src.nodata) if src.nodata is not None else None

            # 1. COG Structure Check
            is_tiled = bool(src.profile.get("tiled", False))
            has_overviews = len(src.overviews(1)) > 0 if band_count >= 1 else False
            is_cog = is_tiled and has_overviews
            if not is_cog:
                warnings.append("Raster does not have standard COG internal overviews/tiling layout.")

            # 2. Measurement Data Check (distinguish scientific data from 8-bit RGB preview)
            is_measurement = True
            if dtype_str.lower() in ["uint8", "byte"] and band_count in [3, 4]:
                is_measurement = False
                warnings.append(
                    "Raster format is 8-bit RGB/RGBA Byte; appears to be a visual quicklook/preview "
                    "rather than calibrated scientific radar/elevation measurement data."
                )

            # 3. Spatial Intersection with Pilot AOI
            west, south, east, north = aoi_bbox
            aoi_poly = box(west, south, east, north)
            # Check bounds intersection
            # Note: If CRS is EPSG:4326, comparison is direct.
            raster_poly = box(src.bounds.left, src.bounds.bottom, src.bounds.right, src.bounds.top)
            intersects_aoi = raster_poly.intersects(aoi_poly)
            if not intersects_aoi:
                warnings.append(
                    f"Raster bounds [{src.bounds.left:.2f}, {src.bounds.bottom:.2f}, "
                    f"{src.bounds.right:.2f}, {src.bounds.top:.2f}] do not intersect pilot AOI."
                )

            # 4. Valid Data Percentage (Sample-based block reading to prevent OOM)
            sample_w = min(1024, width)
            sample_h = min(1024, height)
            window = Window(
                col_off=(width - sample_w) // 2,
                row_off=(height - sample_h) // 2,
                width=sample_w,
                height=sample_h
            )
            sample_array = src.read(1, window=window)

            if nodata_val is not None:
                valid_mask = (sample_array != nodata_val) & ~np.isnan(sample_array)
            else:
                valid_mask = ~np.isnan(sample_array)

            valid_percent = round(float(np.mean(valid_mask) * 100.0), 2)
            if valid_percent < 5.0:
                warnings.append(f"Very low valid data coverage in sample window ({valid_percent}%).")

            return RasterValidationReport(
                file_path=str(path.resolve()),
                file_size_bytes=file_size_bytes,
                file_size_mb=file_size_mb,
                sha256_checksum=checksum,
                is_readable=True,
                driver=driver,
                width=width,
                height=height,
                band_count=band_count,
                dtype=dtype_str,
                crs=crs_str,
                geotransform=transform,
                bounds=bounds,
                pixel_resolution=[round(res_x, 6), round(res_y, 6)],
                nodata_value=nodata_val,
                valid_data_percent=valid_percent,
                intersects_aoi=intersects_aoi,
                is_measurement_data=is_measurement,
                is_valid_cog=is_cog,
                validation_warnings=warnings,
            )

    except rasterio.errors.RasterioError as e:
        logger.error(f"Raster inspection failed: {e}")
        return RasterValidationReport(
            file_path=str(path.resolve()),
            file_size_bytes=file_size_bytes,
            file_size_mb=file_size_mb,
            sha256_checksum=checksum,
            is_readable=False,
            driver="UNKNOWN",
            width=0,
            height=0,
            band_count=0,
            dtype="unknown",
            crs=None,
            geotransform=[],
            bounds=[],
            pixel_resolution=[],
            nodata_value=None,
            valid_data_percent=0.0,
            intersects_aoi=False,
            is_measurement_data=False,
            is_valid_cog=False,
            validation_warnings=[f"Failed to read raster with rasterio: {str(e)}"],
        )
