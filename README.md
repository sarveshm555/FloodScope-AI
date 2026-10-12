# FloodScope AI 🛰️🌊

**Geospatial Disaster-Intelligence Platform for Evidence-Based Flood Impact & Settlement Connectivity Analysis**

*Developed for Multimodal AI Hackathon 2026 — Track B: Mapping Flood Damage from Space*  
*Case Study: August 26, 2026 Trishuli River Basin Flood, Bagmati Province, Nepal*

---

## 1. Project Overview

FloodScope AI provides objective, evidence-based disaster intelligence from space. In rapid-onset Himalayan river floods, rugged terrain and persistent monsoon cloud cover render optical satellite sensors ineffective and sever isolated mountain valleys.

FloodScope AI integrates:
1. **Sentinel-1 C-band SAR Observations (IW GRD):** All-weather day-and-night radar backscatter comparison across matched 12-day orbit geometries (Aug 16 vs Aug 28, 2026).
2. **Terrain Geomorphology (Copernicus WorldDEM-30):** High-resolution digital surface models to filter radar shadow/layover and analyze downstream channel flows.
3. **Pre-Event Infrastructure Overlays (OpenStreetMap via HeiGIT ohsome API):** Strict use of pre-event snapshots (July 27, 2026) to quantify exposed buildings, highway corridors, and river crossings without post-event bias.
4. **Graph-Theoretic Settlement Connectivity (NetworkX):** Topology-based reachability modeling to determine whether mountain settlements have lost all road access to district hospitals and administrative hubs.
5. **Situation-Report Copilot:** English and Nepali situation reports strictly grounded in validated spatial statistics, preventing hallucination through deterministic fallback and LLM schema validation.

---

## 2. Technology Stack

- **Frontend:** React 18, TypeScript, Vite, Tailwind CSS, MapLibre GL JS, Lucide Icons.
- **Backend:** Python 3.12, FastAPI, Pydantic v2, Uvicorn, Requests, HTTPX.
- **Geospatial & Graph Processing:** NetworkX, Shapely, GeoPandas, Rasterio, NumPy, SciPy.
- **Testing & Quality:** Pytest, Pydantic schema validation.
- **Data Integrations:** Copernicus Data Space Ecosystem (CDSE) OData/STAC API, AWS Open Data (Copernicus DEM GLO-30), HeiGIT ohsome API.

---

## 3. Project Directory Structure

```text
FloodScope-AI/
├── .env.example              # Documented configuration template
├── .gitignore                 # Excludes raw SAFE scenes, rasters, secrets, and node_modules
├── README.md                  # Comprehensive project documentation
├── backend/
│   ├── requirements.txt       # Minimal, verified backend dependencies
│   └── app/
│       ├── main.py            # FastAPI application entrypoint with CORS
│       ├── api/
│       │   └── health.py      # GET /api/health endpoint
│       ├── core/
│       │   └── config.py      # Safe settings loader with credential shielding
│       ├── schemas/
│       │   └── health.py      # Strict Pydantic response models
│       ├── services/          # Core pipeline service handlers
│       ├── geospatial/        # Catalog, preprocessing, change detection, and graphs
│       ├── reporting/         # Copilot grounding and English/Nepali templates
│       ├── models/            # Domain entities
│       └── utils/             # Helper utilities
├── frontend/
│   ├── package.json           # Frontend package definitions
│   ├── vite.config.ts         # Vite configuration with backend proxy
│   ├── tailwind.config.js     # Tailwind CSS theme extension
│   └── src/
│       ├── App.tsx            # Main disaster dashboard view
│       ├── main.tsx           # React root
│       ├── types/             # Shared TypeScript schemas
│       ├── services/api.ts    # Backend API client
│       └── components/
│           ├── Header.tsx           # Title, hackathon track, and status pills
│           ├── AreaSelector.tsx     # AOI, date picker, and sensor selection
│           ├── MapWorkspace.tsx     # MapLibre GL JS interactive map
│           ├── SummaryPanel.tsx     # Exposure metrics with explicit empty state
│           ├── ConnectivityPanel.tsx# Settlement reachability graph status
│           ├── CopilotPanel.tsx     # Bilingual Situation-Report Copilot
│           └── ProcessingStatus.tsx # Stage-by-stage pipeline tracking
├── tests/
│   └── unit/
│       └── test_health.py     # Health, schema, and credential-shielding tests
├── data/
│   ├── raw/                   # Raw satellite scenes and OSM extracts (.gitignored)
│   ├── interim/               # Reprojected, cropped intermediate rasters (.gitignored)
│   ├── processed/             # Output flood masks & exposed infrastructure (.gitignored)
│   └── evaluation/            # EMSR927 validation reference data (.gitignored)
├── reports/
│   ├── attribution.md         # Mandatory Copernicus and OpenStreetMap attributions
│   └── limitations.md         # Documented sensor, terrain, and operational caveats
├── docs/                      # Architectural and methodology documentation
└── scripts/                   # Catalog inspection and automation utilities
```

