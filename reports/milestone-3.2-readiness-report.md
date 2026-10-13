# FloodScope AI — Milestone 3.2 Report: Sentinel-1 Access Validation and DEM Mosaic Readiness

**Date:** October 13, 2026  
**Workspace:** `C:\Users\sarvesh\OneDrive\Desktop\FloodScope-AI`  
**Data Storage:** `D:\FloodScope-Data`  
**Git Commit:** Pending review  

---

## 1. Executive Summary

Milestone 3.2 resolves the core remaining data-readiness and evidence-integrity questions prior to implementing SAR pre-processing or flood detection:
1. **DEM Mosaic Generation and Verification:** Successfully built and verified a persistent, tiled, compressed Cloud-Optimized GeoTIFF DEM mosaic at `D:\FloodScope-Data\processed\dem_mosaic_pilot_aoi.tif` from the two raw Copernicus DEM GLO-30 tiles (`N27_00_E085_00` and `N28_00_E085_00`).
2. **Pixel-Level & Geometric Integrity:** Proved via Rasterio and Shapely that the mosaic covers **100.0000%** of the Trishuli pilot AOI ($85.10^\circ\text{–}85.25^\circ\text{E},\ 27.85^\circ\text{–}28.05^\circ\text{N}$) with **exactly 0 nodata gaps** across all 388,800 elevation pixels within the window.
3. **Sentinel-1 COG & SAFE Access Validation:** Verified live metadata for pre- and post-event candidate acquisitions against the Copernicus Data Space Ecosystem (CDSE). Confirmed that candidate products contain dual-polarization ($\text{VV}+\text{VH}$) in Interferometric Wide (IW) mode on relative orbit 85. Proved that unauthenticated HTTP range requests on CDSE COG products return `HTTP 307` redirecting to an unauthorized endpoint, confirming that CDSE strictly mandates OAuth2 authentication.
4. **Credential Blocker Transparency:** Confirmed that CDSE credentials (`CDSE_USERNAME`/`CDSE_PASSWORD` or `CDSE_CLIENT_ID`/`CDSE_CLIENT_SECRET`) are currently unconfigured in `.env`. In strict adherence to rules, download of the ~1.18 GB COG files was safely stopped, and credentials were not invented or exposed.
5. **Storage, Manifest, and Regression Testing:** Disk space remains safe (C: 5.77 GB free; D: 110.80 GB free). All 3 entries in `data/manifest.json` and `D:\FloodScope-Data\manifest.json` match byte-for-byte with valid SHA-256 hashes. All 36 backend unit tests pass, and frontend production build succeeds with zero errors.

---

## 2. Task 1 — DEM Mosaic Readiness & Pixel-Level Validation

### 2.1 Inspection of Raw Tiles
Both tiles were opened and inspected using Rasterio:

| Property | Tile 1 (`N27_00_E085_00`) | Tile 2 (`N28_00_E085_00`) |
| :--- | :--- | :--- |
| **Path** | `D:\FloodScope-Data\raw\Copernicus_DSM_COG_10_N27_00_E085_00_DEM.tif` | `D:\FloodScope-Data\raw\Copernicus_DSM_COG_10_N28_00_E085_00_DEM.tif` |
| **CRS** | `EPSG:4326` | `EPSG:4326` |
| **Resolution** | $(0.0002778^\circ, 0.0002778^\circ)$ (~30 m) | $(0.0002778^\circ, 0.0002778^\circ)$ (~30 m) |
| **Dimensions** | $3600 \times 3600$ pixels | $3600 \times 3600$ pixels |
| **Bounds (W, S, E, N)** | $[84.999861^\circ, 27.000139^\circ, 85.999861^\circ, 28.000139^\circ]$ | $[84.999861^\circ, 28.000139^\circ, 85.999861^\circ, 29.000139^\circ]$ |
| **NoData Value** | `None` (valid float32 matrix) | `None` (valid float32 matrix) |
| **Valid Data %** | 100.00% (min: 86.5 m, max: 4,461.5 m) | 100.00% (min: 656.5 m, max: 7,920.3 m) |
| **Pilot AOI Overlap** | **75.07%** ($27.85^\circ\text{N}$ to $28.00^\circ\text{N}$) | **24.93%** ($28.00^\circ\text{N}$ to $28.05^\circ\text{N}$) |

