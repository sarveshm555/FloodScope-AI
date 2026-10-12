import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple
import requests
from shapely.geometry import box, shape
from shapely.ops import unary_union

from backend.app.schemas.catalog import (
    CatalogSearchRequest,
    CatalogSearchResponse,
    SatelliteProductMetadata,
    CandidatePairSummary,
)

logger = logging.getLogger("floodscope.catalog")

CDSE_ODATA_URL = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"

# In-memory search results registry
_SEARCH_REGISTRY: Dict[str, CatalogSearchResponse] = {}


def parse_iso_datetime(dt_str: str) -> datetime:
    """Parse ISO8601 strings, including those with sub-seconds or trailing Z."""
    cleaned = dt_str.replace("Z", "+00:00")
    return datetime.fromisoformat(cleaned)


def check_footprint_intersection(
    geo_footprint: Optional[Dict[str, Any]],
    aoi_bbox: List[float]
) -> Tuple[bool, float]:
    """Calculate geometric intersection between product footprint and AOI box.
    
    Returns:
        (intersects_aoi: bool, coverage_percent: float)
    """
    if not geo_footprint:
        return False, 0.0

    try:
        west, south, east, north = aoi_bbox
        aoi_poly = box(west, south, east, north)
        aoi_area = aoi_poly.area
        if aoi_area <= 0:
            return False, 0.0

        footprint_geom = shape(geo_footprint)
        if not footprint_geom.is_valid:
            footprint_geom = footprint_geom.buffer(0)

        if not footprint_geom.intersects(aoi_poly):
            return False, 0.0

        intersection = footprint_geom.intersection(aoi_poly)
        coverage_pct = round((intersection.area / aoi_area) * 100.0, 2)
        return True, min(coverage_pct, 100.0)
    except Exception as e:
        logger.warning(f"Failed to calculate footprint intersection: {e}")
        return False, 0.0


def query_cdse_odata(
    filter_expr: str,
    top: int = 40,
    session: Optional[requests.Session] = None
) -> List[Dict[str, Any]]:
    """Query Copernicus Data Space Ecosystem OData API with pagination and error handling."""
    s = session or requests.Session()
    headers = {"User-Agent": "FloodScope-AI-Discovery/1.0"}
    params = {
        "$filter": filter_expr,
        "$top": top,
        "$orderby": "ContentDate/Start asc",
        "$expand": "Attributes"
    }

    try:
        resp = s.get(CDSE_ODATA_URL, params=params, headers=headers, timeout=25)
        if resp.status_code == 429:
            logger.warning("CDSE catalog rate limit (429) encountered.")
            return []
        resp.raise_for_status()
        data = resp.json()
        return data.get("value", [])
    except requests.exceptions.Timeout:
        logger.error("CDSE catalog query timed out after 25s.")
        return []
    except requests.exceptions.RequestException as e:
        logger.error(f"CDSE catalog query HTTP error: {e}")
        return []


