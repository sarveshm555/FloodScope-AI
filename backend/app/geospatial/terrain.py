import logging
import numpy as np
import rasterio
from rasterio.windows import from_bounds
from rasterio.features import shapes
from shapely.geometry import shape, box, mapping
from shapely.ops import unary_union
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

from backend.app.core.config import settings
from backend.app.schemas.analysis import (
    TerrainAnalysisRequest,
    TerrainAnalysisResponse,
    TerrainStatistics,
    FloodScenarioRequest,
    FloodScenarioResponse,
)

logger = logging.getLogger("floodscope.terrain")


def get_default_dem_path() -> Path:
    """Return path to verified Copernicus DEM mosaic in processed data directory."""
    mosaic_path = settings.data_dir / "processed" / "dem_mosaic_pilot_aoi.tif"
    if not mosaic_path.exists():
        # Fallback to raw N27 if mosaic is missing
        n27_path = settings.data_dir / "raw" / "Copernicus_DSM_COG_10_N27_00_E085_00_DEM.tif"
        if n27_path.exists():
            return n27_path
        raise FileNotFoundError(f"DEM raster not found at expected path: {mosaic_path}")
    return mosaic_path


def compute_terrain_and_slope(request: TerrainAnalysisRequest) -> TerrainAnalysisResponse:
    """Analyze real DEM terrain, calculate Horn/gradient slope in degrees, and extract low-slope basins.
    
    Methodology:
    - Calculates grid cell dimension in meters at central latitude using WGS84 ellipsoidal scaling.
    - Derives finite-difference surface gradients (dy, dx).
    - Computes slope: theta = arctan(sqrt(dx^2 + dy^2)).
    - Extracts low-slope valley candidates without falsely asserting floodwater presence.
    """
    dem_path = get_default_dem_path()
    aoi_w, aoi_s, aoi_e, aoi_n = request.bbox
    aoi_poly = box(aoi_w, aoi_s, aoi_e, aoi_n)

    with rasterio.open(str(dem_path)) as src:
        # Validate spatial intersection
        dem_poly = box(src.bounds.left, src.bounds.bottom, src.bounds.right, src.bounds.top)
        if not dem_poly.intersects(aoi_poly):
            raise ValueError(f"Requested AOI {request.bbox} does not intersect DEM bounds {list(src.bounds)}")

        win = from_bounds(aoi_w, aoi_s, aoi_e, aoi_n, src.transform)
        elev_data = src.read(1, window=win)
        win_transform = rasterio.windows.transform(win, src.transform)
        crs_str = str(src.crs)

        # Handle NoData or NaN
        nd = src.nodata
        valid_mask = ~np.isnan(elev_data)
        if nd is not None:
            valid_mask &= (elev_data != nd)

        if not np.any(valid_mask):
            raise ValueError("No valid elevation data found in requested AOI window.")

        # Compute cell spacing in meters
        center_lat = (aoi_s + aoi_n) / 2.0
        # 1 deg lon ~ 111,320m * cos(lat), 1 deg lat ~ 110,540m
        dx_m = abs(src.transform.a) * 111320.0 * np.cos(np.radians(center_lat))
        dy_m = abs(src.transform.e) * 110540.0

        # Gradient & Slope
        grad_y, grad_x = np.gradient(elev_data, dy_m, dx_m)
        slope_rad = np.arctan(np.sqrt(grad_x**2 + grad_y**2))
        slope_deg = np.degrees(slope_rad)

        valid_elev = elev_data[valid_mask]
        valid_slope = slope_deg[valid_mask]

        elev_min = float(np.min(valid_elev))
        elev_max = float(np.max(valid_elev))
        elev_mean = float(np.mean(valid_elev))

        slope_min = float(np.min(valid_slope))
        slope_max = float(np.max(valid_slope))
        slope_mean = float(np.mean(valid_slope))

        pixel_area_km2 = (dx_m * dy_m) / 1e6
        total_pixels = int(valid_elev.size)

        # Low slope (< slope_threshold_deg)
        low_slope_mask = valid_mask & (slope_deg <= request.slope_threshold_deg)
        low_slope_count = int(np.count_nonzero(low_slope_mask))
        low_slope_area = round(low_slope_count * pixel_area_km2, 3)

        # Valley floor candidates (low slope AND elevation <= threshold)
        elev_thresh = request.elevation_threshold_m or elev_max
        valley_mask = low_slope_mask & (elev_data <= elev_thresh)
        valley_count = int(np.count_nonzero(valley_mask))
        valley_area = round(valley_count * pixel_area_km2, 3)

        # Vectorize valley candidate polygon for GeoJSON overlay
        features = []
        if valley_count > 0:
            # Downsample slightly if large to ensure fast GeoJSON transmission
            mask_uint8 = valley_mask.astype(np.uint8)
            for geom, val in shapes(mask_uint8, mask=valley_mask, transform=win_transform):
                if val == 1:
                    s = shape(geom)
                    if s.area > (win_transform.a * win_transform.a * 4):  # filter isolated 1-2 pixel noise
                        features.append({
                            "type": "Feature",
                            "geometry": mapping(s),
                            "properties": {
                                "type": "valley_floor_candidate",
                                "max_slope_deg": request.slope_threshold_deg,
                                "max_elev_m": elev_thresh,
                                "source": "Copernicus DEM GLO-30 (real)"
                            }
                        })

        geojson_layer = {
            "type": "FeatureCollection",
            "features": features[:250]  # limit to top components for map performance
        }

        stats = TerrainStatistics(
            elevation_min_m=round(elev_min, 1),
            elevation_max_m=round(elev_max, 1),
            elevation_mean_m=round(elev_mean, 1),
            slope_min_deg=round(slope_min, 1),
            slope_max_deg=round(slope_max, 1),
            slope_mean_deg=round(slope_mean, 1),
            total_pixels=total_pixels,
            low_slope_pixels=low_slope_count,
            low_slope_area_km2=low_slope_area,
            valley_candidate_pixels=valley_count,
            valley_candidate_area_km2=valley_area,
        )

        return TerrainAnalysisResponse(
            source_dem=dem_path.name,
            crs=crs_str,
            pixel_resolution_m=[round(dx_m, 2), round(dy_m, 2)],
            bounds=[aoi_w, aoi_s, aoi_e, aoi_n],
            statistics=stats,
            limitations=[
                "Calculated from static Copernicus DEM GLO-30 (pre-event topography).",
                "Low elevation or low slope does not prove the presence of water or flood occurrence.",
                "Surface roughness, micro-embankments, and sub-30m drainage channels are not resolved."
            ],
            disclaimer="Terrain analysis indicates physical topographic slope and valley geometry. It is NOT satellite flood detection.",
            geojson_layer=geojson_layer
        )


