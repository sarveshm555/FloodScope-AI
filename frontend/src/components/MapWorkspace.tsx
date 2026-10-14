import React, { useEffect, useRef, useState, useCallback } from 'react';
import maplibregl from 'maplibre-gl';
import { AreaOfInterest } from '../types';
import { Layers, Eye, EyeOff, Map, AlertTriangle } from 'lucide-react';

interface MapWorkspaceProps {
  selectedArea: AreaOfInterest;
  terrainGeojson?: Record<string, any> | null;
  floodScenarioGeojson?: Record<string, any> | null;
  exposedRoadsGeojson?: Record<string, any> | null;
  exposedBridgesGeojson?: Record<string, any> | null;
  exposedBuildingsGeojson?: Record<string, any> | null;
  isScenarioMode?: boolean;
}

interface MapLayer {
  id: string;
  name: string;
  category: 'terrain' | 'scenario' | 'infrastructure';
  color: string;
  enabled: boolean;
  available: boolean;
}

export const MapWorkspace: React.FC<MapWorkspaceProps> = ({
  selectedArea,
  terrainGeojson,
  floodScenarioGeojson,
  exposedRoadsGeojson,
  exposedBridgesGeojson,
  exposedBuildingsGeojson,
  isScenarioMode = false,
}) => {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapInstance = useRef<maplibregl.Map | null>(null);
  const [mapLoaded, setMapLoaded] = useState<boolean>(false);

  const [layers, setLayers] = useState<MapLayer[]>([
    { id: 'aoi_boundary', name: 'Pilot AOI Bounding Box', category: 'terrain', color: '#38bdf8', enabled: true, available: true },
    { id: 'terrain_valleys', name: 'Valley Basins (Real DEM)', category: 'terrain', color: '#10b981', enabled: true, available: false },
    { id: 'flood_scenario', name: 'Hypothetical Flood Extent', category: 'scenario', color: '#0284c7', enabled: true, available: false },
    { id: 'exposed_roads', name: 'Exposed Roads (OSM)', category: 'infrastructure', color: '#f59e0b', enabled: true, available: false },
    { id: 'exposed_bridges', name: 'Exposed Bridges (OSM)', category: 'infrastructure', color: '#ef4444', enabled: true, available: false },
    { id: 'exposed_buildings', name: 'Exposed Buildings (OSM)', category: 'infrastructure', color: '#dc2626', enabled: false, available: false },
  ]);

  // Update availability based on incoming GeoJSON
  useEffect(() => {
    setLayers(prev => prev.map(l => {
      if (l.id === 'terrain_valleys') return { ...l, available: !!terrainGeojson };
      if (l.id === 'flood_scenario') return { ...l, available: !!floodScenarioGeojson };
      if (l.id === 'exposed_roads') return { ...l, available: !!exposedRoadsGeojson };
      if (l.id === 'exposed_bridges') return { ...l, available: !!exposedBridgesGeojson };
      if (l.id === 'exposed_buildings') return { ...l, available: !!exposedBuildingsGeojson };
      return l;
    }));
  }, [terrainGeojson, floodScenarioGeojson, exposedRoadsGeojson, exposedBridgesGeojson, exposedBuildingsGeojson]);

  // Helper to safely add or update GeoJSON source & layer
  const syncLayersToMap = useCallback(() => {
    const map = mapInstance.current;
    if (!map || !map.isStyleLoaded()) return;

    const updateGeojsonSource = (
      sourceId: string,
      layerId: string,
      type: 'fill' | 'line' | 'circle',
      data: any,
      paint: any
    ) => {
      if (!data || !data.features || data.features.length === 0) {
        if (map.getLayer(layerId)) map.removeLayer(layerId);
        if (map.getSource(sourceId)) map.removeSource(sourceId);
        return;
      }

      if (map.getSource(sourceId)) {
        (map.getSource(sourceId) as maplibregl.GeoJSONSource).setData(data);
      } else {
        map.addSource(sourceId, { type: 'geojson', data });
        map.addLayer({
          id: layerId,
          type: type as any,
          source: sourceId,
          paint
        });
      }
    };

    // 1. Terrain Valleys
    updateGeojsonSource(
      'terrain-valleys-src',
      'terrain_valleys',
      'fill',
      terrainGeojson,
      { 'fill-color': '#10b981', 'fill-opacity': 0.35 }
    );

    // 2. Flood Scenario
    updateGeojsonSource(
      'flood-scenario-src',
      'flood_scenario',
      'fill',
      floodScenarioGeojson,
      { 'fill-color': '#0284c7', 'fill-opacity': 0.65 }
    );

    // 3. Exposed Roads
    updateGeojsonSource(
      'exposed-roads-src',
      'exposed_roads',
      'line',
      exposedRoadsGeojson,
      { 'line-color': '#f59e0b', 'line-width': 3.5 }
    );

    // 4. Exposed Bridges
    updateGeojsonSource(
      'exposed-bridges-src',
      'exposed_bridges',
      'line',
      exposedBridgesGeojson,
      { 'line-color': '#ef4444', 'line-width': 5.0 }
    );

    // 5. Exposed Buildings
    updateGeojsonSource(
      'exposed-buildings-src',
      'exposed_buildings',
      'fill',
      exposedBuildingsGeojson,
      { 'fill-color': '#dc2626', 'fill-opacity': 0.7 }
    );
  }, [terrainGeojson, floodScenarioGeojson, exposedRoadsGeojson, exposedBridgesGeojson, exposedBuildingsGeojson]);

  // Initialize Map
  useEffect(() => {
    if (!mapContainer.current || mapInstance.current) return;

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
              'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
            ],
            tileSize: 256,
            attribution: '© OpenStreetMap contributors'
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

    map.on('load', () => {
      // Add AOI Bounding Box layer
      const aoiGeojson: GeoJSON.FeatureCollection = {
        type: 'FeatureCollection',
        features: [
          {
            type: 'Feature',
            geometry: {
              type: 'Polygon',
              coordinates: [
                [
                  [minLon, minLat],
                  [maxLon, minLat],
                  [maxLon, maxLat],
                  [minLon, maxLat],
                  [minLon, minLat]
                ]
              ]
            },
            properties: { name: selectedArea.name }
          }
        ]
      };

      map.addSource('aoi-source', { type: 'geojson', data: aoiGeojson });
      map.addLayer({
        id: 'aoi_boundary',
        type: 'line',
        source: 'aoi-source',
        paint: {
          'line-color': '#38bdf8',
          'line-width': 2,
          'line-dasharray': [3, 2]
        }
      });

      setMapLoaded(true);
    });

    mapInstance.current = map;

    return () => {
      map.remove();
      mapInstance.current = null;
    };
  }, []);

  // Update dynamic layers when data changes or map finishes loading
  useEffect(() => {
    if (mapLoaded) {
      syncLayersToMap();
    }
  }, [mapLoaded, syncLayersToMap]);

  // Toggle layer visibility
  const toggleLayer = (id: string) => {
    setLayers(prev =>
      prev.map(l => {
        if (l.id === id) {
          const nextState = !l.enabled;
          const map = mapInstance.current;
          if (map && map.getLayer(id)) {
            map.setLayoutProperty(id, 'visibility', nextState ? 'visible' : 'none');
          }
          return { ...l, enabled: nextState };
        }
        return l;
      })
    );
  };

  return (
    <div className="relative w-full h-full min-h-[540px] bg-slate-950 rounded-xl overflow-hidden border border-slate-800 shadow-xl flex flex-col">
      {/* Map Header Bar */}
      <div className="absolute top-3 left-3 z-10 bg-slate-900/90 backdrop-blur px-3 py-1.5 rounded-lg border border-slate-700/80 shadow flex items-center space-x-2 text-xs">
        <Map className="w-4 h-4 text-sky-400" />
        <span className="font-semibold text-slate-200">{selectedArea.name}</span>
        <span className="text-slate-400">({selectedArea.region})</span>
        {isScenarioMode ? (
          <span className="flex items-center space-x-1 px-2 py-0.5 rounded bg-amber-950/80 text-amber-300 border border-amber-700 text-[10px] font-medium ml-2">
            <AlertTriangle className="w-3 h-3 text-amber-400" />
            <span>Illustrative Scenario Mode</span>
          </span>
        ) : (
          <span className="flex items-center space-x-1 px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700 text-[10px] font-medium ml-2">
            <span>Terrain &amp; OSM Baseline</span>
          </span>
        )}
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
          <span className="text-[10px] text-emerald-400 font-medium">Evidence Layers</span>
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
                {!layer.available ? (
                  <span className="text-[9px] px-1.5 py-0.2 rounded bg-slate-800 text-slate-500 border border-slate-700">
                    Not Loaded
                  </span>
                ) : (
                  <span className="text-[9px] px-1.5 py-0.2 rounded bg-emerald-950 text-emerald-400 border border-emerald-800">
                    Active
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
          Basemap: OpenStreetMap contributors. Terrain derived from Copernicus GLO-30 DEM.
        </div>
      </div>
    </div>
  );
};
