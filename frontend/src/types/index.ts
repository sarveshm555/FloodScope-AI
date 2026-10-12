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

export interface AnalysisState {
  status: 'idle' | 'discovering' | 'downloading' | 'processing' | 'completed' | 'failed';
  selectedArea: AreaOfInterest;
  eventDate: string;
  activeTab: 'summary' | 'connectivity' | 'copilot' | 'layers';
}
