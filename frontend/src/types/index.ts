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

export interface RasterValidationReport {
  file_path: string;
  file_size_bytes: number;
  file_size_mb: number;
  sha256_checksum: string;
  is_readable: boolean;
  driver: string;
  width: number;
  height: number;
  band_count: number;
  dtype: string;
  crs: string | null;
  geotransform: number[];
  bounds: number[];
  pixel_resolution: number[];
  nodata_value: number | null;
  valid_data_percent: number;
  intersects_aoi: boolean;
  is_measurement_data: boolean;
  is_valid_cog: boolean;
  validation_warnings: string[];
  validated_at: string;
}

export interface AcquiredProductManifestEntry {
  product_id: string;
  source_catalog: string;
  acquisition_time: string | null;
  original_filename: string;
  local_path: string;
  file_size_bytes: number;
  file_size_mb: number;
  sha256_checksum: string;
  download_timestamp: string;
  processing_status: string;
  validation: RasterValidationReport | null;
  known_limitations: string[];
  product_category?: 'source' | 'derived' | string;
  format_label?: string;
}

export interface DataManifest {
  manifest_version: string;
  created_at: string;
  last_updated_at: string;
  data_directory: string;
  aoi_bbox: number[];
  products: Record<string, AcquiredProductManifestEntry>;
}

export interface StorageStatus {
  data_directory: string;
  total_gb: number;
  used_gb: number;
  free_gb: number;
  free_mb: number;
  storage_safe_for_downloads: boolean;
}

export interface AnalysisState {
  status: 'idle' | 'discovering' | 'downloading' | 'processing' | 'completed' | 'failed';
  selectedArea: AreaOfInterest;
  eventDate: string;
  activeTab: 'discovery' | 'summary' | 'connectivity' | 'copilot';
}

export interface TerrainStatistics {
  elevation_min_m: number;
  elevation_max_m: number;
  elevation_mean_m: number;
  slope_min_deg: number;
  slope_max_deg: number;
  slope_mean_deg: number;
  total_pixels: number;
  low_slope_pixels: number;
  low_slope_area_km2: number;
  valley_candidate_pixels: number;
  valley_candidate_area_km2: number;
}

export interface TerrainAnalysisResponse {
  source_dem: string;
  crs: string;
  pixel_resolution_m: number[];
  bounds: number[];
  statistics: TerrainStatistics;
  limitations: string[];
  disclaimer: string;
  geojson_layer?: Record<string, any>;
}

export interface FloodScenarioResponse {
  is_hypothetical: boolean;
  scenario_name: string;
  hypothesis_statement: string;
  water_level_threshold_m: number;
  max_slope_deg: number;
  extent_area_km2: number;
  geojson: Record<string, any>;
  limitations: string[];
  disclaimer: string;
}

export interface InfrastructureExposureSummary {
  is_confirmed_damage: boolean;
  flood_scenario_name: string;
  total_buildings_mapped: number;
  exposed_buildings_count: number;
  exposed_buildings_percent: number;
  total_road_length_km: number;
  exposed_road_length_km: number;
  exposed_road_percent: number;
  total_bridges_mapped: number;
  exposed_bridges_count: number;
  health_facilities_mapped: number;
  exposed_health_facilities_count: number;
  isolated_settlements: string[];
  limitations: string[];
  disclaimer: string;
  geojson_layers: Record<string, any>;
}

export interface SituationReportResponse {
  analysis_timestamp: string;
  aoi_name: string;
  data_sources: string[];
  is_hypothetical_scenario: boolean;
  summary_metrics: Record<string, any>;
  english_report: string;
  nepali_report: string;
  uncertainty_statement: string;
}

export type AppViewMode = 'globe' | 'analysis';

export interface GlobeMarker {
  id: string;
  name: string;
  region: string;
  country: string;
  lat: number;
  lon: number;
  status: 'primary_active' | 'illustrative_planned';
  eventDate?: string;
  description: string;
  terrainStatus: string;
  infrastructureStatus: string;
  satelliteStatus: string;
  aoiId?: string;
}

export interface GlobeCameraPreset {
  id: string;
  label: string;
  lat: number;
  lon: number;
  distance: number;
}

export interface SarFloodCandidatesResponse {
  available: boolean;
  message?: string;
  summary?: {
    metadata: {
      analysis_type: string;
      study_area: string;
      aoi_bbox: number[];
      pre_event_product: string;
      pre_event_date: string;
      post_event_product: string;
      post_event_date: string;
      polarization: string;
      orbit: string;
      temporal_baseline_days: number;
      grid_resolution_m: number;
      crs: string;
      calibration: string;
      speckle_filter: string;
      dem_topographic_filter: string;
      change_threshold_db: string;
      permanent_water_exclusion: string;
      pipeline_version?: string;
      area_calculation_method?: string;
      generated_at: string;
    };
    results: {
      candidate_flood_area_km2: number;
      permanent_water_area_km2: number;
      candidate_flood_pixel_count: number;
      infrastructure_exposure: {
        exposed_road_length_km: number;
        total_mapped_road_km: number;
        exposed_bridges_count: number;
        total_mapped_bridges: number;
        exposed_buildings_count: number;
        total_mapped_buildings: number;
        exposed_clinics_count: number;
        total_mapped_clinics: number;
      };
    };
  };
  geojson?: Record<string, any>;
}


