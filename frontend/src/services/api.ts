import { BackendHealth } from '../types';

const API_BASE = import.meta.env.VITE_API_URL || '';

export async function fetchHealth(): Promise<BackendHealth> {
  const response = await fetch(`${API_BASE}/api/health`);
  if (!response.ok) {
    throw new Error(`Health check failed with status: ${response.status}`);
  }
  return response.json();
}
