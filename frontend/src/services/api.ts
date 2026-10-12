import { BackendHealth, CatalogSearchResponse } from '../types';

const API_BASE = import.meta.env.VITE_API_URL || '';

export async function fetchHealth(): Promise<BackendHealth> {
  const response = await fetch(`${API_BASE}/api/health`);
  if (!response.ok) {
    throw new Error(`Health check failed with status: ${response.status}`);
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