### 2.2 Merged Mosaic Verification
Using Rasterio's `merge` module, both tiles were unified and saved to:  
`D:\FloodScope-Data\processed\dem_mosaic_pilot_aoi.tif`

- **Format:** Cloud-Optimized GeoTIFF (Deflate compression, $512 \times 512$ pixel internal tiling, overviews `[2, 4, 8, 16]`).
- **File Size:** 113,448,011 bytes (108.19 MB).
- **Dimensions:** $3600 \times 7200$ pixels.
- **Combined Bounds:** Left: $84.999861^\circ\text{E}$, Bottom: $27.000139^\circ\text{N}$, Right: $85.999861^\circ\text{E}$, Top: $29.000139^\circ\text{N}$.
- **NoData Value:** `-9999.0`.

### 2.3 Pixel-Level Coverage & NoData Analysis Inside Pilot AOI
The Trishuli pilot AOI ($[85.10, 27.85, 85.25, 28.05]$) was extracted via `rasterio.windows.from_bounds`:
- **Window Grid Size:** Rows $3,420$ to $4,140$ ($720$ rows), Columns $360$ to $900$ ($540$ cols).
- **Total Pixels in AOI:** $720 \times 540 = \mathbf{388,800\text{ pixels}}$.
- **Geometric Containment:** **100.0000%** (Polygon strictly enclosed by mosaic bounds).
- **NoData Gaps in AOI:** **0 pixels (0.00%)**.
- **Valid Elevation Pixels in AOI:** **388,800 pixels (100.0000%)**.
- **Elevation Distribution:**
  - Minimum elevation: **454.50 m** (Trishuli riverbed gorge)
  - Maximum elevation: **3,378.85 m** (Surrounding mountain ridgeline)
  - Mean elevation: **1,106.55 m**

---

## 3. Task 2 — Sentinel-1 COG Access Validation & Authentication Blocker

### 3.1 Live Catalog Re-Query Results

| Attribute | Pre-Event Candidate | Post-Event Candidate |
| :--- | :--- | :--- |
| **Observation Timestamp** | `2026-08-16T12:21:41.058Z` | `2026-08-28T12:21:41.762Z` |
| **Orbit & Track** | ASCENDING, Relative Orbit 85 | ASCENDING, Relative Orbit 85 |
| **Sensor Mode** | Interferometric Wide (IW) | Interferometric Wide (IW) |
| **Polarization** | **VV & VH** (Dual-pol required for flood mapping) | **VV & VH** (Dual-pol required for flood mapping) |
| **AOI Coverage** | **100.0%** | **100.0%** |
| **COG Product ID** | `04db2c11-1319-4808-adaa-da7f7ccbbd4f` | `9e6c24a1-24ca-419f-bcec-db66791dcf19` |
| **COG Product Name** | `S1D_IW_GRDH_..._004151_..._B091_COG.SAFE` | `S1D_IW_GRDH_..._004326_..._C73B_COG.SAFE` |
| **COG Archive Size** | 1,240,792,161 bytes (1,183.31 MB) | 1,238,165,967 bytes (1,180.81 MB) |
| **SAFE Alternative ID** | `844b9a32-9aa2-4611-83f6-ae6501c01955` | `9cb3c885-cfb8-40cc-a44a-8673e772c794` |
| **SAFE Archive Size** | 1,732,874,277 bytes (1,652.60 MB) | 1,732,898,724 bytes (1,652.62 MB) |

### 3.2 Authentication & Range Request Testing
- **Test:** Issued HTTP Range request (`bytes=0-1023`) to `https://catalogue.dataspace.copernicus.eu/odata/v1/Products(04db2c11-1319-4808-adaa-da7f7ccbbd4f)/$value` without credentials.
- **Result:** CDSE responded with `HTTP 307 Temporary Redirect` requiring authentication. Unauthenticated requests are rejected.
- **Credential Status:** `CDSE_CLIENT_ID` / `CDSE_CLIENT_SECRET` and `CDSE_USERNAME` / `CDSE_PASSWORD` are **not configured** in the active environment.
- **Decision:** As specified by Milestone 3.2 instructions:
  > *"If credentials are not configured, report that as a blocker and stop before attempting a full download."*
  > *"Never invent successful authentication or data-access results."*  
  Full SAR scene downloads were halted. No mock downloads were generated.

---

## 4. Task 3 — Storage and Manifest Safety

