import json
import logging
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime, timezone

from backend.app.core.config import settings, PROJECT_ROOT
from backend.app.schemas.downloads import DataManifest, AcquiredProductManifestEntry

logger = logging.getLogger("floodscope.manifest")


def get_manifest_path() -> Path:
    """Return destination path for data manifest file."""
    manifest_dir = settings.data_dir
    manifest_file = manifest_dir / "manifest.json"
    if not manifest_file.exists():
        repo_manifest = (PROJECT_ROOT / "data" / "manifest.json").resolve()
        if repo_manifest.exists():
            return repo_manifest
    manifest_dir.mkdir(parents=True, exist_ok=True)
    return manifest_file


def load_manifest() -> DataManifest:
    """Load existing manifest or initialize new instance."""
    path = get_manifest_path()
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return DataManifest(**data)
        except Exception as e:
            logger.warning(f"Could not parse existing manifest; initializing fresh manifest: {e}")

    return DataManifest(
        data_directory=str(settings.data_dir),
        aoi_bbox=[85.10, 27.85, 85.25, 28.05],
        products={}
    )


def save_manifest(manifest: DataManifest) -> Path:
    """Save manifest atomically to disk."""
    path = get_manifest_path()
    manifest.last_updated_at = datetime.now(timezone.utc).isoformat()
    temp_path = path.with_suffix(".tmp")
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(manifest.model_dump(), f, indent=2)
    temp_path.replace(path)
    logger.info(f"Updated data manifest at {path}")
    return path


def register_acquired_product(entry: AcquiredProductManifestEntry) -> DataManifest:
    """Record an acquired and validated product entry in the manifest."""
    manifest = load_manifest()
    manifest.products[entry.product_id] = entry
    save_manifest(manifest)
    return manifest
