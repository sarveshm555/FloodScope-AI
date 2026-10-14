import React, { useEffect, useState } from 'react';
import { Header } from './components/Header';
import { AreaSelector, PILOT_AREAS } from './components/AreaSelector';
import { MapWorkspace } from './components/MapWorkspace';
import { SummaryPanel } from './components/SummaryPanel';
import { ConnectivityPanel } from './components/ConnectivityPanel';
import { CopilotPanel } from './components/CopilotPanel';
import { ProcessingStatus, Stage } from './components/ProcessingStatus';
import { SatelliteDiscovery } from './components/SatelliteDiscovery';
import { DataManifestView } from './components/DataManifestView';
import {
  AreaOfInterest,
  BackendHealth,
  CatalogSearchResponse,
  TerrainAnalysisResponse,
  FloodScenarioResponse,
  InfrastructureExposureSummary,
  SituationReportResponse,
} from './types';
import {
  fetchHealth,
  searchSatelliteCatalog,
  fetchTerrainAnalysis,
  fetchFloodScenario,
  fetchExposureSummary,
  fetchSituationReport,
} from './services/api';
import { Play, RotateCw, AlertTriangle } from 'lucide-react';

export const App: React.FC = () => {
  const [health, setHealth] = useState<BackendHealth | null>(null);
  const [healthLoading, setHealthLoading] = useState<boolean>(true);
  const [healthError, setHealthError] = useState<string | null>(null);

  const [selectedArea, setSelectedArea] = useState<AreaOfInterest>(PILOT_AREAS[0]);
  const [eventDate, setEventDate] = useState<string>('2026-08-26');

  // Analysis pipeline states
  const [waterLevelM, setWaterLevelM] = useState<number>(500.0);
  const [maxSlopeDeg, setMaxSlopeDeg] = useState<number>(8.0);
  const [analyzing, setAnalyzing] = useState<boolean>(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  // Computed data assets
  const [terrainData, setTerrainData] = useState<TerrainAnalysisResponse | null>(null);
  const [scenarioData, setScenarioData] = useState<FloodScenarioResponse | null>(null);
  const [exposureData, setExposureData] = useState<InfrastructureExposureSummary | null>(null);
  const [reportData, setReportData] = useState<SituationReportResponse | null>(null);

  // Satellite discovery states
  const [discoveryData, setDiscoveryData] = useState<CatalogSearchResponse | null>(null);
  const [discoveryLoading, setDiscoveryLoading] = useState<boolean>(false);
  const [discoveryError, setDiscoveryError] = useState<string | null>(null);

  const [activeTab, setActiveTab] = useState<'discovery' | 'manifest' | 'summary' | 'connectivity' | 'copilot'>('summary');

  // Pipeline stages
  const [stages, setStages] = useState<Stage[]>([
    { id: 'catalog', name: '1. Satellite Catalog Discovery', status: 'idle', detail: 'Discover pre/post Sentinel-1 SAR pairs in CDSE' },
    { id: 'acquisition', name: '2. Data Acquisition & Validation', status: 'completed', detail: 'Real Copernicus DEM GLO-30 mosaic verified (100% AOI)' },
    { id: 'preprocessing', name: '3. Geospatial Terrain Analysis', status: 'idle', detail: 'Slope, basin floors, elevation profile (Copernicus DEM)' },
    { id: 'flood_change', name: '4. Illustrative Flood Scenario', status: 'idle', detail: 'Hydrodynamic river stage simulation (455m-1200m)' },
    { id: 'exposure', name: '5. OSM Infrastructure Overlay', status: 'idle', detail: 'Spatial intersection: 56k+ buildings, 370 roads, 60 bridges' },
    { id: 'connectivity', name: '6. Settlement Graph Reachability', status: 'idle', detail: 'Network connectivity & isolated settlement detection' },
    { id: 'copilot', name: '7. Situation-Report Copilot', status: 'idle', detail: 'Traceable bilingual English & Nepali report generation' },
  ]);

  useEffect(() => {
    fetchHealth()
      .then((data) => {
        setHealth(data);
        setHealthLoading(false);
      })
      .catch((err) => {
        setHealthError(err.message);
        setHealthLoading(false);
      });
  }, []);

  const handleDiscover = () => {
    setDiscoveryLoading(true);
    setDiscoveryError(null);
    setStages((prev) =>
      prev.map((s) =>
        s.id === 'catalog'
          ? { ...s, status: 'running', detail: 'Querying Copernicus Data Space catalog API...' }
          : s
      )
    );

    searchSatelliteCatalog({
      bbox: selectedArea.bbox,
      event_date: eventDate,
      pre_days: 15,
      post_days: 15,
      include_sentinel_1: true,
      include_sentinel_2: true,
    })
      .then((res) => {
        setDiscoveryData(res);
        setDiscoveryLoading(false);
        setActiveTab('discovery');
        setStages((prev) =>
          prev.map((s) =>
            s.id === 'catalog'
              ? {
                  ...s,
                  status: 'completed',
                  detail: `Discovered ${res.total_discovered} products (${res.sentinel_1_count} SAR, ${res.sentinel_2_count} optical)`
                }
              : s
          )
        );
      })
      .catch((err) => {
        setDiscoveryError(err.message);
        setDiscoveryLoading(false);
        setStages((prev) =>
          prev.map((s) =>
            s.id === 'catalog'
              ? { ...s, status: 'failed', detail: `Query error: ${err.message}` }
              : s
          )
        );
      });
  };

  const handleRunFullAnalysis = async () => {
    setAnalyzing(true);
    setAnalysisError(null);

    try {
      // Step 3: Terrain
      setStages((prev) =>
        prev.map((s) =>
          s.id === 'preprocessing'
            ? { ...s, status: 'running', detail: 'Computing terrain slope and valley floor...' }
            : s
        )
      );
      const tRes = await fetchTerrainAnalysis(selectedArea.bbox, 5.0, 800.0);
      setTerrainData(tRes);
      setStages((prev) =>
        prev.map((s) =>
          s.id === 'preprocessing'
            ? { ...s, status: 'completed', detail: `DEM slope calculated (Mean ${tRes.statistics.slope_mean_deg}°)` }
            : s
        )
      );

      // Step 4: Scenario
      setStages((prev) =>
        prev.map((s) =>
          s.id === 'flood_change'
            ? { ...s, status: 'running', detail: `Generating ${waterLevelM}m stage scenario...` }
            : s
        )
      );
      const sRes = await fetchFloodScenario(waterLevelM, maxSlopeDeg, selectedArea.bbox);
      setScenarioData(sRes);
      setStages((prev) =>
        prev.map((s) =>
          s.id === 'flood_change'
            ? { ...s, status: 'completed', detail: `Hypothetical flood footprint: ${sRes.extent_area_km2} km²` }
            : s
        )
      );

      // Step 5 & 6: Exposure & Connectivity
      setStages((prev) =>
        prev.map((s) =>
          s.id === 'exposure' || s.id === 'connectivity'
            ? { ...s, status: 'running', detail: 'Intersecting OpenStreetMap buildings, roads & bridges...' }
            : s
        )
      );
      const eRes = await fetchExposureSummary(waterLevelM, maxSlopeDeg);
      setExposureData(eRes);
      setStages((prev) =>
        prev.map((s) => {
          if (s.id === 'exposure') {
            return {
              ...s,
              status: 'completed',
              detail: `${eRes.exposed_buildings_count} bldgs, ${eRes.exposed_road_length_km} km roads exposed`
            };
          }
          if (s.id === 'connectivity') {
            return {
              ...s,
              status: 'completed',
              detail: `${eRes.exposed_bridges_count} bridges severed, ${eRes.isolated_settlements.length} settlements at risk`
            };
          }
          return s;
        })
      );

      // Step 7: Copilot Report
      setStages((prev) =>
        prev.map((s) =>
          s.id === 'copilot'
            ? { ...s, status: 'running', detail: 'Synthesizing bilingual English & Nepali report...' }
            : s
        )
      );
      const rRes = await fetchSituationReport(waterLevelM, maxSlopeDeg);
      setReportData(rRes);
      setStages((prev) =>
        prev.map((s) =>
          s.id === 'copilot'
            ? { ...s, status: 'completed', detail: 'Bilingual situation report generated successfully' }
            : s
        )
      );

      setActiveTab('summary');
    } catch (err: any) {
      setAnalysisError(err.message || 'Pipeline execution failed');
      setStages((prev) =>
        prev.map((s) =>
          s.status === 'running'
            ? { ...s, status: 'failed', detail: `Failed: ${err.message}` }
            : s
        )
      );
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      <Header health={health} loading={healthLoading} error={healthError} />

      <main className="flex-1 p-6 grid grid-cols-1 xl:grid-cols-12 gap-6 max-w-[1720px] mx-auto w-full">
        {/* Left Column: Configuration, Scenario Controls & Pipeline Status */}
        <div className="xl:col-span-4 space-y-6">
          <AreaSelector
            selectedArea={selectedArea}
            onSelectArea={setSelectedArea}
            eventDate={eventDate}
            onDateChange={setEventDate}
            onDiscover={handleDiscover}
            discovering={discoveryLoading}
          />

          {/* Interactive Analysis Trigger & Scenario Parameter Panel */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h2 className="text-sm font-semibold text-slate-200">Execution &amp; Scenario Mode</h2>
              <span className="text-[10px] bg-sky-950 text-sky-400 border border-sky-800 px-2 py-0.5 rounded font-mono">
                Real DEM + OSM
              </span>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <div className="flex justify-between text-slate-300 mb-1">
                  <span>River Stage Threshold (Elevation):</span>
                  <span className="font-mono text-sky-400 font-bold">{waterLevelM} m</span>
                </div>
                <input
                  type="range"
                  min="460"
                  max="750"
                  step="5"
                  value={waterLevelM}
                  onChange={(e) => setWaterLevelM(parseFloat(e.target.value))}
                  disabled={analyzing}
                  className="w-full accent-sky-500 cursor-pointer"
                />
                <span className="text-[10px] text-slate-500">Trishuli valley floor begins at ~455m</span>
              </div>

              <div>
                <div className="flex justify-between text-slate-300 mb-1">
                  <span>Max Inundation Slope:</span>
                  <span className="font-mono text-emerald-400 font-bold">{maxSlopeDeg}°</span>
                </div>
                <input
                  type="range"
                  min="2"
                  max="15"
                  step="1"
                  value={maxSlopeDeg}
                  onChange={(e) => setMaxSlopeDeg(parseFloat(e.target.value))}
                  disabled={analyzing}
                  className="w-full accent-emerald-500 cursor-pointer"
                />
                <span className="text-[10px] text-slate-500">Excludes unrealistic steep valley wall flooding</span>
              </div>
            </div>

            <button
              onClick={handleRunFullAnalysis}
              disabled={analyzing}
              className={`w-full py-2.5 px-4 rounded-lg font-semibold text-xs flex items-center justify-center space-x-2 transition shadow-lg ${
                analyzing
                  ? 'bg-sky-800 text-slate-300 cursor-wait'
                  : 'bg-gradient-to-r from-sky-600 to-indigo-600 hover:from-sky-500 hover:to-indigo-500 text-white'
              }`}
            >
              {analyzing ? (
                <>
                  <RotateCw className="w-4 h-4 animate-spin" />
                  <span>Processing Spatial Layers...</span>
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-current" />
                  <span>Run Analysis Pipeline</span>
                </>
              )}
            </button>

            {analysisError && (
              <div className="p-2.5 rounded bg-rose-950/50 border border-rose-800 text-[11px] text-rose-300 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-rose-400 flex-shrink-0" />
                <span>{analysisError}</span>
              </div>
            )}
          </div>

          <ProcessingStatus stages={stages} />
        </div>

        {/* Right Column: Map Workspace & Intelligence Panels */}
        <div className="xl:col-span-8 flex flex-col space-y-6">
          {/* Map Workspace with Live Overlays */}
          <div className="h-[520px] w-full">
            <MapWorkspace
              selectedArea={selectedArea}
              terrainGeojson={terrainData?.geojson_layer}
              floodScenarioGeojson={scenarioData?.geojson}
              exposedRoadsGeojson={exposureData?.geojson_layers?.exposed_roads}
              exposedBridgesGeojson={exposureData?.geojson_layers?.exposed_bridges}
              exposedBuildingsGeojson={exposureData?.geojson_layers?.exposed_buildings}
              isScenarioMode={!!scenarioData}
            />
          </div>

          {/* Intelligence Tab Navigation */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-2 flex flex-wrap items-center gap-2">
            <button
              onClick={() => setActiveTab('summary')}
              className={`flex-1 py-2 px-3 rounded-lg text-xs font-semibold transition ${
                activeTab === 'summary'
                  ? 'bg-sky-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              Infrastructure Exposure
            </button>
            <button
              onClick={() => setActiveTab('connectivity')}
              className={`flex-1 py-2 px-3 rounded-lg text-xs font-semibold transition ${
                activeTab === 'connectivity'
                  ? 'bg-sky-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              Settlement Connectivity
            </button>
            <button
              onClick={() => setActiveTab('copilot')}
              className={`flex-1 py-2 px-3 rounded-lg text-xs font-semibold transition ${
                activeTab === 'copilot'
                  ? 'bg-sky-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              Situation-Report Copilot
            </button>
            <button
              onClick={() => setActiveTab('manifest')}
              className={`flex-1 py-2 px-3 rounded-lg text-xs font-semibold transition ${
                activeTab === 'manifest'
                  ? 'bg-sky-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              Data Assets &amp; Manifest
            </button>
            <button
              onClick={() => setActiveTab('discovery')}
              className={`flex-1 py-2 px-3 rounded-lg text-xs font-semibold transition ${
                activeTab === 'discovery'
                  ? 'bg-sky-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              Satellite Discovery
              {discoveryData && (
                <span className="ml-1.5 px-1.5 py-0.2 rounded-full bg-slate-950/80 text-[10px]">
                  {discoveryData.total_discovered}
                </span>
              )}
            </button>
          </div>

          {/* Active Tab Content */}
          <div>
            {activeTab === 'summary' && (
              <SummaryPanel
                terrainData={terrainData}
                exposureData={exposureData}
                isScenarioMode={!!scenarioData}
              />
            )}
            {activeTab === 'connectivity' && (
              <ConnectivityPanel exposureData={exposureData} />
            )}
            {activeTab === 'copilot' && (
              <CopilotPanel
                health={health}
                reportData={reportData}
                loading={analyzing}
              />
            )}
            {activeTab === 'manifest' && <DataManifestView />}
            {activeTab === 'discovery' && (
              <SatelliteDiscovery
                discoveryData={discoveryData}
                loading={discoveryLoading}
                error={discoveryError}
                onRefresh={handleDiscover}
              />
            )}
          </div>
        </div>
      </main>

      {/* Footer Attributions */}
      <footer className="border-t border-slate-800 bg-slate-950 px-6 py-4 text-xs text-slate-500 text-center space-y-1">
        <p>
          FloodScope AI is an educational disaster-intelligence prototype developed for Multimodal AI Hackathon 2026.
        </p>
        <p>
          "Contains modified Copernicus Sentinel data 2026." • "Produced using Copernicus WorldDEM-30 © DLR e.V. 2010–2014 and © Airbus Defence and Space GmbH 2014–2018 provided under COPERNICUS by the European Union and ESA; all rights reserved." • "© OpenStreetMap contributors."
        </p>
      </footer>
    </div>
  );
};