### 4.1 Disk Space Status Immediately After Mosaic Creation
- **Drive `C:`:** **5.77 GB free** (remains protected; no large files written).
- **Drive `D:`:** **110.80 GB free** (`FLOODSCOPE_DATA_DIR` target volume).
- **Drive `E:`:** **120.44 GB free**.

### 4.2 Manifest Verification
The manifest was updated to register the processed DEM mosaic asset alongside the two raw DEM tiles. Both `D:\FloodScope-Data\manifest.json` and [`data/manifest.json`](file:///c:/Users/sarvesh/OneDrive/Desktop/FloodScope-AI/data/manifest.json) were verified using [`scripts/verify_manifest_integrity.py`](file:///c:/Users/sarvesh/OneDrive/Desktop/FloodScope-AI/scripts/verify_manifest_integrity.py):

```
Checking D:/FloodScope-Data/manifest.json (3 products):
  [OK] Copernicus_DSM_COG_10_N27_00_E085_00: size=44874244 bytes, sha256 matches.
  [OK] Copernicus_DSM_COG_10_N28_00_E085_00: size=38402839 bytes, sha256 matches.
  [OK] Copernicus_DSM_GLO_30_Trishuli_Mosaic: size=113448011 bytes, sha256 matches.
Checking data/manifest.json (3 products):
  [OK] Copernicus_DSM_COG_10_N27_00_E085_00: size=44874244 bytes, sha256 matches.
  [OK] Copernicus_DSM_COG_10_N28_00_E085_00: size=38402839 bytes, sha256 matches.
  [OK] Copernicus_DSM_GLO_30_Trishuli_Mosaic: size=113448011 bytes, sha256 matches.

All manifest paths, sizes, and checksums verified against real files on disk!
```

---

## 5. Task 4 — Regression Tests & Build Status

### 5.1 Backend Test Suite
Executed: `python -m pytest tests/unit/ -v`
- **Result:** **36 passed in 2.87s** (0 failures).
- **New Unit Tests Added in [`tests/unit/test_readiness.py`](file:///c:/Users/sarvesh/OneDrive/Desktop/FloodScope-AI/tests/unit/test_readiness.py):**
  1. `test_dem_mosaic_coverage_and_alignment`: Confirms synthetic mosaic creation and geometric containment of pilot AOI.
  2. `test_valid_pixel_vs_geometric_coverage_with_nodata`: Proves detection of nodata holes inside AOI despite 100% geometric polygon overlap.
  3. `test_sentinel1_access_failure_when_credentials_absent`: Verifies that `CDSEAuthClient.get_access_token()` raises `AuthCredentialsMissingError` safely when environment variables are unset.
  4. `test_safe_handling_of_auth_errors_without_leaking_secrets`: Verifies `redact_secrets()` strips passwords, client secrets, and bearer tokens from log messages.

### 5.2 Frontend Build
Executed: `npm run build` in `frontend/`
- **Result:** Completed with **0 errors** (`tsc && vite build` built in 43.67s).

---

## 6. Summary of Deliverables & Blockers

| Milestone Item | Status | Result |
| :--- | :--- | :--- |
| **DEM Mosaic Creation** | COMPLETED | `D:\FloodScope-Data\processed\dem_mosaic_pilot_aoi.tif` (108.2 MB, COG). |
| **Geometric Coverage** | COMPLETED | 100.0000% containment of Trishuli pilot AOI. |
| **Valid Pixel Coverage** | COMPLETED | 100.0000% (388,800/388,800 pixels); 0 nodata gaps. |
| **S1 Candidates Validated** | COMPLETED | Verified dual-pol ($\text{VV}+\text{VH}$), track 85, 12-day repeat, 100% overlap. |
| **CDSE Credentials** | BLOCKED | Credentials not configured in `.env`; downloads safely paused. |
| **Manifest Integrity** | COMPLETED | 3 assets verified by size and SHA-256 in external and tracked manifests. |
| **Test Suite** | COMPLETED | 36/36 unit tests passed; frontend production build passed. |

### Remaining Blocker:
To acquire the candidate Sentinel-1 COG or SAFE products from Copernicus Data Space Ecosystem, valid credentials (`CDSE_CLIENT_ID` / `CDSE_CLIENT_SECRET` or `CDSE_USERNAME` / `CDSE_PASSWORD`) must be added to `.env`. Once provided, `SafeDownloadManager` can authenticate and download the pre/post SAR scenes directly into `D:\FloodScope-Data\raw\`.