def normalize_product_record(
    raw: Dict[str, Any],
    aoi_bbox: List[float],
    event_dt: datetime,
    retrieval_ts: str
) -> SatelliteProductMetadata:
    """Transform raw CDSE OData record into normalized SatelliteProductMetadata with provenance."""
    raw_attrs = {a["Name"]: a["Value"] for a in raw.get("Attributes", [])}
    collection = "SENTINEL-1" if "S1" in raw.get("Name", "") else "SENTINEL-2"

    # Acquisition timestamp
    content_date = raw.get("ContentDate", {})
    acq_str = content_date.get("Start") or raw.get("OriginDate") or datetime.now(timezone.utc).isoformat()
    acq_dt = parse_iso_datetime(acq_str)

    # Timing relative to flood event
    delta_seconds = (acq_dt - event_dt).total_seconds()
    delta_days = round(delta_seconds / 86400.0, 2)
    if delta_days < -0.5:
        timing = "pre-event"
    elif delta_days > 0.5:
        timing = "post-event"
    else:
        timing = "event-day"

    # Geometry intersection
    geo_footprint = raw.get("GeoFootprint")
    intersects, coverage_pct = check_footprint_intersection(geo_footprint, aoi_bbox)

    # Platform derivation
    name = raw.get("Name", "")
    platform = name[:3] if len(name) >= 3 else "Unknown"

    # Cloud cover (Optical)
    cloud_cover = None
    if "cloudCover" in raw_attrs:
        try:
            cloud_cover = round(float(raw_attrs["cloudCover"]), 2)
        except (ValueError, TypeError):
            pass

    # Relative orbit
    rel_orbit = None
    if "relativeOrbitNumber" in raw_attrs:
        try:
            rel_orbit = int(raw_attrs["relativeOrbitNumber"])
        except (ValueError, TypeError):
            pass

    # Product Type
    product_type = raw_attrs.get("productType", "UNKNOWN")
    if product_type == "UNKNOWN":
        if "GRD" in name:
            product_type = "IW_GRDH_1S"
        elif "MSIL2A" in name:
            product_type = "S2MSI2A"
        elif "MSIL1C" in name:
            product_type = "S2MSI1C"

    # Size calculation
    content_length = raw.get("ContentLength")
    size_mb = round(content_length / (1024 * 1024), 2) if content_length else None

    # Default selection categorization (will be refined by pair matcher)
    if not intersects:
        selection_status = "rejected_no_intersection"
        selection_reason = f"Product footprint does not intersect the requested AOI ({coverage_pct}% overlap)."
    elif collection == "SENTINEL-2":
        if cloud_cover is not None and cloud_cover > 75.0:
            selection_status = "cloud_risk"
            selection_reason = (
                f"Scene cloud cover is high ({cloud_cover}%). High probability of optical occlusion; "
                "AOI-level suitability requires inspection of scene cloud mask."
            )
        else:
            selection_status = "compatible_candidate"
            selection_reason = (
                f"Optical observation with {cloud_cover if cloud_cover is not None else 'unspecified'}% "
                f"scene cloud cover. Covers {coverage_pct}% of pilot AOI."
            )
    else:
        selection_status = "compatible_candidate"
        selection_reason = (
            f"Sentinel-1 SAR acquisition (Orbit {raw_attrs.get('orbitDirection')}, Track {rel_orbit}) "
            f"covers {coverage_pct}% of pilot AOI. Candidate for repeat-pass pairing."
        )

    return SatelliteProductMetadata(
        id=str(raw.get("Id")),
        name=name,
        collection=collection,
        platform=platform,
        acquisition_time=acq_str,
        product_type=product_type,
        orbit_direction=raw_attrs.get("orbitDirection"),
        relative_orbit=rel_orbit,
        operational_mode=raw_attrs.get("operationalMode", "IW"),
        polarization=raw_attrs.get("polarisationChannels") or raw_attrs.get("polarization"),
        cloud_cover_percentage=cloud_cover,
        size_mb=size_mb,
        size_bytes=content_length,
        footprint_geojson=geo_footprint,
        intersects_aoi=intersects,
        aoi_intersection_percent=coverage_pct,
        timing=timing,
        delta_days_from_event=delta_days,
        selection_status=selection_status,
        selection_reason=selection_reason,
        retrieval_timestamp=retrieval_ts,
        metadata_source="Copernicus Data Space Ecosystem (CDSE) OData Catalogue",
        data_downloaded=False,
    )


