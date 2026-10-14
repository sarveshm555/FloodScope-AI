import React from 'react';
import { Building2, Navigation, Anchor, ShieldAlert, Mountain, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { TerrainAnalysisResponse, InfrastructureExposureSummary } from '../types';

interface SummaryPanelProps {
  terrainData?: TerrainAnalysisResponse | null;
  exposureData?: InfrastructureExposureSummary | null;
  isScenarioMode?: boolean;
}

export const SummaryPanel: React.FC<SummaryPanelProps> = ({
  terrainData,
  exposureData,
  isScenarioMode = false,
}) => {
  if (!terrainData && !exposureData) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
        <div className="flex items-center space-x-2 border-b border-slate-800 pb-3">
          <ShieldAlert className="w-5 h-5 text-sky-400" />
          <h2 className="font-semibold text-slate-200">Infrastructure Exposure Summary</h2>
        </div>
        <div className="bg-slate-950/70 border border-dashed border-slate-800 rounded-lg p-6 text-center space-y-3">
          <p className="text-xs text-slate-400">
            Click <strong>"Run Analysis Pipeline"</strong> above to calculate real terrain topography from the Copernicus DEM and compute infrastructure exposure from OpenStreetMap.
          </p>
        </div>
      </div>
    );
  }

  const stats = terrainData?.statistics;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-5">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center space-x-2">
          <ShieldAlert className="w-5 h-5 text-sky-400" />
          <h2 className="font-semibold text-slate-200">Topography &amp; Infrastructure Exposure</h2>
        </div>
        {isScenarioMode && (
          <span className="flex items-center gap-1 text-[10px] bg-amber-950/60 text-amber-300 border border-amber-800 px-2 py-0.5 rounded">
            <AlertTriangle className="w-3 h-3 text-amber-400" />
            Hypothetical Model
          </span>
        )}
      </div>

      {/* Real Topography Section */}
      {stats && (
        <div className="space-y-2">
          <div className="flex items-center space-x-1.5 text-xs font-semibold text-slate-300">
            <Mountain className="w-4 h-4 text-emerald-400" />
            <span>Copernicus DEM GLO-30 Terrain Baseline (Real)</span>
          </div>
          <div className="grid grid-cols-3 gap-2.5 text-xs">
            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
              <span className="text-slate-400 text-[11px]">Elevation Range</span>
              <div className="text-base font-bold text-slate-200 mt-0.5">
                {stats.elevation_min_m}m - {stats.elevation_max_m}m
              </div>
              <span className="text-[10px] text-slate-500">Mean: {stats.elevation_mean_m}m</span>
            </div>
            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
              <span className="text-slate-400 text-[11px]">Mean Slope</span>
              <div className="text-base font-bold text-slate-200 mt-0.5">{stats.slope_mean_deg}°</div>
              <span className="text-[10px] text-slate-500">Max: {stats.slope_max_deg}°</span>
            </div>
            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
              <span className="text-slate-400 text-[11px]">Valley Basin Floor</span>
              <div className="text-base font-bold text-emerald-400 mt-0.5">{stats.valley_candidate_area_km2} km²</div>
              <span className="text-[10px] text-slate-500">Slope ≤ 5° &amp; Elev ≤ 800m</span>
            </div>
          </div>
        </div>
      )}

      {/* Exposure Metrics Section */}
      {exposureData && (
        <div className="space-y-2">
          <div className="flex items-center space-x-1.5 text-xs font-semibold text-slate-300">
            <Building2 className="w-4 h-4 text-sky-400" />
            <span>Infrastructure Spatial Intersections (OSM Data)</span>
          </div>
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
              <span className="text-slate-400 flex items-center gap-1.5">
                <Navigation className="w-3.5 h-3.5 text-amber-400" />
                Potentially Inundated Roads
              </span>
              <div className="text-xl font-bold text-amber-400 mt-1">
                {exposureData.exposed_road_length_km} km
              </div>
              <span className="text-[10px] text-slate-500">
                {exposureData.exposed_road_percent}% of {exposureData.total_road_length_km} km mapped
              </span>
            </div>

            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
              <span className="text-slate-400 flex items-center gap-1.5">
                <Anchor className="w-3.5 h-3.5 text-rose-400" />
                Bridges in Flood Footprint
              </span>
              <div className="text-xl font-bold text-rose-400 mt-1">
                {exposureData.exposed_bridges_count} / {exposureData.total_bridges_mapped}
              </div>
              <span className="text-[10px] text-slate-500">Potentially submerged / severed</span>
            </div>

            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
              <span className="text-slate-400 flex items-center gap-1.5">
                <Building2 className="w-3.5 h-3.5 text-rose-300" />
                Exposed Buildings
              </span>
              <div className="text-xl font-bold text-rose-300 mt-1">
                {exposureData.exposed_buildings_count}
              </div>
              <span className="text-[10px] text-slate-500">
                {exposureData.exposed_buildings_percent}% of {exposureData.total_buildings_mapped} mapped
              </span>
            </div>

            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
              <span className="text-slate-400 flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-sky-400" />
                Health Clinics Exposed
              </span>
              <div className="text-xl font-bold text-sky-300 mt-1">
                {exposureData.exposed_health_facilities_count} / {exposureData.health_facilities_mapped}
              </div>
              <span className="text-[10px] text-slate-500">Hospitals &amp; health clinics</span>
            </div>
          </div>
        </div>
      )}

      {/* Ground Truth & Disclaimer Banner */}
      <div className="p-3 bg-slate-950/80 rounded-lg border border-slate-800 text-[11px] text-slate-400 space-y-1">
        <p className="font-semibold text-slate-300">Methodological Transparency Notice:</p>
        <p>
          Calculations reflect spatial intersection between pre-event OpenStreetMap features and a hydro-topographic flood scenario on verified Copernicus DEM terrain.
          <strong className="text-amber-400 font-normal"> Intersections represent potential water inundation exposure, not confirmed structural destruction.</strong>
        </p>
      </div>
    </div>
  );
};
