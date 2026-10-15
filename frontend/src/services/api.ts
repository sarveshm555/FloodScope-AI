import {
  BackendHealth,
  CatalogSearchResponse,
  DataManifest,
  StorageStatus,
  TerrainAnalysisResponse,
  FloodScenarioResponse,
  InfrastructureExposureSummary,
  SituationReportResponse,
  SarFloodCandidatesResponse,
} from '../types';

const rawApiBase = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || '';
export const API_BASE = rawApiBase.replace(/\/+$/, '');

export function getApiBaseUrl(): string {
  return API_BASE || '(Local Proxy: http://127.0.0.1:8000)';
}

export async function fetchHealth(): Promise<BackendHealth> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/api/health`);
  } catch (err: any) {
    throw new Error(`Unable to connect to FloodScope backend API: ${err.message || 'Network unreachable'}`);
  }

  if (!response.ok) {
    if (response.status === 404) {
      throw new Error(
        'Backend service unreachable (404 Not Found). In production, configure VITE_API_BASE_URL in your environment. Locally, ensure the FastAPI server is running at http://127.0.0.1:8000.'
      );
    }
    throw new Error(`Health check failed with status: ${response.status}`);
  }
  return response.json();
}

export async function fetchDataManifest(): Promise<DataManifest> {
  const response = await fetch(`${API_BASE}/api/downloads/manifest`);
  if (!response.ok) {
    throw new Error(`Failed to load manifest: ${response.status}`);
  }
  return response.json();
}

export async function fetchStorageStatus(): Promise<StorageStatus> {
  const response = await fetch(`${API_BASE}/api/downloads/storage-status`);
  if (!response.ok) {
    throw new Error(`Failed to check storage status: ${response.status}`);
  }
  return response.json();
}

export interface CatalogSearchParams {
  bbox: [number, number, number, number];
  event_date: string;
  pre_days?: number;
  post_days?: number;
  include_sentinel_1?: boolean;
  include_sentinel_2?: boolean;
  orbit_direction?: string | null;
}

export async function searchSatelliteCatalog(
  params: CatalogSearchParams
): Promise<CatalogSearchResponse> {
  const response = await fetch(`${API_BASE}/api/catalog/search`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      bbox: params.bbox,
      event_date: params.event_date,
      pre_days: params.pre_days ?? 15,
      post_days: params.post_days ?? 15,
      include_sentinel_1: params.include_sentinel_1 ?? true,
      include_sentinel_2: params.include_sentinel_2 ?? true,
      orbit_direction: params.orbit_direction ?? null,
    }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    let detail = `Catalog search failed (${response.status})`;
    try {
      const parsed = JSON.parse(errorText);
      if (parsed.detail) detail = parsed.detail;
    } catch {
      // Keep fallback
    }
    throw new Error(detail);
  }

  return response.json();
}

export async function fetchTerrainAnalysis(
  bbox: [number, number, number, number],
  slopeThreshold: number = 5.0,
  elevationThreshold: number = 800.0
): Promise<TerrainAnalysisResponse> {
  const response = await fetch(`${API_BASE}/api/analysis/terrain`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      bbox,
      slope_threshold_deg: slopeThreshold,
      elevation_threshold_m: elevationThreshold,
    }),
  });
  if (!response.ok) {
    throw new Error(`Terrain analysis failed (${response.status})`);
  }
  return response.json();
}

export async function fetchFloodScenario(
  waterLevelM: number = 500.0,
  maxSlopeDeg: number = 8.0,
  bbox: [number, number, number, number] = [85.10, 27.85, 85.25, 28.05]
): Promise<FloodScenarioResponse> {
  const response = await fetch(`${API_BASE}/api/analysis/scenario`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      water_level_m: waterLevelM,
      max_slope_deg: maxSlopeDeg,
      aoi_bbox: bbox,
    }),
  });
  if (!response.ok) {
    throw new Error(`Scenario generation failed (${response.status})`);
  }
  return response.json();
}

export async function fetchOsmInfrastructure(
  bbox: [number, number, number, number] = [85.10, 27.85, 85.25, 28.05]
): Promise<Record<string, any>> {
  const [w, s, e, n] = bbox;
  const response = await fetch(`${API_BASE}/api/analysis/osm-infrastructure?w=${w}&s=${s}&e=${e}&n=${n}`);
  if (!response.ok) {
    throw new Error(`OSM fetch failed (${response.status})`);
  }
  return response.json();
}

export async function fetchExposureSummary(
  waterLevelM: number = 500.0,
  maxSlopeDeg: number = 8.0
): Promise<InfrastructureExposureSummary> {
  const response = await fetch(
    `${API_BASE}/api/analysis/exposure?water_level_m=${waterLevelM}&max_slope_deg=${maxSlopeDeg}`,
    { method: 'POST' }
  );
  if (!response.ok) {
    throw new Error(`Exposure calculation failed (${response.status})`);
  }
  return response.json();
}

export async function fetchSituationReport(
  waterLevelM: number = 500.0,
  maxSlopeDeg: number = 8.0
): Promise<SituationReportResponse> {
  const response = await fetch(
    `${API_BASE}/api/analysis/situation-report?water_level_m=${waterLevelM}&max_slope_deg=${maxSlopeDeg}`,
    { method: 'POST' }
  );
  if (!response.ok) {
    throw new Error(`Report generation failed (${response.status})`);
  }
  return response.json();
}

export async function fetchSarFloodCandidates(): Promise<SarFloodCandidatesResponse> {
  const response = await fetch(`${API_BASE}/api/analysis/sar-flood-candidates`);
  if (!response.ok) {
    throw new Error(`Failed to load SAR flood candidates (${response.status})`);
  }
  return response.json();
}