def match_candidate_sar_pairs(
    s1_candidates: List[SatelliteProductMetadata]
) -> Tuple[List[SatelliteProductMetadata], List[CandidatePairSummary]]:
    """Match compatible pre- and post-event Sentinel-1 observations by orbit and geometry.
    
    Pairs must match:
    - Same relativeOrbit
    - Same orbitDirection
    - Same operationalMode (typically IW)
    - Same polarization channels (e.g. VV&VH)
    - Intersect AOI
    """
    valid_candidates = [c for c in s1_candidates if c.intersects_aoi and c.relative_orbit is not None]
    pre_events = [c for c in valid_candidates if c.timing == "pre-event"]
    post_events = [c for c in valid_candidates if c.timing == "post-event"]

    pairs: List[CandidatePairSummary] = []

    for pre in pre_events:
        for post in post_events:
            # Check geometry compatibility
            if (
                pre.relative_orbit == post.relative_orbit
                and pre.orbit_direction == post.orbit_direction
                and pre.operational_mode == post.operational_mode
                and pre.polarization == post.polarization
            ):
                temporal_gap = abs(post.delta_days_from_event - pre.delta_days_from_event)
                # Ideal Sentinel-1 repeat pass is 12 days
                delta_from_12 = abs(temporal_gap - 12.0)
                # Score between 0.5 and 1.0 based on proximity to 12 days
                score = round(max(0.4, 1.0 - (delta_from_12 * 0.05)), 2)
                
                reason = (
                    f"Matched geometry: {pre.orbit_direction} Orbit {pre.relative_orbit}, "
                    f"Mode {pre.operational_mode}, Polarisation {pre.polarization}. "
                    f"Temporal baseline: {temporal_gap:.1f} days ({pre.acquisition_time[:10]} to {post.acquisition_time[:10]})."
                )
                
                pairs.append(
                    CandidatePairSummary(
                        pre_event_product_id=pre.id,
                        pre_event_product_name=pre.name,
                        pre_event_date=pre.acquisition_time,
                        post_event_product_id=post.id,
                        post_event_product_name=post.name,
                        post_event_date=post.acquisition_time,
                        relative_orbit=pre.relative_orbit,
                        orbit_direction=pre.orbit_direction or "UNKNOWN",
                        polarization=pre.polarization or "UNKNOWN",
                        temporal_baseline_days=temporal_gap,
                        suitability_score=score,
                        recommendation_reason=reason,
                    )
                )

    # Sort pairs by highest suitability score
    pairs.sort(key=lambda p: (p.suitability_score, -p.temporal_baseline_days), reverse=True)

    # Update candidate statuses for recommended products
    updated_candidates = []
    recommended_ids = set()
    if pairs:
        best_pair = pairs[0]
        recommended_ids.add(best_pair.pre_event_product_id)
        recommended_ids.add(best_pair.post_event_product_id)

    for c in s1_candidates:
        if c.id in recommended_ids:
            updated = c.model_copy(update={
                "selection_status": "recommended_pair",
                "selection_reason": (
                    f"Selected as primary SAR change pair (Track {c.relative_orbit}, {c.orbit_direction}). "
                    f"Shares identical acquisition geometry across the flood event."
                )
            })
            updated_candidates.append(updated)
        elif c.intersects_aoi and c.relative_orbit is not None:
            # Check if it has a pair in any candidate set
            in_any_pair = any(c.id == p.pre_event_product_id or c.id == p.post_event_product_id for p in pairs)
            status = "compatible_candidate" if in_any_pair else "alternate_orbit"
            reason = (
                f"Compatible SAR observation ({c.orbit_direction} Orbit {c.relative_orbit}). "
                f"{'Available as alternate paired observation.' if in_any_pair else 'No matching pre/post pair on same relative orbit within search window.'}"
            )
            updated_candidates.append(c.model_copy(update={
                "selection_status": status,
                "selection_reason": reason
            }))
        else:
            updated_candidates.append(c)

    return updated_candidates, pairs


