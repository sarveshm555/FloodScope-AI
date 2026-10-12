export interface HealthServicesStatus {
  copernicus_catalog_available: boolean;
  cdse_download_credentials_configured: boolean;
  llm_provider_configured: boolean;
  llm_provider_name: string | null;
  ohsome_osm_api_available: boolean;
}

export interface BackendHealth {
  application_name: string;
  status: string;
  backend_version: string;
  environment: string;
  timestamp: string;
  config_available: boolean;
  data_directory: string;
  data_directory_exists: boolean;
  services: HealthServicesStatus;
}

export interface AreaOfInterest {
  id: string;
  name: string;
  region: string;
  country: string;
  bbox: [number, number, number, number]; // [min_lon, min_lat, max_lon, max_lat]
  defaultDate: string;
}

export interface SatelliteProductMetadata {
  id: string;
  name: string;
  collection: string;
  platform: string;
  acquisition_time: string;
  product_type: string;
  orbit_direction: string | null;
  relative_orbit: number | null;
  operational_mode: string | null;
  polarization: string | null;
  cloud_cover_percentage: number | null;
  size_mb: number | null;
  size_bytes: number | null;
  footprint_geojson: Record<string, any> | null;
  intersects_aoi: boolean;
  aoi_intersection_percent: number;
  timing: 'pre-event' | 'post-event' | 'event-day';
  delta_days_from_event: number;
  selection_status: 'recommended_pair' | 'compatible_candidate' | 'alternate_orbit' | 'cloud_risk' | 'rejected_no_intersection';
  selection_reason: string;
  retrieval_timestamp: string;
  metadata_source: string;
  data_downloaded: boolean;
}

export interface CandidatePairSummary {
  pre_event_product_id: string;
  pre_event_product_name: string;
  pre_event_date: string;
  post_event_product_id: string;
  post_event_product_name: string;
  post_event_date: string;
  relative_orbit: number;
  orbit_direction: string;
  polarization: string;
  temporal_baseline_days: number;
  suitability_score: number;
  recommendation_reason: string;
}

export interface CatalogSearchResponse {
  search_id: string;
  query_parameters: {
    bbox: number[];
    event_date: string;
    pre_days: number;
    post_days: number;
    include_sentinel_1: boolean;
    include_sentinel_2: boolean;
    orbit_direction: string | null;
  };
  retrieval_timestamp: string;
  total_discovered: number;
  sentinel_1_count: number;
  sentinel_2_count: number;
  sentinel_1_candidates: SatelliteProductMetadata[];
  sentinel_2_candidates: SatelliteProductMetadata[];
  recommended_sar_pairs: CandidatePairSummary[];
  warnings: string[];
  metadata_source: string;
  data_downloaded: boolean;
}

export interface AnalysisState {
  status: 'idle' | 'discovering' | 'downloading' | 'processing' | 'completed' | 'failed';
  selectedArea: AreaOfInterest;
  eventDate: string;
  activeTab: 'discovery' | 'summary' | 'connectivity' | 'copilot';
}
