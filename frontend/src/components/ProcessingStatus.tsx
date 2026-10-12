import React from 'react';
import { CheckCircle2, Clock, Activity, AlertCircle } from 'lucide-react';

export interface Stage {
  id: string;
  name: string;
  status: 'idle' | 'running' | 'completed' | 'failed';
  detail: string;
}

interface ProcessingStatusProps {
  stages: Stage[];
}

export const ProcessingStatus: React.FC<ProcessingStatusProps> = ({ stages }) => {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center space-x-2">
          <Activity className="w-5 h-5 text-sky-400" />
          <h2 className="font-semibold text-slate-200">Processing Pipeline Status</h2>
        </div>
        <span className="text-[11px] text-slate-400">Milestone 1 Foundation</span>
      </div>

      <div className="space-y-2.5">
        {stages.map((stage) => {
          let badge = (
            <span className="flex items-center text-slate-500 text-xs">
              <Clock className="w-3.5 h-3.5 mr-1" />
              Idle
            </span>
          );

          if (stage.status === 'running') {
            badge = (
              <span className="flex items-center text-sky-400 text-xs font-medium animate-pulse">
                <span className="w-2 h-2 rounded-full bg-sky-400 mr-1.5" />
                Processing
              </span>
            );
          } else if (stage.status === 'completed') {
            badge = (
              <span className="flex items-center text-emerald-400 text-xs font-medium">
                <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
                Done
              </span>
            );
          } else if (stage.status === 'failed') {
            badge = (
              <span className="flex items-center text-rose-400 text-xs font-medium">
                <AlertCircle className="w-3.5 h-3.5 mr-1" />
                Error
              </span>
            );
          }

          return (
            <div
              key={stage.id}
              className="flex items-center justify-between p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80 text-xs"
            >
              <div>
                <span className="font-medium text-slate-300">{stage.name}</span>
                <p className="text-[11px] text-slate-500">{stage.detail}</p>
              </div>
              <div>{badge}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