def execute_catalog_discovery(
    request: CatalogSearchRequest,
    session: Optional[requests.Session] = None
) -> CatalogSearchResponse:
    """Execute live or mocked satellite data discovery across CDSE."""
    search_id = str(uuid.uuid4())
    retrieval_ts = datetime.now(timezone.utc).isoformat()
    warnings: List[str] = []

    try:
        event_dt = datetime.fromisoformat(f"{request.event_date}T00:00:00+00:00")
    except ValueError:
        event_dt = datetime.fromisoformat("2026-08-26T00:00:00+00:00")
        warnings.append(f"Invalid event date format '{request.event_date}'; defaulted to 2026-08-26.")

    start_dt = event_dt - timedelta(days=request.pre_days)
    end_dt = event_dt + timedelta(days=request.post_days)

    start_str = start_dt.strftime("%Y-%m-%dT00:00:00.000Z")
    end_str = end_dt.strftime("%Y-%m-%dT23:59:59.999Z")

    west, south, east, north = request.bbox
    wkt_poly = f"POLYGON(({west} {south}, {east} {south}, {east} {north}, {west} {north}, {west} {south}))"

    s1_candidates: List[SatelliteProductMetadata] = []
    s2_candidates: List[SatelliteProductMetadata] = []

    # 1. Discover Sentinel-1 SAR GRD
    if request.include_sentinel_1:
        s1_filters = [
            "Collection/Name eq 'SENTINEL-1'",
            f"OData.CSC.Intersects(area=geography'SRID=4326;{wkt_poly}')",
            f"ContentDate/Start gt {start_str}",
            f"ContentDate/Start lt {end_str}",
            "contains(Name, 'GRD')"
        ]
        if request.orbit_direction:
            s1_filters.append(f"Attributes/any(a: a/Name eq 'orbitDirection' and a/Value eq '{request.orbit_direction}')")

        s1_raw = query_cdse_odata(" and ".join(s1_filters), top=50, session=session)
        if not s1_raw:
            warnings.append(
                f"No Sentinel-1 GRD acquisitions returned for AOI between {start_dt.date()} and {end_dt.date()}."
            )
        for raw in s1_raw:
            try:
                norm = normalize_product_record(raw, request.bbox, event_dt, retrieval_ts)
                s1_candidates.append(norm)
            except Exception as e:
                logger.error(f"Failed to normalize S1 record {raw.get('Id')}: {e}")

    # 2. Discover Sentinel-2 Optical MSI
    if request.include_sentinel_2:
        s2_filters = [
            "Collection/Name eq 'SENTINEL-2'",
            f"OData.CSC.Intersects(area=geography'SRID=4326;{wkt_poly}')",
            f"ContentDate/Start gt {start_str}",
            f"ContentDate/Start lt {end_str}",
            "contains(Name, 'MSI')"
        ]
        s2_raw = query_cdse_odata(" and ".join(s2_filters), top=30, session=session)
        if not s2_raw:
            warnings.append(
                f"No Sentinel-2 MSI acquisitions returned for AOI between {start_dt.date()} and {end_dt.date()}."
            )
        for raw in s2_raw:
            try:
                norm = normalize_product_record(raw, request.bbox, event_dt, retrieval_ts)
                s2_candidates.append(norm)
            except Exception as e:
                logger.error(f"Failed to normalize S2 record {raw.get('Id')}: {e}")

    # 3. Match SAR candidate pairs
    s1_candidates, recommended_pairs = match_candidate_sar_pairs(s1_candidates)

    response = CatalogSearchResponse(
        search_id=search_id,
        query_parameters={
            "bbox": request.bbox,
            "event_date": request.event_date,
            "pre_days": request.pre_days,
            "post_days": request.post_days,
            "include_sentinel_1": request.include_sentinel_1,
            "include_sentinel_2": request.include_sentinel_2,
            "orbit_direction": request.orbit_direction,
        },
        retrieval_timestamp=retrieval_ts,
        total_discovered=len(s1_candidates) + len(s2_candidates),
        sentinel_1_count=len(s1_candidates),
        sentinel_2_count=len(s2_candidates),
        sentinel_1_candidates=s1_candidates,
        sentinel_2_candidates=s2_candidates,
        recommended_sar_pairs=recommended_pairs,
        warnings=warnings,
        metadata_source="Copernicus Data Space Ecosystem (CDSE) OData Catalogue",
        data_downloaded=False,
    )

    # Store in memory registry for retrieval by search_id
    _SEARCH_REGISTRY[search_id] = response
    return response


def get_search_results(search_id: str) -> Optional[CatalogSearchResponse]:
    """Retrieve saved catalog discovery results by search_id."""
    return _SEARCH_REGISTRY.get(search_id)
