import React from 'react';
import { AreaOfInterest } from '../types';
import { MapPin, Calendar, Radio, Info } from 'lucide-react';

export const PILOT_AREAS: AreaOfInterest[] = [
  {
    id: 'trishuli_nepal',
    name: 'Trishuli Basin & Highway Corridor',
    region: 'Nuwakot & Rasuwa Districts',
    country: 'Nepal',
    bbox: [85.00, 27.80, 85.35, 28.15],
    defaultDate: '2026-08-26',
  },
  {
    id: 'custom_bbox',
    name: 'Custom Bounding Box',
    region: 'User Defined Area',
    country: 'Custom',
    bbox: [85.00, 27.80, 85.35, 28.15],
    defaultDate: '2026-08-26',
  }
];

interface AreaSelectorProps {
  selectedArea: AreaOfInterest;
  onSelectArea: (area: AreaOfInterest) => void;
  eventDate: string;
  onDateChange: (date: string) => void;
  onDiscover: () => void;
  discovering: boolean;
}

export const AreaSelector: React.FC<AreaSelectorProps> = ({
  selectedArea,
  onSelectArea,
  eventDate,
  onDateChange,
  onDiscover,
  discovering,
}) => {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-5">
      <div className="flex items-center space-x-2 border-b border-slate-800 pb-3">
        <MapPin className="w-5 h-5 text-sky-400" />
        <h2 className="font-semibold text-slate-200">Disaster Analysis Configuration</h2>
      </div>

      <div className="space-y-4">
        {/* Geographic Area */}
        <div>
          <label className="block text-xs font-medium text-slate-400 mb-1.5">
            Geographic Region / Case Study
          </label>
          <select
            value={selectedArea.id}
            onChange={(e) => {
              const found = PILOT_AREAS.find((a) => a.id === e.target.value);
              if (found) onSelectArea(found);
            }}
            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-sky-500"
          >
            {PILOT_AREAS.map((area) => (
              <option key={area.id} value={area.id}>
                {area.name} ({area.region}, {area.country})
              </option>
            ))}
          </select>
          <p className="mt-1 text-[11px] text-slate-500">
            Coordinates: [{selectedArea.bbox.join(', ')}]
          </p>
        </div>

        {/* Flood Event Date */}
        <div>
          <label className="block text-xs font-medium text-slate-400 mb-1.5 flex items-center gap-1.5">
            <Calendar className="w-3.5 h-3.5 text-sky-400" />
            Flood Event Date
          </label>
          <input
            type="date"
            value={eventDate}
            onChange={(e) => onDateChange(e.target.value)}
            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-sky-500"
          />
          <p className="mt-1 text-[11px] text-slate-500">
            Trishuli benchmark flood event: August 26, 2026
          </p>
        </div>

        {/* Satellite Constellations */}
        <div className="pt-2 border-t border-slate-800">
          <label className="block text-xs font-medium text-slate-400 mb-2 flex items-center gap-1.5">
            <Radio className="w-3.5 h-3.5 text-sky-400" />
            Sensors &amp; Input Requirements
          </label>
          <div className="space-y-2 text-xs">
            <div className="flex items-center justify-between p-2 rounded-lg bg-slate-800/60 border border-slate-700/60">
              <span className="text-slate-300">Sentinel-1 C-SAR (IW GRD)</span>
              <span className="text-[10px] font-semibold bg-emerald-950 text-emerald-400 border border-emerald-800 px-2 py-0.5 rounded">
                Primary (All-weather)
              </span>
            </div>
            <div className="flex items-center justify-between p-2 rounded-lg bg-slate-800/40 border border-slate-800">
              <span className="text-slate-400">Sentinel-2 Optical (MSI)</span>
              <span className="text-[10px] bg-slate-800 text-slate-400 px-2 py-0.5 rounded">
                Optional (Cloud-checked)
              </span>
            </div>
            <div className="flex items-center justify-between p-2 rounded-lg bg-slate-800/40 border border-slate-800">
              <span className="text-slate-400">Copernicus WorldDEM-30</span>
              <span className="text-[10px] bg-sky-950 text-sky-400 border border-sky-800 px-2 py-0.5 rounded">
                Terrain Reference
              </span>
            </div>
          </div>
        </div>

        {/* Discovery Action Button */}
        <div className="pt-2">
          <button
            onClick={onDiscover}
            disabled={discovering}
            className="w-full py-2.5 px-4 bg-sky-600 hover:bg-sky-500 disabled:bg-slate-800 text-white font-medium rounded-lg text-sm transition flex items-center justify-center space-x-2 shadow-md shadow-sky-900/30"
          >
            {discovering ? (
              <>
                <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                <span>Querying Copernicus Catalog...</span>
              </>
            ) : (
              <span>Discover Satellite Observations</span>
            )}
          </button>
        </div>

        {/* Compliance Notice */}
        <div className="p-3 bg-amber-950/30 border border-amber-800/40 rounded-lg text-[11px] text-amber-300/90 flex gap-2">
          <Info className="w-4 h-4 shrink-0 text-amber-400 mt-0.5" />
          <span>
            <strong>Data Rule Compliance:</strong> Only pre-event OSM data (July 27, 2026 snapshot) and actual satellite orbits are permitted. Official damage maps (EMSR927) are strictly reserved for post-analysis validation.
          </span>
        </div>
      </div>
    </div>
  );
};