def generate_hypothetical_flood_scenario(request: FloodScenarioRequest) -> FloodScenarioResponse:
    """Generate an explicitly labeled, user-parameterized HYPOTHETICAL flood scenario from real DEM.
    
    Grounded scientific assumptions:
    - Uses real Copernicus DEM elevation and slope.
    - Water stage is bounded by hypothetical water_level_m threshold along the Trishuli river valley.
    - Restricts extent to gentle slopes (<= max_slope_deg) to avoid impossible vertical mountain flooding.
    - STRICTLY LABELED AS HYPOTHETICAL SCENARIO.
    """
    dem_path = get_default_dem_path()
    aoi_w, aoi_s, aoi_e, aoi_n = request.aoi_bbox

    with rasterio.open(str(dem_path)) as src:
        win = from_bounds(aoi_w, aoi_s, aoi_e, aoi_n, src.transform)
        elev_data = src.read(1, window=win)
        win_transform = rasterio.windows.transform(win, src.transform)

        center_lat = (aoi_s + aoi_n) / 2.0
        dx_m = abs(src.transform.a) * 111320.0 * np.cos(np.radians(center_lat))
        dy_m = abs(src.transform.e) * 110540.0
        grad_y, grad_x = np.gradient(elev_data, dy_m, dx_m)
        slope_deg = np.degrees(np.arctan(np.sqrt(grad_x**2 + grad_y**2)))

        # Mask: elevation <= water_level_m AND slope <= max_slope_deg
        valid = ~np.isnan(elev_data)
        if src.nodata is not None:
            valid &= (elev_data != src.nodata)

        scenario_mask = valid & (elev_data <= request.water_level_m) & (slope_deg <= request.max_slope_deg)
        pixel_count = int(np.count_nonzero(scenario_mask))
        extent_km2 = round(pixel_count * (dx_m * dy_m) / 1e6, 3)

        features = []
        if pixel_count > 0:
            for geom, val in shapes(scenario_mask.astype(np.uint8), mask=scenario_mask, transform=win_transform):
                if val == 1:
                    s = shape(geom)
                    if s.area > (win_transform.a * win_transform.a * 4):
                        features.append({
                            "type": "Feature",
                            "geometry": mapping(s),
                            "properties": {
                                "scenario": "Hypothetical Inundation Scenario",
                                "water_level_m": request.water_level_m,
                                "max_slope_deg": request.max_slope_deg,
                                "is_satellite_observation": False,
                                "caveat": "Illustrative model only; not verified satellite inundation"
                            }
                        })

        geojson = {
            "type": "FeatureCollection",
            "features": features
        }

        return FloodScenarioResponse(
            is_hypothetical=True,
            scenario_name=f"Hypothetical {request.water_level_m}m River Stage Scenario",
            hypothesis_statement=(
                f"Assumes an illustrative flood stage reaching {request.water_level_m} meters elevation "
                f"on valley terrain slopes <= {request.max_slope_deg} degrees."
            ),
            water_level_threshold_m=request.water_level_m,
            max_slope_deg=request.max_slope_deg,
            extent_area_km2=extent_km2,
            geojson=geojson,
            limitations=[
                "This is a parameterized hypothetical terrain model, NOT observed satellite flood extent.",
                "No hydrodynamic routing or rainfall-runoff equations are modeled.",
                "Real flood extents require post-event SAR amplitude difference verification."
            ],
            disclaimer="FOR PLANNING & SIMULATION DEMONSTRATION ONLY. Do not use for emergency operational rescue decisions."
        )
