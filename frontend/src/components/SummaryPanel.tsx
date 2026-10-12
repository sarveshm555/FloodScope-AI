import React from 'react';
import { Building2, Navigation, Anchor, AlertCircle, ShieldAlert, Clock } from 'lucide-react';

interface SummaryPanelProps {
  analysisRun: boolean;
}

export const SummaryPanel: React.FC<SummaryPanelProps> = ({ analysisRun }) => {
  if (!analysisRun) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
        <div className="flex items-center space-x-2 border-b border-slate-800 pb-3">
          <ShieldAlert className="w-5 h-5 text-sky-400" />
          <h2 className="font-semibold text-slate-200">Infrastructure Exposure Summary</h2>
        </div>

        {/* Empty State Banner */}
        <div className="bg-slate-950/70 border border-dashed border-slate-800 rounded-lg p-6 text-center space-y-3">
          <div className="inline-flex p-3 rounded-full bg-slate-900 border border-slate-800 text-slate-400">
            <Clock className="w-6 h-6 text-sky-400 animate-pulse" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-300">Awaiting Pipeline Execution</h3>
            <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
              No analysis has run yet. Satellite radar observations must be retrieved and cross-referenced with pre-event OpenStreetMap vectors.
            </p>
          </div>
        </div>

        {/* Metric Placeholders showing explicit Unavailable/Pending */}
        <div className="grid grid-cols-2 gap-3 text-xs">
          <div className="p-3 bg-slate-950/50 rounded-lg border border-slate-800/80">
            <span className="text-slate-400 flex items-center gap-1.5">
              <AlertCircle className="w-3.5 h-3.5 text-sky-400" />
              Candidate Flood Extent
            </span>
            <div className="text-lg font-bold text-slate-500 mt-1">Pending</div>
            <span className="text-[10px] text-slate-600">Requires Sentinel-1 SAR pair</span>
          </div>

          <div className="p-3 bg-slate-950/50 rounded-lg border border-slate-800/80">
            <span className="text-slate-400 flex items-center gap-1.5">
              <Building2 className="w-3.5 h-3.5 text-rose-400" />
              Potentially Exposed Buildings
            </span>
            <div className="text-lg font-bold text-slate-500 mt-1">Pending</div>
            <span className="text-[10px] text-slate-600">Spatial intersection count</span>
          </div>

          <div className="p-3 bg-slate-950/50 rounded-lg border border-slate-800/80">
            <span className="text-slate-400 flex items-center gap-1.5">
              <Navigation className="w-3.5 h-3.5 text-amber-400" />
              Potentially Affected Roads
            </span>
            <div className="text-lg font-bold text-slate-500 mt-1">Pending</div>
            <span className="text-[10px] text-slate-600">Kilometers / segments intersected</span>
          </div>

          <div className="p-3 bg-slate-950/50 rounded-lg border border-slate-800/80">
            <span className="text-slate-400 flex items-center gap-1.5">
              <Anchor className="w-3.5 h-3.5 text-emerald-400" />
              Potentially Exposed Bridges
            </span>
            <div className="text-lg font-bold text-slate-500 mt-1">Pending</div>
            <span className="text-[10px] text-slate-600">Critical crossing points</span>
          </div>
        </div>

        <div className="text-[11px] text-slate-500 italic border-t border-slate-800 pt-3">
          Note: Exposure does not imply confirmed structural destruction. Field validation and hydrodynamic parameters are required for definitive damage classification.
        </div>
      </div>
    );
  }

  return null;
};
