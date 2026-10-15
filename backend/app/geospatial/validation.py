import json
import zipfile
import hashlib
import struct
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
import rasterio
from rasterio.windows import Window
import numpy as np
from shapely.geometry import box, shape

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

            # 1. COG Structure & Layout Check
            is_tiled = bool(src.profile.get("tiled", False))
            has_overviews = len(src.overviews(1)) > 0 if band_count >= 1 else False

            # Strict Cloud Optimized GeoTIFF (COG) specification requires linearized IFDs in file header (< 32 KB)
            is_header_ifd = False
            first_ifd_offset = -1
            try:
                with open(path, "rb") as tf:
                    hdr = tf.read(4)
                    order = "<" if hdr[:2] == b"II" else ">"
                    if hdr in (b"II\x2b\x00", b"MM\x00\x2b"):  # BigTIFF
                        tf.seek(8)
                        first_ifd_offset = struct.unpack(order + "Q", tf.read(8))[0]
                    elif hdr in (b"II\x2a\x00", b"MM\x00\x2a"):  # Classic TIFF
                        first_ifd_offset = struct.unpack(order + "I", tf.read(4))[0]
                    is_header_ifd = (0 < first_ifd_offset < 32768)
            except Exception:
                is_header_ifd = False

            is_cog = is_tiled and has_overviews and is_header_ifd
            if not is_tiled or not has_overviews:
                warnings.append("Raster does not have standard COG internal overviews/tiling layout.")
            elif not is_header_ifd:
                warnings.append(
                    f"Raster has internal tiling and overviews, but IFD directory is located at the tail of the file (offset {first_ifd_offset}); "
                    "lacks linearized ghost IFD header required for strict COG HTTP range streaming."
                )

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
            raster_poly = box(src.bounds.left, src.bounds.bottom, src.bounds.right, src.bounds.top)
            intersects_aoi = raster_poly.intersects(aoi_poly)
            if not intersects_aoi:
                warnings.append(
                    f"Raster bounds [{src.bounds.left:.2f}, {src.bounds.bottom:.2f}, "
                    f"{src.bounds.right:.2f}, {src.bounds.top:.2f}] do not intersect pilot AOI."
                )

            # 4. Valid Data Percentage (Block-wise streaming evaluates 100% of cells without OOM risk)
            total_valid_cells = 0
            total_cells = width * height
            for _, win in src.block_windows(1):
                block = src.read(1, window=win)
                if nodata_val is not None:
                    if np.isnan(nodata_val):
                        valid_mask = ~np.isnan(block)
                    else:
                        valid_mask = (block != nodata_val) & ~np.isnan(block)
                else:
                    valid_mask = ~np.isnan(block)
                total_valid_cells += int(np.sum(valid_mask))

            valid_percent = round(float((total_valid_cells / total_cells) * 100.0), 2)
            if valid_percent < 5.0:
                warnings.append(f"Very low valid data coverage ({valid_percent}%).")

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


