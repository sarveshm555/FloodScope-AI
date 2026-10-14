import logging
import numpy as np
from typing import Dict, Any, List, Optional
from shapely.geometry import shape, LineString, Polygon, MultiPolygon, Point, mapping
from shapely.ops import unary_union

from backend.app.schemas.analysis import InfrastructureExposureSummary

logger = logging.getLogger("floodscope.exposure")


from shapely.prepared import prep


def calculate_line_length_km(geom: Any) -> float:
    """Calculate geodesic distance in kilometers from EPSG:4326 line geometry (LineString, MultiLineString, GeometryCollection)."""
    if geom is None or geom.is_empty:
        return 0.0
    if hasattr(geom, "geoms"):
        return sum(calculate_line_length_km(part) for part in geom.geoms)
    if not hasattr(geom, "coords"):
        return 0.0
    coords = list(geom.coords)
    if len(coords) < 2:
        return 0.0
    total_km = 0.0
    for i in range(len(coords) - 1):
        lon1, lat1 = coords[i]
        lon2, lat2 = coords[i + 1]
        mid_lat = (lat1 + lat2) / 2.0
        # Metric conversion factors for WGS84
        dx = (lon2 - lon1) * 111.32 * np.cos(np.radians(mid_lat))
        dy = (lat2 - lat1) * 110.54
        total_km += np.sqrt(dx**2 + dy**2)
    return total_km


def extract_linear_geometry(geom: Any) -> Optional[Any]:
    """Extract clean LineString or MultiLineString from intersection geometry for MapLibre rendering."""
    if geom is None or geom.is_empty:
        return None
    if geom.geom_type in ("LineString", "MultiLineString"):
        return geom
    if geom.geom_type == "GeometryCollection":
        lines = [g for g in geom.geoms if g.geom_type in ("LineString", "MultiLineString") and not g.is_empty]
        if not lines:
            return None
        if len(lines) == 1:
            return lines[0]
        flat_lines = []
        for l in lines:
            if hasattr(l, "geoms"):
                flat_lines.extend(list(l.geoms))
            else:
                flat_lines.append(l)
        return MultiLineString(flat_lines)
    return None


