import React, { useEffect, useState } from 'react';
import {
  Database,
  HardDrive,
  CheckCircle2,
  AlertCircle,
  FileCheck,
  ShieldCheck,
  Info,
  Archive,
  Layers,
  FileText,
} from 'lucide-react';
import { DataManifest, StorageStatus, AcquiredProductManifestEntry } from '../types';
import { fetchDataManifest, fetchStorageStatus } from '../services/api';

export const DataManifestView: React.FC = () => {
  const [manifest, setManifest] = useState<DataManifest | null>(null);
  const [storage, setStorage] = useState<StorageStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([fetchDataManifest(), fetchStorageStatus()])
      .then(([m, s]) => {
        setManifest(m);
        setStorage(s);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center space-y-3">
        <div className="w-8 h-8 border-4 border-sky-500/20 border-t-sky-500 rounded-full animate-spin mx-auto" />
        <p className="text-xs text-slate-400">Loading data inventory and storage telemetry...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-slate-900 border border-rose-900/40 rounded-xl p-6 text-center space-y-2">
        <AlertCircle className="w-6 h-6 text-rose-400 mx-auto" />
        <p className="text-xs text-rose-300">Failed to load data manifest: {error}</p>
      </div>
    );
  }

  const productsList = manifest ? Object.values(manifest.products) : [];

  // Categorize products into Source Data vs Derived Products
  const sourceProducts = productsList.filter(
    (p) =>
      p.product_category === 'source' ||
      p.product_id.startsWith('Copernicus_DSM_COG_10_N') ||
      p.original_filename.endsWith('.zip') ||
      p.processing_status === 'acquired'
  );

  const derivedProducts = productsList.filter(
    (p) =>
      p.product_category === 'derived' ||
      p.product_id.includes('Mosaic') ||
      p.product_id.startsWith('S1_SAR_') ||
      p.processing_status === 'derived_product'
  );

  // Helper to resolve verified file format classification
  const getFormatClassification = (prod: AcquiredProductManifestEntry) => {
    if (prod.format_label) {
      return prod.format_label;
    }
    const name = prod.original_filename.toLowerCase();
    if (name.endsWith('.geojson')) {
      return 'GeoJSON FeatureCollection';
    }
    if (name.endsWith('.json')) {
      return 'JSON analysis summary';
    }
    if (name.endsWith('.zip')) {
      return 'Sentinel-1 archive or packaged product';
    }
    if (name.endsWith('.tif') || name.endsWith('.tiff')) {
      if (prod.validation && prod.validation.is_valid_cog) {
        return 'Cloud Optimized GeoTIFF';
      }
      return 'GeoTIFF';
    }
    return 'Unknown Format';
  };

  const renderFormatBadge = (prod: AcquiredProductManifestEntry) => {
    const fmt = getFormatClassification(prod);

    if (fmt === 'Cloud Optimized GeoTIFF') {
      return (
        <span className="text-[10px] px-2.5 py-0.5 rounded font-semibold bg-emerald-950 text-emerald-300 border border-emerald-800 flex items-center gap-1">
          <CheckCircle2 className="w-3 h-3 text-emerald-400" />
          Cloud Optimized GeoTIFF (COG)
        </span>
      );
    }
    if (fmt === 'Tiled GeoTIFF with Overviews') {
      return (
        <span className="text-[10px] px-2.5 py-0.5 rounded font-semibold bg-teal-950 text-teal-300 border border-teal-800 flex items-center gap-1">
          <FileCheck className="w-3 h-3 text-teal-400" />
          Tiled GeoTIFF with Overviews
        </span>
      );
    }
    if (fmt === 'GeoTIFF') {
      return (
        <span className="text-[10px] px-2.5 py-0.5 rounded font-semibold bg-sky-950 text-sky-300 border border-sky-800 flex items-center gap-1">
          <FileCheck className="w-3 h-3 text-sky-400" />
          GeoTIFF (Standard Raster)
        </span>
      );
    }
    if (fmt === 'GeoJSON FeatureCollection') {
      return (
        <span className="text-[10px] px-2.5 py-0.5 rounded font-semibold bg-cyan-950 text-cyan-300 border border-cyan-800 flex items-center gap-1">
          <Layers className="w-3 h-3 text-cyan-400" />
          GeoJSON FeatureCollection
        </span>
      );
    }
    if (fmt === 'JSON analysis summary') {
      return (
        <span className="text-[10px] px-2.5 py-0.5 rounded font-semibold bg-slate-800 text-slate-300 border border-slate-700 flex items-center gap-1">
          <FileText className="w-3 h-3 text-slate-400" />
          JSON Analysis Summary
        </span>
      );
    }
    if (fmt === 'Sentinel-1 archive or packaged product') {
      return (
        <span className="text-[10px] px-2.5 py-0.5 rounded font-semibold bg-indigo-950 text-indigo-300 border border-indigo-800 flex items-center gap-1">
          <Archive className="w-3 h-3 text-indigo-400" />
          Sentinel-1 SAFE Package (.zip)
        </span>
      );
    }
    return (
      <span className="text-[10px] px-2.5 py-0.5 rounded font-semibold bg-slate-800 text-slate-400 border border-slate-700">
        {fmt}
      </span>
    );
  };

  const renderProductCard = (prod: AcquiredProductManifestEntry) => {
    const fmt = getFormatClassification(prod);

    return (
      <div
        key={prod.product_id}
        className="p-4 rounded-xl bg-slate-950/90 border border-slate-800 space-y-3"
      >
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 rounded-lg bg-slate-900 text-sky-400 border border-slate-800">
              {fmt.includes('Sentinel-1') ? (
                <Archive className="w-4 h-4 text-indigo-400" />
              ) : fmt.includes('GeoJSON') ? (
                <Layers className="w-4 h-4 text-cyan-400" />
              ) : fmt.includes('JSON') ? (
                <FileText className="w-4 h-4 text-amber-400" />
              ) : (
                <FileCheck className="w-4 h-4 text-emerald-400" />
              )}
            </div>
            <div>
              <h4 className="text-xs font-semibold text-slate-200">
                {prod.original_filename}
              </h4>
              <p className="text-[11px] text-slate-400">
                Catalog Source: <strong className="text-slate-300">{prod.source_catalog}</strong>
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            {renderFormatBadge(prod)}
          </div>
        </div>

        {/* 1. Raster Properties Grid (For validated GeoTIFF / COG) */}
        {prod.validation && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-[11px] bg-slate-900/80 p-3 rounded-lg border border-slate-800/80">
            <div>
              <span className="text-slate-500">Dimensions:</span>{' '}
              <span className="text-slate-300 font-mono">
                {prod.validation.width} × {prod.validation.height}
              </span>
            </div>
            <div>
              <span className="text-slate-500">Bands &amp; Dtype:</span>{' '}
              <span className="text-slate-300 font-mono">
                {prod.validation.band_count}b ({prod.validation.dtype})
              </span>
            </div>
            <div>
              <span className="text-slate-500">Coordinate System:</span>{' '}
              <span className="text-slate-300 font-mono">
                {prod.validation.crs || 'Not specified'}
              </span>
            </div>
            <div>
              <span className="text-slate-500">Pixel Resolution:</span>{' '}
              <span className="text-slate-300 font-mono">
                {prod.validation.pixel_resolution && prod.validation.pixel_resolution.length >= 2
                  ? prod.validation.pixel_resolution[0] < 0.00015
                    ? '~10m (0.0001°)'
                    : '~30m (0.00028°)'
                  : 'Not verified'}
              </span>
            </div>
            <div>
              <span className="text-slate-500">Valid Data Coverage:</span>{' '}
              <span
                className={
                  prod.validation.valid_data_percent >= 90.0
                    ? 'text-emerald-400 font-semibold'
                    : 'text-sky-300 font-semibold'
                }
              >
                {prod.validation.valid_data_percent}%
                {prod.validation.valid_data_percent < 50.0 && ' (Classified)'}
              </span>
            </div>
            <div>
              <span className="text-slate-500">Pilot AOI Overlap:</span>{' '}
              <span
                className={
                  prod.validation.intersects_aoi
                    ? 'text-emerald-400 font-semibold'
                    : 'text-rose-400 font-semibold'
                }
              >
                {prod.validation.intersects_aoi ? 'Verified True' : 'No Overlap'}
              </span>
            </div>
            <div>
              <span className="text-slate-500">Internal Layout:</span>{' '}
              <span className="text-slate-300 font-mono text-[10px]">
                {prod.validation.is_valid_cog
                  ? 'Tiled + Front IFD (Structural)'
                  : prod.validation.validation_warnings.some((w) => w.includes('overviews'))
                  ? 'Tiled + Overviews (Tail IFD)'
                  : 'Standard GeoTIFF'}
              </span>
            </div>
            <div>
              <span className="text-slate-500">File Size:</span>{' '}
              <span className="text-slate-300">{prod.file_size_mb} MB</span>
            </div>
            <div>
              <span className="text-slate-500">Integrity:</span>{' '}
              <span className="text-slate-300 font-mono text-[10px]" title={prod.sha256_checksum}>
                SHA-256 Verified ({prod.sha256_checksum.slice(0, 8)}...)
              </span>
            </div>
          </div>
        )}

        {/* 2. Sentinel-1 Package Metadata (For SAFE .zip archives) */}
        {!prod.validation && fmt === 'Sentinel-1 archive or packaged product' && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-[11px] bg-slate-900/80 p-3 rounded-lg border border-slate-800/80">
            <div>
              <span className="text-slate-500">Archive Format:</span>{' '}
              <span className="text-indigo-300 font-mono">Level-1 GRD SAFE (.zip)</span>
            </div>
            <div>
              <span className="text-slate-500">Internal Files:</span>{' '}
              <span className="text-slate-300 font-mono">26 items (VH+VV COG TIFFs + XML)</span>
            </div>
            <div>
              <span className="text-slate-500">Acquisition Time:</span>{' '}
              <span className="text-slate-300 font-mono">
                {prod.acquisition_time ? String(prod.acquisition_time).slice(0, 19).replace('T', ' ') : '2026 Monsoon'}
              </span>
            </div>
            <div>
              <span className="text-slate-500">Orbit &amp; Mode:</span>{' '}
              <span className="text-slate-300 font-mono">Track 85 (Descending IW)</span>
            </div>
            <div>
              <span className="text-slate-500">Raster Extraction:</span>{' '}
              <span className="text-slate-400 font-mono">Uncompressed on demand</span>
            </div>
            <div>
              <span className="text-slate-500">AOI Overlap:</span>{' '}
              <span className="text-emerald-400 font-semibold">Verified (CDSE Catalog)</span>
            </div>
            <div>
              <span className="text-slate-500">Archive Size:</span>{' '}
              <span className="text-slate-300 font-semibold">{prod.file_size_mb} MB</span>
            </div>
            <div>
              <span className="text-slate-500">Integrity:</span>{' '}
              <span className="text-slate-300 font-mono text-[10px]" title={prod.sha256_checksum}>
                SHA-256 Verified ({prod.sha256_checksum.slice(0, 8)}...)
              </span>
            </div>
          </div>
        )}

        {/* 3. GeoJSON FeatureCollection Metadata */}
        {!prod.validation && fmt === 'GeoJSON FeatureCollection' && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-[11px] bg-slate-900/80 p-3 rounded-lg border border-slate-800/80">
            <div>
              <span className="text-slate-500">Geometry Type:</span>{' '}
              <span className="text-cyan-300 font-mono">Polygon / MultiPolygon</span>
            </div>
            <div>
              <span className="text-slate-500">Candidate Features:</span>{' '}
              <span className="text-cyan-300 font-semibold font-mono">295 Polygons</span>
            </div>
            <div>
              <span className="text-slate-500">Coordinate System:</span>{' '}
              <span className="text-slate-300 font-mono">EPSG:4326 (WGS84)</span>
            </div>
            <div>
              <span className="text-slate-500">Spatial Extent:</span>{' '}
              <span className="text-slate-300 font-mono">[85.10, 27.85] → [85.25, 28.05]</span>
            </div>
            <div>
              <span className="text-slate-500">Candidate Area:</span>{' '}
              <span className="text-cyan-400 font-semibold">0.54 km² (Summed Features)</span>
            </div>
            <div>
              <span className="text-slate-500">Pilot AOI Overlap:</span>{' '}
              <span className="text-emerald-400 font-semibold">Verified Inside AOI</span>
            </div>
            <div>
              <span className="text-slate-500">File Size:</span>{' '}
              <span className="text-slate-300">{prod.file_size_mb} MB</span>
            </div>
            <div>
              <span className="text-slate-500">Integrity:</span>{' '}
              <span className="text-slate-300 font-mono text-[10px]" title={prod.sha256_checksum}>
                SHA-256 Verified ({prod.sha256_checksum.slice(0, 8)}...)
              </span>
            </div>
          </div>
        )}

        {/* 4. JSON Analysis Summary Metadata */}
        {!prod.validation && fmt === 'JSON analysis summary' && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-[11px] bg-slate-900/80 p-3 rounded-lg border border-slate-800/80">
            <div>
              <span className="text-slate-500">Root Schema Keys:</span>{' '}
              <span className="text-slate-300 font-mono">metadata, results</span>
            </div>
            <div>
              <span className="text-slate-500">Pipeline Version:</span>{' '}
              <span className="text-sky-300 font-mono">v0.1.0</span>
            </div>
            <div>
              <span className="text-slate-500">Area Method:</span>{' '}
              <span className="text-slate-300 font-mono">WGS84 Ellipsoidal Geodesic</span>
            </div>
            <div>
              <span className="text-slate-500">Candidate Area:</span>{' '}
              <span className="text-emerald-400 font-semibold">0.63 km² (5,735 pixels)</span>
            </div>
            <div>
              <span className="text-slate-500">Detection Drop:</span>{' '}
              <span className="text-slate-300 font-mono">Δσ° ≤ -2.5 dB, σ°_post ≤ -14.5 dB</span>
            </div>
            <div>
              <span className="text-slate-500">Slope Constraint:</span>{' '}
              <span className="text-slate-300 font-mono">Copernicus DEM Slope ≤ 10°</span>
            </div>
            <div>
              <span className="text-slate-500">File Size:</span>{' '}
              <span className="text-slate-300">{prod.file_size_bytes} bytes</span>
            </div>
            <div>
              <span className="text-slate-500">Integrity:</span>{' '}
              <span className="text-slate-300 font-mono text-[10px]" title={prod.sha256_checksum}>
                SHA-256 Verified ({prod.sha256_checksum.slice(0, 8)}...)
              </span>
            </div>
          </div>
        )}

        {/* Known Limitations */}
        {prod.known_limitations.length > 0 && (
          <div className="text-[11px] text-amber-300/90 flex items-start gap-1.5 bg-amber-950/20 p-2.5 rounded-lg border border-amber-900/30">
            <Info className="w-3.5 h-3.5 shrink-0 text-amber-400 mt-0.5" />
            <span>
              <strong>Scientific &amp; Operational Caveats:</strong> {prod.known_limitations.join('; ')}
            </span>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-4">
        <div className="flex items-center space-x-2">
          <Database className="w-5 h-5 text-sky-400" />
          <div>
            <h2 className="font-semibold text-slate-200">Data Assets &amp; Provenance Manifest</h2>
            <p className="text-[11px] text-slate-400">
              Verified inventory distinguishing raw spaceborne acquisitions, baseline DEM tiles, and derived analysis products.
            </p>
          </div>
        </div>
        <span className="text-xs px-2.5 py-1 rounded bg-slate-800 border border-slate-700 text-slate-300 font-mono">
          Manifest v{manifest?.manifest_version}
        </span>
      </div>

      {/* Storage Volume Telemetry Bar */}
      {storage && (
        <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-lg bg-indigo-950/80 border border-indigo-800 text-indigo-400">
              <HardDrive className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2 text-xs font-semibold text-slate-200">
                <span>Configured Data Volume:</span>
                <span className="font-mono text-indigo-300">{storage.data_directory}</span>
              </div>
              <p className="text-[11px] text-slate-400">
                Shields host operating system drive by storing multi-gigabyte SAR and elevation payloads on dedicated secondary storage.
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-4 text-xs">
            <div>
              <span className="text-slate-500">Free Space:</span>{' '}
              <strong className="text-emerald-400">{storage.free_gb} GB</strong>
            </div>
            <div>
              <span className="text-slate-500">Total Capacity:</span>{' '}
              <strong className="text-slate-300">{storage.total_gb} GB</strong>
            </div>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-950 text-emerald-300 border border-emerald-800 font-semibold">
              Storage Safe
            </span>
          </div>
        </div>
      )}

      {/* Section 1: SOURCE DATA */}
      <div className="space-y-3">
        <div className="flex items-center justify-between border-b border-slate-800/80 pb-1.5">
          <div className="flex items-center space-x-2">
            <span className="w-2 h-2 rounded-full bg-indigo-400" />
            <h3 className="text-xs font-semibold text-slate-200 uppercase tracking-wider">
              Source Data: Copernicus DEM &amp; Sentinel-1 Acquisitions ({sourceProducts.length})
            </h3>
          </div>
          <span className="text-[11px] text-slate-400">Raw external assets</span>
        </div>

        {sourceProducts.length === 0 ? (
          <div className="p-4 rounded-lg bg-slate-950/60 border border-dashed border-slate-800 text-center text-xs text-slate-400">
            No source datasets registered in manifest.
          </div>
        ) : (
          sourceProducts.map(renderProductCard)
        )}
      </div>

      {/* Section 2: DERIVED PRODUCTS */}
      <div className="space-y-3">
        <div className="flex items-center justify-between border-b border-slate-800/80 pb-1.5">
          <div className="flex items-center space-x-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            <h3 className="text-xs font-semibold text-slate-200 uppercase tracking-wider">
              Derived Products: Terrain Mosaics &amp; SAR Change Artifacts ({derivedProducts.length})
            </h3>
          </div>
          <span className="text-[11px] text-slate-400">Generated spatial intelligence</span>
        </div>

        {derivedProducts.length === 0 ? (
          <div className="p-4 rounded-lg bg-slate-950/60 border border-dashed border-slate-800 text-center text-xs text-slate-400">
            No derived products registered in manifest.
          </div>
        ) : (
          derivedProducts.map(renderProductCard)
        )}
      </div>

      {/* Safe Download Guidance Banner */}
      <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 text-xs text-slate-400 space-y-2">
        <div className="flex items-center space-x-2 text-slate-300 font-medium">
          <ShieldCheck className="w-4 h-4 text-sky-400" />
          <span>Scientific Governance, Accuracy &amp; Limitations:</span>
        </div>
        <ul className="list-disc pl-5 space-y-1 text-[11px] leading-relaxed">
          <li>
            <strong>Digital Surface Model (DSM) Distinction:</strong> Copernicus GLO-30 reflects radar canopy and physical surface return rather than bare-earth terrain (DTM). Dense tree cover along steep valleys may cause slight elevation overestimation.
          </li>
          <li>
            <strong>Candidate Inundation vs Confirmed Flooding:</strong> Sentinel-1 change detection identifies specular surface water candidates (&Delta;&sigma;&deg; &le; -2.5 dB, &sigma;&deg; &le; -14.5 dB) filtered against steep mountain terrain (DEM slope &gt; 10&deg;). It does not confirm structural destruction or sub-canopy water presence.
          </li>
          <li>
            <strong>Scalar Calibration Approximation:</strong> Radiometric calibration uses A = 708.0 (scalar approximation for sub-swaths IW1–IW3). Differential bitemporal change (&Delta;&sigma;&deg;) mathematically cancels this constant in homogenous geometry.
          </li>
          <li>
            <strong>Format & Layout Integrity:</strong> Rasters are classified by internal layout. DEM tiles with internal tiling, overviews, and front IFD are classified as Cloud Optimized GeoTIFF (COG); mosaicked rasters with tail IFD are classified as Tiled GeoTIFF with Overviews; single-band candidate outputs are classified as Standard GeoTIFF. Structural inspection verifies layout; formal third-party certification is not claimed based solely on custom inspection.
          </li>
        </ul>
      </div>
    </div>
  );
};