def inspect_and_validate_geojson(
    file_path: Path,
    aoi_bbox: List[float] = [85.10, 27.85, 85.25, 28.05],
    precomputed_checksum: Optional[str] = None
) -> Dict[str, Any]:
    """Inspect and rigorously validate a GeoJSON feature collection file."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Target GeoJSON file does not exist: {path}")

    file_size_bytes = path.stat().st_size
    file_size_mb = round(file_size_bytes / (1024 * 1024), 2)
    checksum = precomputed_checksum or compute_sha256(path)

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if data.get("type") != "FeatureCollection":
        raise ValueError(f"GeoJSON root must be FeatureCollection, found: {data.get('type')}")

    features = data.get("features", [])
    valid_count = 0
    min_x, min_y, max_x, max_y = float("inf"), float("inf"), float("-inf"), float("-inf")
    for feat in features:
        geom = feat.get("geometry")
        if geom:
            geom_shape = shape(geom)
            if geom_shape.is_valid:
                valid_count += 1
            bounds = geom_shape.bounds
            min_x = min(min_x, bounds[0])
            min_y = min(min_y, bounds[1])
            max_x = max(max_x, bounds[2])
            max_y = max(max_y, bounds[3])

    feature_bounds = [round(min_x, 4), round(min_y, 4), round(max_x, 4), round(max_y, 4)] if features else []
    west, south, east, north = aoi_bbox
    aoi_poly = box(west, south, east, north)
    geom_poly = box(min_x, min_y, max_x, max_y) if features else None
    intersects_aoi = geom_poly.intersects(aoi_poly) if geom_poly else False

    return {
        "file_path": str(path.resolve()),
        "file_size_bytes": file_size_bytes,
        "file_size_mb": file_size_mb,
        "sha256_checksum": checksum,
        "is_readable": True,
        "format": "GeoJSON FeatureCollection",
        "feature_count": len(features),
        "valid_geometry_count": valid_count,
        "crs": "EPSG:4326",
        "bounds": feature_bounds,
        "intersects_aoi": intersects_aoi,
        "all_geometries_valid": valid_count == len(features),
    }


def inspect_and_validate_json_summary(
    file_path: Path,
    precomputed_checksum: Optional[str] = None
) -> Dict[str, Any]:
    """Inspect and validate a structured JSON change-detection analysis summary."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Target JSON summary file does not exist: {path}")

    file_size_bytes = path.stat().st_size
    file_size_mb = round(file_size_bytes / (1024 * 1024), 4)
    checksum = precomputed_checksum or compute_sha256(path)

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    keys = list(data.keys())
    has_meta = "metadata" in data
    has_results = "results" in data

    return {
        "file_path": str(path.resolve()),
        "file_size_bytes": file_size_bytes,
        "file_size_mb": file_size_mb,
        "sha256_checksum": checksum,
        "is_readable": True,
        "format": "JSON analysis summary",
        "root_keys": keys,
        "has_metadata": has_meta,
        "has_results": has_results,
        "pipeline_version": data.get("metadata", {}).get("pipeline_version"),
        "area_calculation_method": data.get("metadata", {}).get("area_calculation_method"),
        "candidate_flood_area_km2": data.get("results", {}).get("candidate_flood_area_km2"),
        "candidate_flood_pixels": data.get("results", {}).get("candidate_flood_pixels"),
    }


def inspect_and_validate_sentinel1_archive(
    file_path: Path,
    precomputed_checksum: Optional[str] = None
) -> Dict[str, Any]:
    """Inspect and validate a Sentinel-1 packaged product archive (.zip)."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Target Sentinel-1 archive file does not exist: {path}")

    file_size_bytes = path.stat().st_size
    file_size_mb = round(file_size_bytes / (1024 * 1024), 2)
    checksum = precomputed_checksum or compute_sha256(path)

    if not zipfile.is_zipfile(path):
        raise ValueError(f"File is not a valid ZIP archive: {path}")

    with zipfile.ZipFile(path, "r") as z:
        namelist = z.namelist()
        total_files = len(namelist)
        measurement_files = [f for f in namelist if "measurement" in f and f.lower().endswith((".tif", ".tiff"))]
        has_safe_manifest = any("manifest.safe" in f.lower() for f in namelist)
        has_calibration = any("calibration" in f.lower() for f in namelist)
        root_dir = namelist[0].split("/")[0] if namelist else ""

    return {
        "file_path": str(path.resolve()),
        "file_size_bytes": file_size_bytes,
        "file_size_mb": file_size_mb,
        "sha256_checksum": checksum,
        "is_readable": True,
        "format": "Sentinel-1 archive or packaged product",
        "archive_type": "SAFE ZIP",
        "root_directory": root_dir,
        "total_files": total_files,
        "measurement_files": measurement_files,
        "has_safe_manifest": has_safe_manifest,
        "has_calibration": has_calibration,
        "is_verified_s1_package": has_safe_manifest and len(measurement_files) >= 2,
    }
