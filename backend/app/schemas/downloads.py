from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class DownloadRequest(BaseModel):
    """Request to initiate satellite product download."""
    product_id: str = Field(..., description="Unique product UUID from Copernicus Data Space.")
    product_name: str = Field(..., description="Product SAFE or COG name.")
    collection: str = Field(default="SENTINEL-1", description="'SENTINEL-1' or 'SENTINEL-2' or 'COP-DEM'")
    estimated_size_mb: Optional[float] = Field(None, description="Reported product size in Megabytes.")
    target_filename: Optional[str] = Field(None, description="Optional custom destination filename.")


class RasterValidationReport(BaseModel):
    """Detailed structural and geospatial validation report for a downloaded raster."""
    file_path: str
    file_size_bytes: int
    file_size_mb: float
    sha256_checksum: str
    is_readable: bool
    driver: str
    width: int
    height: int
    band_count: int
    dtype: str
    crs: Optional[str]
    geotransform: List[float]
    bounds: List[float]  # [left, bottom, right, top]
    pixel_resolution: List[float]  # [res_x, res_y]
    nodata_value: Optional[float]
    valid_data_percent: float
    intersects_aoi: bool
    is_measurement_data: bool
    is_valid_cog: bool
    validation_warnings: List[str]
    validated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class AcquiredProductManifestEntry(BaseModel):
    """Entry in the machine-readable data provenance manifest."""
    product_id: str
    source_catalog: str
    acquisition_time: Optional[str]
    original_filename: str
    local_path: str
    file_size_bytes: int
    file_size_mb: float
    sha256_checksum: str
    download_timestamp: str
    processing_status: str  # 'acquired', 'validated', 'validation_failed'
    validation: Optional[RasterValidationReport] = None
    known_limitations: List[str] = Field(default_factory=list)


class DataManifest(BaseModel):
    """Machine-readable inventory of all acquired and validated data assets."""
    manifest_version: str = "1.0.0"
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    last_updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    data_directory: str
    aoi_bbox: List[float] = Field(
        default=[85.10, 27.85, 85.25, 28.05],
        description="Pilot bounding box in EPSG:4326."
    )
    products: Dict[str, AcquiredProductManifestEntry] = Field(default_factory=dict)
