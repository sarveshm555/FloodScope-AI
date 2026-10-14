import json
import logging
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Dict, Any, List, Optional
from shapely.geometry import shape, Point, LineString, Polygon, mapping, box
from shapely.ops import unary_union

from backend.app.core.config import settings

logger = logging.getLogger("floodscope.osm")


def get_osm_cache_path() -> Path:
    """Return local path to cached OSM raw payload on D: drive."""
    cache_dir = settings.data_dir / "raw"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / "osm_trishuli_infrastructure.json"


def fetch_osm_infrastructure(
    bbox: List[float] = [85.10, 27.85, 85.25, 28.05],
    use_cache: bool = True
) -> Dict[str, Any]:
    """Retrieve real OpenStreetMap infrastructure within pilot AOI via Overpass API.
    
    Retrieves:
    - Primary, secondary, trunk, tertiary, residential highways
    - Bridges
    - Buildings
    - Hospitals, clinics, and named settlement nodes
    
    Saves and reuses persistent cache on D: drive to protect against network drops and Overpass rate limits.
    """
    cache_path = get_osm_cache_path()
    # Check if existing raw test cache exists and copy over if helpful
    test_cache = settings.data_dir / "raw" / "osm_trishuli_test.json"
    if not cache_path.exists() and test_cache.exists():
        try:
            cache_path.write_bytes(test_cache.read_bytes())
        except Exception:
            pass

    if use_cache and cache_path.exists() and cache_path.stat().st_size > 1000:
        logger.info(f"Loading cached OSM infrastructure from {cache_path}")
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)

    aoi_w, aoi_s, aoi_e, aoi_n = bbox
    query = f"""[out:json][timeout:35];
(
  node["amenity"~"hospital|clinic"]({aoi_s},{aoi_w},{aoi_n},{aoi_e});
  node["place"~"town|village|hamlet"]({aoi_s},{aoi_w},{aoi_n},{aoi_e});
  way["highway"~"primary|secondary|trunk|tertiary|residential"]({aoi_s},{aoi_w},{aoi_n},{aoi_e});
  way["bridge"="yes"]({aoi_s},{aoi_w},{aoi_n},{aoi_e});
  way["building"]({aoi_s},{aoi_w},{aoi_n},{aoi_e});
);
out body;
>;
out skel qt;
"""
    url = "https://overpass-api.de/api/interpreter"
    data = urllib.parse.urlencode({"data": query}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"User-Agent": "FloodScope-AI/1.0 (disaster-response-hackathon)"}
    )

    logger.info("Executing Overpass query for real OpenStreetMap data in pilot AOI...")
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(payload, f)
            logger.info(f"Cached {len(payload.get('elements', []))} OSM elements to {cache_path}")
            return payload
    except Exception as e:
        logger.warning(f"Overpass API request failed or timed out: {e}")
        if cache_path.exists():
            logger.info("Falling back to existing local OSM cache.")
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        raise RuntimeError(f"Could not fetch OSM data and no local cache exists: {e}")


def parse_osm_geojson(osm_data: Dict[str, Any]) -> Dict[str, Any]:
    """Parse raw Overpass nodes and ways into categorized GeoJSON FeatureCollections."""
    elements = osm_data.get("elements", [])
    node_coords = {
        e["id"]: (e["lon"], e["lat"])
        for e in elements if e.get("type") == "node" and "lon" in e and "lat" in e
    }

    roads_features = []
    bridges_features = []
    buildings_features = []
    amenity_features = []
    place_features = []

    for e in elements:
        etype = e.get("type")
        tags = e.get("tags", {})
        eid = e.get("id")

        if etype == "node" and tags:
            lon, lat = e.get("lon"), e.get("lat")
            if lon is not None and lat is not None:
                pt_geom = {"type": "Point", "coordinates": [lon, lat]}
                if "amenity" in tags and tags["amenity"] in ["hospital", "clinic"]:
                    amenity_features.append({
                        "type": "Feature",
                        "id": f"node/{eid}",
                        "geometry": pt_geom,
                        "properties": {
                            "osm_id": eid,
                            "name": tags.get("name", "Unnamed Clinic"),
                            "amenity": tags.get("amenity"),
                            "source": "OpenStreetMap"
                        }
                    })
                elif "place" in tags:
                    place_features.append({
                        "type": "Feature",
                        "id": f"node/{eid}",
                        "geometry": pt_geom,
                        "properties": {
                            "osm_id": eid,
                            "name": tags.get("name", "Unnamed Settlement"),
                            "place": tags.get("place"),
                            "source": "OpenStreetMap"
                        }
                    })

        elif etype == "way" and tags:
            pts = [node_coords[nid] for nid in e.get("nodes", []) if nid in node_coords]
            if len(pts) >= 2:
                if "highway" in tags:
                    is_bridge = tags.get("bridge") == "yes"
                    feat = {
                        "type": "Feature",
                        "id": f"way/{eid}",
                        "geometry": {"type": "LineString", "coordinates": pts},
                        "properties": {
                            "osm_id": eid,
                            "name": tags.get("name", "Unnamed Road"),
                            "highway": tags.get("highway"),
                            "bridge": is_bridge,
                            "source": "OpenStreetMap"
                        }
                    }
                    roads_features.append(feat)
                    if is_bridge:
                        bridges_features.append(feat)

                elif "building" in tags and len(pts) >= 4:
                    feat = {
                        "type": "Feature",
                        "id": f"way/{eid}",
                        "geometry": {"type": "Polygon", "coordinates": [pts]},
                        "properties": {
                            "osm_id": eid,
                            "building": tags.get("building"),
                            "source": "OpenStreetMap"
                        }
                    }
                    buildings_features.append(feat)

    return {
        "roads": {"type": "FeatureCollection", "features": roads_features},
        "bridges": {"type": "FeatureCollection", "features": bridges_features},
        "buildings": {"type": "FeatureCollection", "features": buildings_features},
        "amenities": {"type": "FeatureCollection", "features": amenity_features},
        "places": {"type": "FeatureCollection", "features": place_features},
    }