---

## 4. Prerequisites

- **Python:** 3.12.x
- **Node.js:** v22.x or v20.x
- **npm:** 10.x+
- **Git:** 2.x+

---

## 5. Storage Guidance

> [!WARNING]
> Uncompressed Sentinel-1 GRD SAFE archives exceed 1.6 GB each, and SLC scenes exceed 7 GB.
> If your primary system drive has limited space, set `FLOODSCOPE_DATA_DIR` in your `.env` file to point to an external or secondary drive with at least 15 GB free:
> ```env
> FLOODSCOPE_DATA_DIR=D:\FloodScope-Data
> ```

---

## 6. Installation & Launch Commands

### A. Environment Setup
Copy the template configuration:
```bash
cp .env.example .env
```
*(Optionally add your CDSE username/password or Gemini API key. Neither is required to start the system or query the catalog).*

### B. Backend Launch
From the project root:
```bash
# Optional: create a virtual environment
python -m venv .venv
# Activate:
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate

# Install requirements
pip install -r backend/requirements.txt

# Start backend server
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
Verify the health endpoint:
```bash
curl http://127.0.0.1:8000/api/health
```

### C. Frontend Launch
In a separate terminal:
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## 7. Automated Test Suite

Run unit and integration tests with pytest:
```bash
python -m pytest tests/unit/ -v
```

---

## 8. Current Implementation Status (Milestone 1)

- [x] **Milestone 0: Read-Only Audit** — Environment inspected, CDSE catalog queried, exact Sentinel-1 12-day matching pairs (Aug 16 vs Aug 28) identified, ohsome pre-event query validated (45,275 OSM elements).
- [x] **Milestone 1: Project Foundation** — Clean FastAPI backend with credential-shielded `/api/health`, complete React/TypeScript/Tailwind dashboard with MapLibre GL JS, verified automated test suite, storage protection via `FLOODSCOPE_DATA_DIR`.
- [ ] **Milestone 2: Satellite Data Discovery** — Configurable catalog discovery API for Sentinel-1 & Sentinel-2.
- [ ] **Milestone 3: Data Acquisition & Validation** — Authorized CDSE download & SHA-256 verification.
- [ ] **Milestone 4: Geospatial Preprocessing** — Calibration, terrain correction & alignment.
- [ ] **Milestone 5: Flood & Change Analysis** — Radar backscatter thresholding & flood extent.
- [ ] **Milestone 6: Infrastructure Exposure** — Spatial overlay with pre-event OSM buildings, roads, and bridges.
- [ ] **Milestone 7: Settlement Connectivity** — Road graph reachability modeling to healthcare facilities.
- [ ] **Milestone 9: Situation-Report Copilot** — Bilingual English & Nepali grounded situation reports.
- [ ] **Milestone 12: Evaluation** — Strict post-analysis benchmarking against Copernicus EMSR927.

---

## 9. Data Attribution & Compliance

- "Contains modified Copernicus Sentinel data 2026."
- "Produced using Copernicus WorldDEM-30 © DLR e.V. 2010–2014 and © Airbus Defence and Space GmbH 2014–2018 provided under COPERNICUS by the European Union and ESA; all rights reserved."
- "© OpenStreetMap contributors."
- Reference activation EMSR927 data is strictly reserved for post-analysis validation and is never utilized as a prediction input.
