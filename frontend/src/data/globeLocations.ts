import { GlobeMarker, GlobeCameraPreset } from '../types';

export const GLOBE_MARKERS: GlobeMarker[] = [
  {
    id: 'trishuli_nepal',
    name: 'Trishuli Basin & Highway Corridor',
    region: 'Nuwakot & Rasuwa Districts',
    country: 'Nepal',
    lat: 27.98,
    lon: 85.18,
    status: 'primary_active',
    eventDate: '2026-08-26',
    description:
      'Primary hackathon case study. High-relief mountain gorge basin subject to flash flooding, debris inundation, and severe highway connectivity disruption.',
    terrainStatus: 'Copernicus DEM GLO-30 verified (100% AOI coverage)',
    infrastructureStatus: '301,586 OSM elements cached (roads, bridges, buildings)',
    satelliteStatus: 'Sentinel-1 SAR pending post-event orbital pass',
    aoiId: 'trishuli_nepal',
  },
  {
    id: 'brahmaputra_assam',
    name: 'Brahmaputra River Basin',
    region: 'Assam Valley',
    country: 'India',
    lat: 26.18,
    lon: 91.75,
    status: 'illustrative_planned',
    eventDate: 'Illustrative 2026 Monsoon',
    description:
      'Illustrative future case study. Massive braided river corridor with extensive downstream agricultural and settlement exposure during monsoon surges.',
    terrainStatus: 'Planned Copernicus GLO-30 acquisition',
    infrastructureStatus: 'Pre-event OSM data candidate',
    satelliteStatus: 'Sentinel-1 SAR acquisition planned',
  },
  {
    id: 'indus_sindh',
    name: 'Lower Indus River Plain',
    region: 'Sindh Province',
    country: 'Pakistan',
    lat: 25.39,
    lon: 68.37,
    status: 'illustrative_planned',
    eventDate: 'Illustrative 2026 Monsoon',
    description:
      'Illustrative future case study. Low-gradient alluvial flood plain vulnerable to prolonged riverine inundation and canal overflow.',
    terrainStatus: 'Planned Copernicus GLO-30 acquisition',
    infrastructureStatus: 'Pre-event OSM data candidate',
    satelliteStatus: 'Sentinel-1 SAR acquisition planned',
  },
  {
    id: 'chindwin_sagaing',
    name: 'Chindwin River Valley',
    region: 'Sagaing Region',
    country: 'Myanmar',
    lat: 22.25,
    lon: 95.02,
    status: 'illustrative_planned',
    eventDate: 'Illustrative 2026 Monsoon',
    description:
      'Illustrative future case study. Tropical mountain valley corridor vulnerable to seasonal rainfall, tributary backflow, and riverbank erosion.',
    terrainStatus: 'Planned Copernicus GLO-30 acquisition',
    infrastructureStatus: 'Pre-event OSM data candidate',
    satelliteStatus: 'Sentinel-1 SAR acquisition planned',
  },
];

export const GLOBE_CAMERA_PRESETS: GlobeCameraPreset[] = [
  {
    id: 'global',
    label: 'Global View',
    lat: 20.0,
    lon: 45.0,
    distance: 3.8,
  },
  {
    id: 'nepal',
    label: 'Himalayan Region',
    lat: 28.39,
    lon: 84.12,
    distance: 2.2,
  },
  {
    id: 'trishuli',
    label: 'Trishuli Basin (AOI)',
    lat: 27.98,
    lon: 85.18,
    distance: 1.45,
  },
];
