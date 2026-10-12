import React, { useState } from 'react';
import {
  Satellite,
  Radio,
  Sun,
  AlertTriangle,
  Info,
  Calendar,
  Layers,
  ChevronDown,
  ChevronUp,
  Sparkles,
} from 'lucide-react';
import { CatalogSearchResponse, SatelliteProductMetadata } from '../types';

interface SatelliteDiscoveryProps {
  discoveryData: CatalogSearchResponse | null;
  loading: boolean;
  error: string | null;
  onRefresh: () => void;
}

export const SatelliteDiscovery: React.FC<SatelliteDiscoveryProps> = ({
  discoveryData,
  loading,
  error,
  onRefresh,
}) => {
  const [filter, setFilter] = useState<'all' | 's1' | 's2' | 'recommended'>('all');
  const [expandedId, setExpandedId] = useState<string | null>(null);

  if (loading) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center space-y-4">
        <div className="w-10 h-10 border-4 border-sky-500/20 border-t-sky-500 rounded-full animate-spin mx-auto" />
        <div>
          <h3 className="text-sm font-semibold text-slate-200">
            Querying Copernicus Data Space Catalog...
          </h3>
          <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">
            Searching Sentinel-1 SAR and Sentinel-2 optical archives across the Trishuli Valley pilot bounding box. Calculating spatial intersection and orbit match scores.
          </p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-slate-900 border border-rose-900/40 rounded-xl p-6 text-center space-y-3">
        <AlertTriangle className="w-8 h-8 text-rose-400 mx-auto" />
        <h3 className="text-sm font-semibold text-rose-300">Satellite Catalog Query Error</h3>
        <p className="text-xs text-slate-400 max-w-lg mx-auto bg-slate-950 p-3 rounded-lg border border-slate-800 font-mono">
          {error}
        </p>
        <button
          onClick={onRefresh}
          className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-xs font-medium rounded-lg text-slate-200 transition"
        >
          Retry Discovery
        </button>
      </div>
    );
  }

  if (!discoveryData) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center space-y-3">
        <div className="p-3 bg-slate-950 rounded-full w-12 h-12 flex items-center justify-center mx-auto border border-slate-800">
          <Satellite className="w-6 h-6 text-sky-400" />
        </div>
        <h3 className="text-sm font-semibold text-slate-200">
          Satellite Data Discovery Awaiting Trigger
        </h3>
        <p className="text-xs text-slate-400 max-w-md mx-auto">
          Click <strong>"Discover Satellite Observations"</strong> in the configuration panel to search the official Copernicus Data Space Ecosystem catalog for Sentinel-1 and Sentinel-2 passes.
        </p>
      </div>
    );
  }

  // Filter products
  const allProducts: SatelliteProductMetadata[] = [
    ...discoveryData.sentinel_1_candidates,
    ...discoveryData.sentinel_2_candidates,
  ];

  const filtered = allProducts.filter((p) => {
    if (filter === 's1') return p.collection === 'SENTINEL-1';
    if (filter === 's2') return p.collection === 'SENTINEL-2';
    if (filter === 'recommended') return p.selection_status === 'recommended_pair';
    return true;
  });

  const bestPair = discoveryData.recommended_sar_pairs[0];

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-5">
      {/* Header and Statistics */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center space-x-2">
            <Satellite className="w-5 h-5 text-sky-400" />
            <h2 className="font-semibold text-slate-200">Discovered Satellite Acquisitions</h2>
            <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800">
              Live CDSE Catalog Record
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Query AOI: [{discoveryData.query_parameters.bbox.join(', ')}] • Event: {discoveryData.query_parameters.event_date}
          </p>
        </div>

        {/* Count summary badges */}
        <div className="flex items-center space-x-2 text-xs">
          <span className="px-2.5 py-1 rounded-md bg-slate-800 border border-slate-700 text-slate-300">
            Total Discovered: <strong>{discoveryData.total_discovered}</strong>
          </span>
          <span className="px-2.5 py-1 rounded-md bg-sky-950/80 border border-sky-800 text-sky-300">
            Sentinel-1 SAR: <strong>{discoveryData.sentinel_1_count}</strong>
          </span>
          <span className="px-2.5 py-1 rounded-md bg-amber-950/80 border border-amber-800 text-amber-300">
            Sentinel-2 Optical: <strong>{discoveryData.sentinel_2_count}</strong>
          </span>
        </div>
      </div>

      {/* Recommended 12-day Repeat Pass SAR Pair Banner */}
      {bestPair && (
        <div className="p-4 rounded-xl bg-gradient-to-r from-sky-950/70 via-indigo-950/50 to-slate-900 border border-sky-600/40 shadow-lg space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Sparkles className="w-4 h-4 text-sky-400" />
              <span className="text-xs font-bold text-sky-300 uppercase tracking-wider">
                Primary Recommended SAR Change Pair
              </span>
            </div>
            <span className="text-xs px-2 py-0.5 rounded bg-emerald-900/60 text-emerald-300 border border-emerald-700 font-semibold">
              Match Score: {(bestPair.suitability_score * 100).toFixed(0)}%
            </span>
          </div>

          <p className="text-xs text-slate-300">
            {bestPair.recommendation_reason}
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs pt-1">
            <div className="p-2.5 rounded-lg bg-slate-950/80 border border-slate-800">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold text-emerald-400">Pre-Event Observation</span>
                <span className="text-[10px] text-slate-500">{bestPair.pre_event_date.slice(0, 10)}</span>
              </div>
              <div className="font-mono text-[11px] text-slate-200 truncate mt-1">
                {bestPair.pre_event_product_name}
              </div>
              <div className="text-[10px] text-slate-400 mt-1">
                Orbit {bestPair.relative_orbit} ({bestPair.orbit_direction}) • Pol: {bestPair.polarization}
              </div>
            </div>

            <div className="p-2.5 rounded-lg bg-slate-950/80 border border-slate-800">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold text-sky-400">Post-Event Observation</span>
                <span className="text-[10px] text-slate-500">{bestPair.post_event_date.slice(0, 10)}</span>
              </div>
              <div className="font-mono text-[11px] text-slate-200 truncate mt-1">
                {bestPair.post_event_product_name}
              </div>
              <div className="text-[10px] text-slate-400 mt-1">
                Orbit {bestPair.relative_orbit} ({bestPair.orbit_direction}) • Pol: {bestPair.polarization}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Filter Tabs */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-2">
        <div className="flex items-center space-x-1 text-xs">
          <button
            onClick={() => setFilter('all')}
            className={`px-3 py-1.5 rounded-lg font-medium transition ${
              filter === 'all'
                ? 'bg-slate-800 text-white'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            All Products ({allProducts.length})
          </button>
          <button
            onClick={() => setFilter('recommended')}
            className={`px-3 py-1.5 rounded-lg font-medium transition ${
              filter === 'recommended'
                ? 'bg-sky-600 text-white'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Recommended Pair
          </button>
          <button
            onClick={() => setFilter('s1')}
            className={`px-3 py-1.5 rounded-lg font-medium transition ${
              filter === 's1'
                ? 'bg-slate-800 text-white'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Sentinel-1 SAR ({discoveryData.sentinel_1_count})
          </button>
          <button
            onClick={() => setFilter('s2')}
            className={`px-3 py-1.5 rounded-lg font-medium transition ${
              filter === 's2'
                ? 'bg-slate-800 text-white'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Sentinel-2 Optical ({discoveryData.sentinel_2_count})
          </button>
        </div>

        <span className="text-[11px] text-slate-500">
          Showing {filtered.length} items
        </span>
      </div>

      {/* Discovered Products List */}
      <div className="space-y-2.5 max-h-[460px] overflow-y-auto pr-1">
        {filtered.map((product) => {
          const isExpanded = expandedId === product.id;
          const isSAR = product.collection === 'SENTINEL-1';

          let statusBadge = (
            <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
              Compatible
            </span>
          );

          if (product.selection_status === 'recommended_pair') {
            statusBadge = (
              <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-700 font-semibold">
                Recommended SAR Pair
              </span>
            );
          } else if (product.selection_status === 'cloud_risk') {
            statusBadge = (
              <span className="text-[10px] px-2 py-0.5 rounded bg-amber-950 text-amber-300 border border-amber-700 font-medium">
                High Cloud Cover ({product.cloud_cover_percentage}%)
              </span>
            );
          } else if (product.selection_status === 'rejected_no_intersection') {
            statusBadge = (
              <span className="text-[10px] px-2 py-0.5 rounded bg-rose-950 text-rose-300 border border-rose-800 font-medium">
                No AOI Overlap
              </span>
            );
          }

          return (
            <div
              key={product.id}
              className={`p-3 rounded-lg border transition ${
                product.selection_status === 'recommended_pair'
                  ? 'bg-sky-950/30 border-sky-800/80'
                  : 'bg-slate-950/60 border-slate-800 hover:border-slate-700'
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center space-x-2.5 min-w-0">
                  <div
                    className={`p-1.5 rounded-md ${
                      isSAR
                        ? 'bg-sky-900/40 text-sky-400'
                        : 'bg-amber-900/40 text-amber-400'
                    }`}
                  >
                    {isSAR ? <Radio className="w-4 h-4" /> : <Sun className="w-4 h-4" />}
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center space-x-2">
                      <span className="text-xs font-semibold text-slate-200">
                        {product.platform} {product.product_type}
                      </span>
                      <span
                        className={`text-[10px] px-1.5 py-0.2 rounded font-medium ${
                          product.timing === 'pre-event'
                            ? 'bg-emerald-950 text-emerald-400 border border-emerald-900'
                            : product.timing === 'post-event'
                            ? 'bg-sky-950 text-sky-400 border border-sky-900'
                            : 'bg-purple-950 text-purple-400 border border-purple-900'
                        }`}
                      >
                        {product.timing.toUpperCase()}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 font-mono truncate max-w-md">
                      {product.name}
                    </p>
                  </div>
                </div>

                <div className="flex items-center space-x-2 shrink-0">
                  {statusBadge}
                  <button
                    onClick={() => setExpandedId(isExpanded ? null : product.id)}
                    className="p-1 rounded text-slate-400 hover:text-slate-200"
                  >
                    {isExpanded ? (
                      <ChevronUp className="w-4 h-4" />
                    ) : (
                      <ChevronDown className="w-4 h-4" />
                    )}
                  </button>
                </div>
              </div>

              {/* Technical summary line */}
              <div className="mt-2 text-[11px] text-slate-400 flex flex-wrap items-center gap-x-4 gap-y-1">
                <span className="flex items-center gap-1">
                  <Calendar className="w-3 h-3 text-slate-500" />
                  {product.acquisition_time.replace('T', ' ').slice(0, 19)} UTC
                  ({Math.abs(product.delta_days_from_event)}d {product.delta_days_from_event < 0 ? 'prior' : 'post'})
                </span>

                <span className="flex items-center gap-1">
                  <Layers className="w-3 h-3 text-slate-500" />
                  AOI Overlap: <strong>{product.aoi_intersection_percent}%</strong>
                </span>

                {isSAR && (
                  <span>
                    Track: <strong>{product.relative_orbit ?? 'N/A'}</strong> ({product.orbit_direction}) • Pol: {product.polarization}
                  </span>
                )}

                {!isSAR && product.cloud_cover_percentage !== null && (
                  <span>
                    Scene Cloud: <strong>{product.cloud_cover_percentage}%</strong>
                  </span>
                )}

                {product.size_mb && (
                  <span className="text-slate-500">
                    Archive Size: {product.size_mb} MB
                  </span>
                )}
              </div>

              {/* Selection reason banner */}
              <p className="mt-1.5 text-[11px] text-slate-400 italic">
                {product.selection_reason}
              </p>

              {/* Expanded technical details */}
              {isExpanded && (
                <div className="mt-3 pt-3 border-t border-slate-800 text-[10px] space-y-1 text-slate-400 font-mono bg-slate-950 p-2.5 rounded">
                  <div>Product ID: {product.id}</div>
                  <div>Retrieval Timestamp: {product.retrieval_timestamp}</div>
                  <div>Metadata Source: {product.metadata_source}</div>
                  <div>Intersects AOI: {product.intersects_aoi ? 'True' : 'False'}</div>
                  <div>Payload Downloaded: {product.data_downloaded ? 'True' : 'False (Discovered Only)'}</div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Provenance & Download Notice Footer */}
      <div className="p-3 bg-slate-950/80 rounded-lg border border-slate-800 text-[11px] text-slate-400 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Info className="w-4 h-4 text-sky-400 shrink-0" />
          <span>
            Metadata Source: <strong>{discoveryData.metadata_source}</strong> • Retrieval ID: {discoveryData.search_id.slice(0, 8)}
          </span>
        </div>
        <span className="text-emerald-400 font-semibold">
          Data Downloaded: 0 MB (Metadata Discovery Verified)
        </span>
      </div>
    </div>
  );
};
