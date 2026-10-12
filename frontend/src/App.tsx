import React, { useEffect, useState } from 'react';
import { Header } from './components/Header';
import { AreaSelector, PILOT_AREAS } from './components/AreaSelector';
import { MapWorkspace } from './components/MapWorkspace';
import { SummaryPanel } from './components/SummaryPanel';
import { ConnectivityPanel } from './components/ConnectivityPanel';
import { CopilotPanel } from './components/CopilotPanel';
import { ProcessingStatus, Stage } from './components/ProcessingStatus';
import { AreaOfInterest, BackendHealth } from './types';
import { fetchHealth } from './services/api';

export const App: React.FC = () => {
  const [health, setHealth] = useState<BackendHealth | null>(null);
  const [healthLoading, setHealthLoading] = useState<boolean>(true);
  const [healthError, setHealthError] = useState<string | null>(null);

  const [selectedArea, setSelectedArea] = useState<AreaOfInterest>(PILOT_AREAS[0]);
  const [eventDate, setEventDate] = useState<string>('2026-08-26');
  const [discovering, setDiscovering] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<'summary' | 'connectivity' | 'copilot'>('summary');

  // Pipeline stages
  const [stages, setStages] = useState<Stage[]>([
    { id: 'catalog', name: '1. Satellite Catalog Discovery', status: 'idle', detail: 'Discover pre/post Sentinel-1 SAR pairs in CDSE' },
    { id: 'acquisition', name: '2. Data Acquisition & Validation', status: 'idle', detail: 'Download & verify integrity of selected orbit scenes' },
    { id: 'preprocessing', name: '3. Geospatial Preprocessing', status: 'idle', detail: 'Radiometric calibration, terrain correction, alignment' },
    { id: 'flood_change', name: '4. Flood & Change Detection', status: 'idle', detail: 'Backscatter thresholding, candidate water surface' },
    { id: 'exposure', name: '5. OSM Infrastructure Overlay', status: 'idle', detail: 'Intersect pre-event buildings, roads, bridges (HeiGIT)' },
    { id: 'connectivity', name: '6. Settlement Graph Connectivity', status: 'idle', detail: 'NetworkX shortest path & hospital reachability analysis' },
    { id: 'copilot', name: '7. Situation-Report Copilot', status: 'idle', detail: 'English/Nepali grounded report generation' },
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
    setDiscovering(true);
    // Simulates entering discovery phase in UI while pointing to Milestone 2
    setTimeout(() => {
      setDiscovering(false);
      setStages((prev) =>
        prev.map((s) =>
          s.id === 'catalog'
            ? { ...s, status: 'idle', detail: 'Discovery service configured (Scheduled for Milestone 2)' }
            : s
        )
      );
    }, 800);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      <Header health={health} loading={healthLoading} error={healthError} />

      <main className="flex-1 p-6 grid grid-cols-1 xl:grid-cols-12 gap-6 max-w-[1720px] mx-auto w-full">
        {/* Left Column: Configuration & Pipeline Status */}
        <div className="xl:col-span-4 space-y-6">
          <AreaSelector
            selectedArea={selectedArea}
            onSelectArea={setSelectedArea}
            eventDate={eventDate}
            onDateChange={setEventDate}
            onDiscover={handleDiscover}
            discovering={discovering}
          />

          <ProcessingStatus stages={stages} />
        </div>

        {/* Right Column: Map Workspace & Intelligence Panels */}
        <div className="xl:col-span-8 flex flex-col space-y-6">
          {/* Map Workspace */}
          <div className="h-[520px] w-full">
            <MapWorkspace selectedArea={selectedArea} />
          </div>

          {/* Intelligence Tab Navigation */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-2 flex items-center space-x-2">
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
          </div>

          {/* Active Tab Content */}
          <div>
            {activeTab === 'summary' && <SummaryPanel analysisRun={false} />}
            {activeTab === 'connectivity' && <ConnectivityPanel analysisRun={false} />}
            {activeTab === 'copilot' && <CopilotPanel health={health} analysisRun={false} />}
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
