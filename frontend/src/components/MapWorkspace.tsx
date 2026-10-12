import React, { useEffect, useRef, useState } from 'react';
import maplibregl from 'maplibre-gl';
import { AreaOfInterest } from '../types';
import { Layers, Eye, EyeOff, Map } from 'lucide-react';

interface MapWorkspaceProps {
  selectedArea: AreaOfInterest;
}

interface MapLayer {
  id: string;
  name: string;
  category: 'satellite' | 'flood' | 'infrastructure';
  color: string;
  enabled: boolean;
  available: boolean;
}

export const MapWorkspace: React.FC<MapWorkspaceProps> = ({ selectedArea }) => {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapInstance = useRef<maplibregl.Map | null>(null);
  const [layers, setLayers] = useState<MapLayer[]>([
    { id: 's1_pre', name: 'Pre-Event SAR (Aug 16)', category: 'satellite', color: '#64748b', enabled: true, available: false },
    { id: 's1_post', name: 'Post-Event SAR (Aug 28)', category: 'satellite', color: '#38bdf8', enabled: true, available: false },
    { id: 'flood_extent', name: 'Candidate Flood Extent', category: 'flood', color: '#0284c7', enabled: true, available: false },
    { id: 'change_areas', name: 'Potential Surface Change', category: 'flood', color: '#f59e0b', enabled: false, available: false },
    { id: 'osm_buildings', name: 'Pre-event Buildings (OSM)', category: 'infrastructure', color: '#ef4444', enabled: true, available: false },
    { id: 'osm_roads', name: 'Pre-event Road Network', category: 'infrastructure', color: '#e2e8f0', enabled: true, available: false },
    { id: 'osm_bridges', name: 'River Bridges', category: 'infrastructure', color: '#10b981', enabled: true, available: false },
  ]);

  useEffect(() => {
    if (!mapContainer.current || mapInstance.current) return;

    // Center of Trishuli Valley
    const [minLon, minLat, maxLon, maxLat] = selectedArea.bbox;
    const centerLon = (minLon + maxLon) / 2;
    const centerLat = (minLat + maxLat) / 2;

    const map = new maplibregl.Map({
      container: mapContainer.current,
      style: {
        version: 8,
        sources: {
          'osm-tiles': {
            type: 'raster',
            tiles: [
              'https://a.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}@2x.png',
              'https://b.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}@2x.png'
            ],
            tileSize: 256,
            attribution: '© OpenStreetMap contributors, © CARTO'
          }
        },
        layers: [
          {
            id: 'osm-layer',
            type: 'raster',
            source: 'osm-tiles',
            minzoom: 0,
            maxzoom: 19
          }
        ]
      },
      center: [centerLon, centerLat],
      zoom: 11,
    });

    map.addControl(new maplibregl.NavigationControl(), 'top-right');
    mapInstance.current = map;

    return () => {
      map.remove();
      mapInstance.current = null;
    };
  }, []);

  const toggleLayer = (id: string) => {
    setLayers(prev => prev.map(l => l.id === id ? { ...l, enabled: !l.enabled } : l));
  };

  return (
    <div className="relative w-full h-full min-h-[540px] bg-slate-950 rounded-xl overflow-hidden border border-slate-800 shadow-xl flex flex-col">
      {/* Map Header Bar */}
      <div className="absolute top-3 left-3 z-10 bg-slate-900/90 backdrop-blur px-3 py-1.5 rounded-lg border border-slate-700/80 shadow flex items-center space-x-2 text-xs">
        <Map className="w-4 h-4 text-sky-400" />
        <span className="font-semibold text-slate-200">{selectedArea.name}</span>
        <span className="text-slate-400">({selectedArea.region})</span>
      </div>

      {/* MapLibre DOM Node */}
      <div ref={mapContainer} className="w-full flex-1" />

      {/* Layer Control Drawer / Floating Legend */}
      <div className="absolute bottom-4 left-4 z-10 bg-slate-900/95 backdrop-blur p-3.5 rounded-xl border border-slate-700/80 shadow-2xl max-w-xs text-xs space-y-3">
        <div className="flex items-center justify-between border-b border-slate-800 pb-2">
          <div className="flex items-center space-x-1.5 font-semibold text-slate-200">
            <Layers className="w-4 h-4 text-sky-400" />
            <span>Map Layers &amp; Evidence</span>
          </div>
          <span className="text-[10px] text-slate-500">Awaiting Pipeline</span>
        </div>

        <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
          {layers.map((layer) => (
            <div
              key={layer.id}
              onClick={() => toggleLayer(layer.id)}
              className="flex items-center justify-between p-1.5 rounded hover:bg-slate-800/80 cursor-pointer transition"
            >
              <div className="flex items-center space-x-2">
                <span
                  className="w-2.5 h-2.5 rounded-full"
                  style={{ backgroundColor: layer.color }}
                />
                <span className={`text-[11px] ${layer.enabled ? 'text-slate-300' : 'text-slate-500 line-through'}`}>
                  {layer.name}
                </span>
              </div>
              <div className="flex items-center space-x-1">
                {!layer.available && (
                  <span className="text-[9px] px-1.5 py-0.2 rounded bg-slate-800 text-slate-400 border border-slate-700">
                    Pending
                  </span>
                )}
                {layer.enabled ? (
                  <Eye className="w-3.5 h-3.5 text-sky-400" />
                ) : (
                  <EyeOff className="w-3.5 h-3.5 text-slate-600" />
                )}
              </div>
            </div>
          ))}
        </div>

        <div className="pt-2 border-t border-slate-800 text-[10px] text-slate-400 leading-tight">
          Baseline map: OpenStreetMap tiles. Flood boundaries and exposed layers will appear upon processing execution.
        </div>
      </div>
    </div>
  );
};
