import shutil
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from backend.app.core.config import settings
from backend.app.schemas.downloads import (
    DataManifest,
    RasterValidationReport,
    DownloadRequest,
    AcquiredProductManifestEntry,
)
from backend.app.geospatial.downloads import (
    SafeDownloadManager,
    CDSEAuthClient,
    InsufficientStorageError,
    AuthCredentialsMissingError,
)
from backend.app.geospatial.validation import inspect_and_validate_raster
from backend.app.geospatial.manifest import load_manifest, register_acquired_product

router = APIRouter()


@router.get("/manifest", response_model=DataManifest)
def get_data_manifest() -> DataManifest:
    """Retrieve machine-readable inventory of acquired and validated satellite products."""
    return load_manifest()


@router.get("/storage-status")
def get_storage_status():
    """Report storage usage and free capacity on configured data volume."""
    target_dir = settings.data_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    usage = shutil.disk_usage(str(target_dir))
    return {
        "data_directory": str(target_dir),
        "total_gb": round(usage.total / (1024 ** 3), 2),
        "used_gb": round(usage.used / (1024 ** 3), 2),
        "free_gb": round(usage.free / (1024 ** 3), 2),
        "free_mb": round(usage.free / (1024 ** 2), 2),
        "storage_safe_for_downloads": usage.free > (5 * 1024 ** 3),  # At least 5 GB free recommended
    }


@router.post("/validate-raster", response_model=RasterValidationReport)
def validate_raster_file(
    file_path: str = Query(..., description="Absolute path or relative path within data directory.")
) -> RasterValidationReport:
    """Inspect and validate raster geometry, dimensions, CRS, nodata, and measurement integrity."""
    path = Path(file_path)
    if not path.is_absolute():
        path = settings.data_dir / path

    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Raster file not found: {path}")

    report = inspect_and_validate_raster(path)
    return report


@router.post("/acquire", response_model=AcquiredProductManifestEntry)
def acquire_satellite_product(request: DownloadRequest) -> AcquiredProductManifestEntry:
    """Download a selected satellite product with chunked streaming, disk checks, and raster validation."""
    mgr = SafeDownloadManager()
    try:
        download_result = mgr.download_cdse_product(
            product_id=request.product_id,
            product_name=request.product_name,
            estimated_size_mb=request.estimated_size_mb
        )
        local_path = Path(download_result["local_path"])

        # Validate raster
        validation = inspect_and_validate_raster(
            local_path,
            precomputed_checksum=download_result["sha256_checksum"]
        )

        entry = AcquiredProductManifestEntry(
            product_id=request.product_id,
            source_catalog="Copernicus Data Space Ecosystem",
            acquisition_time=None,
            original_filename=request.product_name,
            local_path=str(local_path),
            file_size_bytes=download_result["file_size_bytes"],
            file_size_mb=download_result["file_size_mb"],
            sha256_checksum=download_result["sha256_checksum"],
            download_timestamp=validation.validated_at,
            processing_status="validated" if validation.is_readable else "validation_failed",
            validation=validation,
            known_limitations=validation.validation_warnings
        )

        register_acquired_product(entry)
        return entry

    except AuthCredentialsMissingError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except InsufficientStorageError as e:
        raise HTTPException(status_code=507, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")
