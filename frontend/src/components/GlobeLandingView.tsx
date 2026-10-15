import React, { useState } from 'react';
import { EarthGlobe } from './EarthGlobe';
import { GLOBE_MARKERS, GLOBE_CAMERA_PRESETS } from '../data/globeLocations';
import { GlobeMarker, SarFloodCandidatesResponse } from '../types';
import {
  Satellite,
  Compass,
  ArrowRight,
  Database,
  Mountain,
  Building2,
  AlertCircle
} from 'lucide-react';

interface GlobeLandingViewProps {
  onEnterAnalysis: (aoiId: string) => void;
  sarData?: SarFloodCandidatesResponse | null;
}

export const GlobeLandingView: React.FC<GlobeLandingViewProps> = ({ onEnterAnalysis, sarData }) => {
  const [selectedMarkerId, setSelectedMarkerId] = useState<string>('trishuli_nepal');

  const handleSelectMarker = (marker: GlobeMarker) => {
    setSelectedMarkerId(marker.id);
  };

  const handleExploreAoi = (aoiId: string) => {
    onEnterAnalysis(aoiId);
  };

  return (
    <div className="relative w-full h-[calc(100vh-73px)] min-h-[680px] bg-slate-950 flex flex-col overflow-hidden">
      {/* Cinematic Top Sub-Banner: Spaceborne Flood Intelligence Context */}
      <div className="bg-slate-900/90 border-b border-slate-800 px-6 py-2.5 flex flex-wrap items-center justify-between gap-3 text-xs z-10">
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-2 text-sky-400 font-semibold">
            <Compass className="w-4 h-4 text-sky-400 animate-pulse" />
            <span>Interactive Spaceborne Reconnaissance</span>
          </div>
          <span className="text-slate-600 hidden sm:inline">|</span>
          <span className="text-slate-300 hidden md:inline">
            August 26, 2026 Trishuli Flood Event (Nuwakot &amp; Rasuwa, Nepal)
          </span>
        </div>

        <div className="flex items-center space-x-4">
          {sarData?.available ? (
            <div className="flex items-center space-x-1.5 text-cyan-300 bg-cyan-950/60 border border-cyan-800/80 px-2.5 py-0.5 rounded text-[11px]">
              <Satellite className="w-3.5 h-3.5 text-cyan-400" />
              <span>Sentinel-1 SAR Analysis Available</span>
            </div>
          ) : (
            <div className="flex items-center space-x-1.5 text-amber-300 bg-amber-950/60 border border-amber-800/80 px-2.5 py-0.5 rounded text-[11px]">
              <AlertCircle className="w-3.5 h-3.5 text-amber-400" />
              <span>Sentinel-1 SAR Pending Acquisition</span>
            </div>
          )}

          <button
            onClick={() => onEnterAnalysis('trishuli_nepal')}
            className="px-3.5 py-1 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-semibold text-xs flex items-center space-x-1.5 transition shadow-sm"
          >
            <span>Open Detailed Analysis Dashboard</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Main 3D Earth Globe Canvas Area */}
      <div className="relative flex-1 w-full h-full">
        <EarthGlobe
          markers={GLOBE_MARKERS}
          presets={GLOBE_CAMERA_PRESETS}
          selectedMarkerId={selectedMarkerId}
          onSelectMarker={handleSelectMarker}
          onExploreAoi={handleExploreAoi}
          sarAvailable={sarData?.available}
        />

        {/* Floating Right Context Drawer: Geospatial Readiness Checklist */}
        <div className="absolute top-6 right-16 hidden lg:flex flex-col w-80 bg-slate-900/90 backdrop-blur-md p-4 rounded-2xl border border-slate-800/90 shadow-2xl space-y-3 z-10 pointer-events-auto">
          <div className="flex items-center space-x-2 border-b border-slate-800 pb-2.5">
            <Database className="w-4 h-4 text-sky-400" />
            <h4 className="font-semibold text-xs text-slate-200">Spaceborne Data Readiness</h4>
          </div>

          <div className="space-y-2 text-xs">
            <div className="p-2.5 rounded-xl bg-slate-950/70 border border-slate-800 space-y-1">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-slate-200 flex items-center gap-1.5">
                  <Mountain className="w-3.5 h-3.5 text-emerald-400" />
                  Copernicus DEM GLO-30
                </span>
                <span className="text-[10px] px-1.5 py-0.2 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 font-medium">
                  Active Mosaic
                </span>
              </div>
              <p className="text-[11px] text-slate-400 leading-snug">
                100% geometric AOI coverage merged across N27E085 &amp; N28E085 tiles (454m - 1200m elevation profile).
              </p>
            </div>

            <div className="p-2.5 rounded-xl bg-slate-950/70 border border-slate-800 space-y-1">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-slate-200 flex items-center gap-1.5">
                  <Building2 className="w-3.5 h-3.5 text-sky-400" />
                  OpenStreetMap Baseline
                </span>
                <span className="text-[10px] px-1.5 py-0.2 rounded bg-sky-950 text-sky-400 border border-sky-800 font-medium">
                  Cached Real Data
                </span>
              </div>
              <p className="text-[11px] text-slate-400 leading-snug">
                301,586 elements verified: 56k+ buildings, 370 road segments, 60 bridges, and clinics.
              </p>
            </div>

            <div className="p-2.5 rounded-xl bg-slate-950/70 border border-slate-800 space-y-1">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-slate-200 flex items-center gap-1.5">
                  <Satellite className={`w-3.5 h-3.5 ${sarData?.available ? 'text-cyan-400' : 'text-amber-400'}`} />
                  Sentinel-1 C-SAR Radar
                </span>
                {sarData?.available ? (
                  <span className="text-[10px] px-1.5 py-0.2 rounded bg-cyan-950 text-cyan-400 border border-cyan-800 font-medium">
                    Analysis Available
                  </span>
                ) : (
                  <span className="text-[10px] px-1.5 py-0.2 rounded bg-amber-950 text-amber-400 border border-amber-800 font-medium">
                    Pending Pass
                  </span>
                )}
              </div>
              <p className="text-[11px] text-slate-400 leading-snug">
                {sarData?.available && sarData.summary ? (
                  <span>
                    Sentinel-1 SAR bitemporal change analysis available: {sarData.summary.results.candidate_flood_area_km2.toFixed(2)} km² candidate inundation zone detected (Aug 16 vs 28).
                  </span>
                ) : (
                  <span>
                    Catalog discovered 8 candidate products. Downlink credentials required for SAR change detection.
                  </span>
                )}
              </p>
            </div>
          </div>

          <div className="pt-1">
            <button
              onClick={() => onEnterAnalysis('trishuli_nepal')}
              className="w-full py-2 px-3 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-semibold text-sky-300 flex items-center justify-center space-x-1.5 transition"
            >
              <span>Launch Trishuli Analysis →</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
