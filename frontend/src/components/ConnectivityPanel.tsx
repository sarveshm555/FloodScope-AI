import React from 'react';
import { GitFork, Hospital, Home, Network, AlertTriangle, ShieldAlert } from 'lucide-react';
import { InfrastructureExposureSummary } from '../types';

interface ConnectivityPanelProps {
  exposureData?: InfrastructureExposureSummary | null;
}

export const ConnectivityPanel: React.FC<ConnectivityPanelProps> = ({ exposureData }) => {
  const isolated = exposureData?.isolated_settlements || [];

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center space-x-2">
          <Network className="w-5 h-5 text-indigo-400" />
          <h2 className="font-semibold text-slate-200">Settlement Road Connectivity</h2>
        </div>
        <span className="text-xs px-2 py-0.5 rounded bg-indigo-950 text-indigo-400 border border-indigo-800 font-mono text-[10px]">
          Topology Engine
        </span>
      </div>

      {!exposureData ? (
        <div className="space-y-4">
          <div className="bg-slate-950/70 border border-dashed border-slate-800 rounded-lg p-5 text-center">
            <GitFork className="w-6 h-6 text-indigo-400 mx-auto mb-2 animate-pulse" />
            <p className="text-xs text-slate-300 font-medium">Road Graph Reachability Model Idle</p>
            <p className="text-[11px] text-slate-500 mt-1 max-w-sm mx-auto">
              Pre-event road network topology will be intersected with candidate flood waters to test path existence between hillside settlements and destination facilities.
            </p>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Key Metric Highlights */}
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
              <span className="text-slate-400 flex items-center gap-1.5 text-[11px]">
                <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
                Severed / Flooded Bridges
              </span>
              <div className="text-xl font-bold text-amber-400 mt-1">
                {exposureData.exposed_bridges_count}
              </div>
              <span className="text-[10px] text-slate-500">
                Critical river crossings in flood zone
              </span>
            </div>

            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
              <span className="text-slate-400 flex items-center gap-1.5 text-[11px]">
                <Hospital className="w-3.5 h-3.5 text-emerald-400" />
                Emergency Health Reachability
              </span>
              <div className="text-xl font-bold text-emerald-400 mt-1">
                {exposureData.health_facilities_mapped - exposureData.exposed_health_facilities_count} / {exposureData.health_facilities_mapped}
              </div>
              <span className="text-[10px] text-slate-500">
                Facilities outside inundation zone
              </span>
            </div>
          </div>

          {/* List of at-risk settlements */}
          <div className="space-y-2">
            <h3 className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
              <ShieldAlert className="w-4 h-4 text-rose-400" />
              Settlements with Potential Cutoff Risk
            </h3>
            {isolated.length === 0 ? (
              <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 text-xs text-slate-400">
                No mapped settlement nodes intersect the flood extent or critical severed bridge zones.
              </div>
            ) : (
              <div className="space-y-1.5 max-h-56 overflow-y-auto pr-1">
                {isolated.map((s, idx) => (
                  <div
                    key={idx}
                    className="p-2.5 bg-slate-950 rounded border border-slate-800/80 flex items-center justify-between text-xs"
                  >
                    <div className="flex items-center space-x-2">
                      <Home className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" />
                      <span className="text-slate-200">{s}</span>
                    </div>
                    <span className="text-[10px] text-amber-400 bg-amber-950/50 px-1.5 py-0.5 rounded border border-amber-900">
                      Isolated Risk
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="p-3 rounded-lg bg-indigo-950/20 border border-indigo-900/40 text-[11px] text-indigo-300/80">
            <strong>Graph Connectivity Rule:</strong> Settlements are flagged as at-risk if their access roads or connecting bridge structures intersect the flood zone, preventing ground vehicular access to regional towns.
          </div>
        </div>
      )}
    </div>
  );
};
