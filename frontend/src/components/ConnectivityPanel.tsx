import { GitFork, Hospital, Home, Network } from 'lucide-react';

interface ConnectivityPanelProps {
  analysisRun: boolean;
}

export const ConnectivityPanel: React.FC<ConnectivityPanelProps> = ({ analysisRun }) => {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center space-x-2">
          <Network className="w-5 h-5 text-indigo-400" />
          <h2 className="font-semibold text-slate-200">Settlement Road Connectivity</h2>
        </div>
        <span className="text-xs px-2 py-0.5 rounded bg-indigo-950 text-indigo-400 border border-indigo-800">
          NetworkX Graph Engine
        </span>
      </div>

      {!analysisRun ? (
        <div className="space-y-4">
          <div className="bg-slate-950/70 border border-dashed border-slate-800 rounded-lg p-5 text-center">
            <GitFork className="w-6 h-6 text-indigo-400 mx-auto mb-2 animate-pulse" />
            <p className="text-xs text-slate-300 font-medium">Road Graph Reachability Model Idle</p>
            <p className="text-[11px] text-slate-500 mt-1 max-w-sm mx-auto">
              Pre-event road network topology will be intersected with candidate flood waters to test path existence between hillside settlements and destination facilities.
            </p>
          </div>

          <div className="space-y-2 text-xs">
            <div className="p-3 bg-slate-950/50 rounded-lg border border-slate-800/80 flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Hospital className="w-4 h-4 text-emerald-400" />
                <span className="text-slate-300">Nuwakot District Hospital</span>
              </div>
              <span className="text-slate-500">Route Status: Pending</span>
            </div>

            <div className="p-3 bg-slate-950/50 rounded-lg border border-slate-800/80 flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Home className="w-4 h-4 text-sky-400" />
                <span className="text-slate-300">Bidur Central Market</span>
              </div>
              <span className="text-slate-500">Route Status: Pending</span>
            </div>
          </div>

          <div className="p-3 rounded-lg bg-indigo-950/20 border border-indigo-900/40 text-[11px] text-indigo-300/80">
            <strong>Graph Methodology Rule:</strong> Settlements are only flagged as isolated if no alternative non-flooded road edge exists within the topologically connected graph component.
          </div>
        </div>
      ) : null}
    </div>
  );
};
