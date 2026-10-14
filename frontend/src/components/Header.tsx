import React from 'react';
import { BackendHealth, AppViewMode } from '../types';
import { Waves, Satellite, CheckCircle2, AlertTriangle, ShieldCheck, Globe, Activity } from 'lucide-react';

interface HeaderProps {
  health: BackendHealth | null;
  loading: boolean;
  error: string | null;
  currentView: AppViewMode;
  onViewChange: (view: AppViewMode) => void;
}

export const Header: React.FC<HeaderProps> = ({
  health,
  loading,
  error,
  currentView,
  onViewChange,
}) => {
  return (
    <header className="border-b border-slate-800 bg-slate-900/95 backdrop-blur px-6 py-3.5 flex flex-wrap items-center justify-between gap-4 sticky top-0 z-30">
      <div className="flex items-center space-x-4">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 bg-sky-600/20 text-sky-400 rounded-lg border border-sky-500/30">
            <Waves className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-xl font-bold tracking-tight text-white">FloodScope AI</h1>
              <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-sky-950 text-sky-400 border border-sky-800">
                Track B: Spaceborne Flood Intelligence
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Geospatial flood intelligence prototype: Copernicus DEM terrain &amp; OSM infrastructure (Sentinel-1 SAR pending acquisition)
            </p>
          </div>
        </div>

        {/* View Switcher: 3D Earth Globe vs Analysis Dashboard */}
        <div className="bg-slate-950/80 border border-slate-700/80 p-1 rounded-xl flex items-center space-x-1 shadow-inner ml-2">
          <button
            onClick={() => onViewChange('globe')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition ${
              currentView === 'globe'
                ? 'bg-sky-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
          >
            <Globe className="w-3.5 h-3.5" />
            <span>3D Earth Overview</span>
          </button>
          <button
            onClick={() => onViewChange('analysis')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition ${
              currentView === 'analysis'
                ? 'bg-sky-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
          >
            <Activity className="w-3.5 h-3.5" />
            <span>Flood Analysis</span>
          </button>
        </div>
      </div>

      <div className="flex items-center space-x-3 text-xs">
        {/* Backend Status Pill */}
        <div className="flex items-center space-x-2 px-3 py-1.5 rounded-md bg-slate-800/80 border border-slate-700">
          {loading ? (
            <span className="flex items-center text-slate-400">
              <span className="w-2 h-2 rounded-full bg-slate-500 animate-pulse mr-1.5" />
              Connecting API...
            </span>
          ) : error ? (
            <span className="flex items-center text-rose-400">
              <AlertTriangle className="w-3.5 h-3.5 mr-1.5 text-rose-400" />
              API Disconnected
            </span>
          ) : health ? (
            <span className="flex items-center text-emerald-400 font-medium">
              <CheckCircle2 className="w-3.5 h-3.5 mr-1.5 text-emerald-400" />
              API v{health.backend_version} ({health.status})
            </span>
          ) : null}
        </div>

        {/* Copilot Provider Indicator */}
        <div className="flex items-center space-x-1.5 px-3 py-1.5 rounded-md bg-slate-800/80 border border-slate-700 text-slate-300">
          <ShieldCheck className="w-3.5 h-3.5 text-indigo-400" />
          <span>Copilot Mode:</span>
          {health?.services.llm_provider_configured ? (
            <span className="text-indigo-300 font-semibold uppercase">{health.services.llm_provider_name || 'LLM'}</span>
          ) : (
            <span className="text-amber-400 font-medium">Deterministic Rule Fallback</span>
          )}
        </div>

        {/* CDSE Status Indicator */}
        <div className="flex items-center space-x-1.5 px-3 py-1.5 rounded-md bg-slate-800/80 border border-slate-700 text-slate-300">
          <Satellite className="w-3.5 h-3.5 text-sky-400" />
          <span>Copernicus Catalog:</span>
          <span className="text-emerald-400 font-medium">Open Query Ready</span>
        </div>
      </div>
    </header>
  );
};