def assess_infrastructure_exposure(
    flood_geojson: Dict[str, Any],
    osm_geojson: Dict[str, Any],
    scenario_name: str = "Illustrative Flood Scenario"
) -> InfrastructureExposureSummary:
    """Perform rigorous spatial intersection between flood boundary and OSM infrastructure.
    
    Rules:
    - Confirmed damage is strictly False (spatial intersection implies exposure, not destruction).
    - Accurately computes road length intersecting the flood polygon.
    - Counts intersecting mapped buildings, bridges, and health facilities.
    - Identifies settlements lacking road connectivity to emergency amenities.
    """
    flood_features = flood_geojson.get("features", [])
    if not flood_features:
        return InfrastructureExposureSummary(
            is_confirmed_damage=False,
            flood_scenario_name=scenario_name,
            total_buildings_mapped=len(osm_geojson.get("buildings", {}).get("features", [])),
            exposed_buildings_count=0,
            exposed_buildings_percent=0.0,
            total_road_length_km=0.0,
            exposed_road_length_km=0.0,
            exposed_road_percent=0.0,
            total_bridges_mapped=len(osm_geojson.get("bridges", {}).get("features", [])),
            exposed_bridges_count=0,
            health_facilities_mapped=len(osm_geojson.get("amenities", {}).get("features", [])),
            exposed_health_facilities_count=0,
            isolated_settlements=[],
            limitations=["Empty flood extent input; no exposure computed."],
            disclaimer="No flood intersection calculated."
        )

    # Union all flood polygons
    flood_polys = []
    for f in flood_features:
        try:
            geom = shape(f["geometry"])
            if geom.is_valid and not geom.is_empty:
                flood_polys.append(geom)
        except Exception:
            continue

    if not flood_polys:
        raise ValueError("No valid geometry could be parsed from flood polygon GeoJSON.")

    flood_union = unary_union(flood_polys)
    prep_flood = prep(flood_union)
    fminx, fminy, fmaxx, fmaxy = flood_union.bounds

    # 1. Road Exposure
    roads_fc = osm_geojson.get("roads", {}).get("features", [])
    total_road_km = 0.0
    exposed_road_km = 0.0
    exposed_road_features = []

    for rf in roads_fc:
        try:
            geom = shape(rf["geometry"])
            length_km = calculate_line_length_km(geom)
            total_road_km += length_km
            rminx, rminy, rmaxx, rmaxy = geom.bounds
            if not (rmaxx < fminx or rminx > fmaxx or rmaxy < fminy or rminy > fmaxy):
                if prep_flood.intersects(geom):
                    inter = geom.intersection(flood_union)
                    if not inter.is_empty:
                        exp_km = calculate_line_length_km(inter)
                        line_geom = extract_linear_geometry(inter)
                        if line_geom is not None and exp_km > 0.0:
                            exposed_road_km += exp_km
                            exposed_road_features.append({
                                "type": "Feature",
                                "geometry": mapping(line_geom),
                                "properties": {
                                    "osm_id": rf.get("properties", {}).get("osm_id"),
                                    "name": rf.get("properties", {}).get("name", "Unnamed Road"),
                                    "exposed_length_km": round(exp_km, 3),
                                    "status": "potentially_inundated"
                                }
                            })
        except Exception as e:
            logger.debug(f"Error checking road feature: {e}")
            continue

    # 2. Bridge Exposure
    bridges_fc = osm_geojson.get("bridges", {}).get("features", [])
    total_bridges = len(bridges_fc)
    exposed_bridge_features = []
    for bf in bridges_fc:
        try:
            geom = shape(bf["geometry"])
            bminx, bminy, bmaxx, bmaxy = geom.bounds
            if not (bmaxx < fminx or bminx > fmaxx or bmaxy < fminy or bminy > fmaxy):
                if prep_flood.intersects(geom):
                    exposed_bridge_features.append(bf)
        except Exception:
            continue

    # 3. Building Exposure
    buildings_fc = osm_geojson.get("buildings", {}).get("features", [])
    total_buildings = len(buildings_fc)
    exposed_building_features = []
    for b_feat in buildings_fc:
        try:
            geom = shape(b_feat["geometry"])
            bminx, bminy, bmaxx, bmaxy = geom.bounds
            if not (bmaxx < fminx or bminx > fmaxx or bmaxy < fminy or bminy > fmaxy):
                if prep_flood.intersects(geom):
                    exposed_building_features.append(b_feat)
        except Exception:
            continue

    # 4. Clinics / Hospitals
    clinics_fc = osm_geojson.get("amenities", {}).get("features", [])
    total_clinics = len(clinics_fc)
    exposed_clinics = []
    for cf in clinics_fc:
        try:
            geom = shape(cf["geometry"])
            cminx, cminy, cmaxx, cmaxy = geom.bounds
            if not (cmaxx < fminx or cminx > fmaxx or cmaxy < fminy or cminy > fmaxy):
                if prep_flood.intersects(geom):
                    exposed_clinics.append(cf)
        except Exception:
            continue

    # 5. Settlement Isolation Check
    places_fc = osm_geojson.get("places", {}).get("features", [])
    isolated_settlements = []
    for pf in places_fc:
        try:
            pt = shape(pf["geometry"])
            pname = pf.get("properties", {}).get("name", "Unnamed")
            if prep_flood.intersects(pt):
                isolated_settlements.append(f"{pname} (direct flood zone overlap)")
            else:
                for eb in exposed_bridge_features:
                    b_geom = shape(eb["geometry"])
                    if pt.distance(b_geom) < 0.015:  # ~1.5km
                        isolated_settlements.append(f"{pname} (potential access cutoff via Bridge #{eb.get('properties', {}).get('osm_id')})")
                        break
        except Exception:
            continue

    # Deduplicate settlements
    isolated_settlements = list(dict.fromkeys(isolated_settlements))[:10]

    b_pct = round((len(exposed_building_features) / total_buildings * 100.0), 2) if total_buildings else 0.0
    r_pct = round((exposed_road_km / total_road_km * 100.0), 2) if total_road_km else 0.0

    return InfrastructureExposureSummary(
        is_confirmed_damage=False,
        flood_scenario_name=scenario_name,
        total_buildings_mapped=total_buildings,
        exposed_buildings_count=len(exposed_building_features),
        exposed_buildings_percent=b_pct,
        total_road_length_km=round(total_road_km, 2),
        exposed_road_length_km=round(exposed_road_km, 2),
        exposed_road_percent=r_pct,
        total_bridges_mapped=total_bridges,
        exposed_bridges_count=len(exposed_bridge_features),
        health_facilities_mapped=total_clinics,
        exposed_health_facilities_count=len(exposed_clinics),
        isolated_settlements=isolated_settlements,
        limitations=[
            "Spatial intersection indicates potential water inundation exposure, NOT structural destruction or building collapse.",
            "Building footprints and bridges reflect pre-event OpenStreetMap coverage.",
            "Road impassability requires ground validation or high-resolution optical inspection."
        ],
        disclaimer="DO NOT USE FOR DIRECT RESCUE ROUTING WITHOUT IN-SITU VALIDATION.",
        geojson_layers={
            "exposed_roads": {"type": "FeatureCollection", "features": exposed_road_features},
            "exposed_bridges": {"type": "FeatureCollection", "features": exposed_bridge_features},
            "exposed_buildings": {"type": "FeatureCollection", "features": exposed_building_features[:500]},
        }
    )
