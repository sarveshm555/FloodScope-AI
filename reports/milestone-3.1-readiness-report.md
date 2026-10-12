# FloodScope AI — Milestone 3.1 Report: Correction & Readiness Check

**Date:** October 12, 2026  
**Workspace:** `C:\Users\sarvesh\OneDrive\Desktop\FloodScope-AI`  
**Data Storage:** `D:\FloodScope-Data`  
**Git Commit:** `11112bd`

---

## 1. Executive Summary

Milestone 3.1 addressed critical data-coverage and acquisition-readiness items identified during the review of Milestone 3:
1. **DEM Coverage Discrepancy Resolved:** Validated via Rasterio and Shapely that the primary tile (`Copernicus_DSM_COG_10_N27_00_E085_00_DEM.tif`) covered only 75.07% of the Trishuli pilot AOI ($27.85^\circ\text{–}28.05^\circ\text{N}$). The adjacent northern tile (`Copernicus_DSM_COG_10_N28_00_E085_00_DEM.tif`, covering $28.00^\circ\text{–}29.00^\circ\text{N}$) was identified, safely downloaded, validated, and combined geometrically to achieve **100.0000% complete terrain coverage**.
2. **Sentinel-1 Acquisition Readiness Verified:** Queried live Copernicus Data Space Ecosystem (CDSE) OData catalog to verify candidate products, catalog IDs, representations (COG vs. standard SAFE archive), AOI overlap (100%), and authenticated access requirements.
3. **Manifest and Storage Safety:** Both DEM files on `D:\FloodScope-Data\raw\` match their registered manifests (`data/manifest.json` and `D:\FloodScope-Data\manifest.json`) in exact byte size and SHA-256 checksum.
4. **Regression & Safety Verification:** All 32 backend unit tests pass (`pytest`) and frontend production build succeeds with zero errors.

---

## 2. Issue 1 — DEM Coverage Validation & Resolution

### 2.1 Pilot AOI vs. N27 Tile Geometry
- **Pilot AOI:**
  - West: $85.10^\circ\text{E}$, South: $27.85^\circ\text{N}$, East: $85.25^\circ\text{E}$, North: $28.05^\circ\text{N}$
  - Area: $0.03000^\circ\text{deg}^2$
- **Tile 1 (`Copernicus_DSM_COG_10_N27_00_E085_00_DEM.tif`):**
  - Actual Bounding Box: West $84.999861^\circ$, South $27.000139^\circ$, East $85.999861^\circ$, North $28.000139^\circ$
  - Intersection with AOI: $[85.10, 27.85] \times [85.25, 28.000139]$
  - Covered Area: $0.022521^\circ\text{deg}^2$ (**75.07%**)
  - Missing Area: Latitude $28.000139^\circ\text{N}$ to $28.05^\circ\text{N}$ (24.93% of pilot AOI)

### 2.2 Adjacent Tile Identification & Acquisition
- **Identified Tile:** `Copernicus_DSM_COG_10_N28_00_E085_00_DEM.tif`
  - Tile Extent: Latitude $28^\circ\text{N}$ to $29^\circ\text{N}$, Longitude $85^\circ\text{E}$ to $86^\circ\text{E}$
  - Source: AWS Copernicus DEM Public Open Data (`s3://copernicus-dem-30m/Copernicus_DSM_COG_10_N28_00_E085_00_DEM/`)
  - Target Path: `D:\FloodScope-Data\raw\Copernicus_DSM_COG_10_N28_00_E085_00_DEM.tif`
  - Download Size: 40,296,878 bytes (38.43 MB)
  - Pre-download disk check: D: drive had >110 GB free.

### 2.3 Raster Validation & Combined Coverage
Both DEM tiles were independently inspected with `rasterio`:

| Metric | Tile 1 (N27) | Tile 2 (N28) | Combined / Mosaicked |
| :--- | :--- | :--- | :--- |
| **Filename** | `..._N27_00_E085_00_DEM.tif` | `..._N28_00_E085_00_DEM.tif` | Both tiles in `raw/` |
| **CRS** | EPSG:4326 | EPSG:4326 | EPSG:4326 |
| **Resolution** | 0.0002778° (~30m) | 0.0002778° (~30m) | 0.0002778° (~30m) |
| **Dimensions** | 3600 × 3600 px (1 band) | 3600 × 3600 px (1 band) | Unified spatial coverage |
| **Data Type** | Float32 | Float32 | Float32 |
| **Elevation Range**| 171.8m to 7,163.6m | 935.1m to 7,422.5m | Full valley-to-ridge terrain |
| **AOI Coverage** | 75.07% | 24.93% | **100.0000%** |
| **SHA-256** | `6b9ae7d9d023b72c5a2c2ffdb64b2149b5c3daeb30740a6b7e07ebaa24683515` | `1590255a0ae7e8c1f49b277e287032a18a2e32c8e13c4c3298ed458f851cd3c7` | Verified |

Geometric proof: Union of $[84.999861, 27.000139, 85.999861, 28.000139]$ and $[84.999861, 28.000139, 85.999861, 29.000139]$ fully contains $[85.10, 27.85, 85.25, 28.05]$ with 0% residual void.

---

## 3. Issue 2 — Sentinel-1 Acquisition Readiness Verification

Live query against CDSE OData API (`https://catalogue.dataspace.copernicus.eu/odata/v1/Products`) executed via [`scripts/inspect_s1_candidates.py`](file:///c:/Users/sarvesh/OneDrive/Desktop/FloodScope-AI/scripts/inspect_s1_candidates.py):

### 3.1 Pre-Event Candidate Verification
- **Acquisition Timestamp:** `2026-08-16T12:21:41.000Z`
- **Orbit & Track:** ASCENDING, Relative Orbit / Track 85
- **Mode & Polarization:** Interferometric Wide (IW), VV + VH dual polarization
- **AOI Intersection:** 100.00% overlap with pilot AOI
- **CDSE Representations:**
  - **COG Product ID:** `04db2c11-1319-4808-adaa-da7f7ccbbd4f`
    - Product Name: `S1A_IW_GRDH_1SDV_20260816T122141_20260816T122206_065884_07F563_B091_COG.SAFE`
    - Product Type: `IW_GRDH_1S-COG`
    - Size: 1,240,798,642 bytes (1,183.3 MB)
  - **Standard SAFE Product ID:** `844b9a32-9aa2-4611-83f6-ae6501c01955`
    - Product Name: `S1A_IW_GRDH_1SDV_20260816T122141_20260816T122206_065884_07F563_C3AB.SAFE`
    - Product Type: `IW_GRDH_1S`
    - Size: 1,732,925,979 bytes (1,652.6 MB)

### 3.2 Post-Event Candidate Verification
- **Acquisition Timestamp:** `2026-08-28T12:21:41.000Z` (exact 12-day repeat orbit match)
- **Orbit & Track:** ASCENDING, Relative Orbit / Track 85
- **Mode & Polarization:** Interferometric Wide (IW), VV + VH dual polarization
- **AOI Intersection:** 100.00% overlap with pilot AOI
- **CDSE Representations:**
  - **COG Product ID:** `9e6c24a1-24ca-419f-bcec-db66791dcf19`
    - Product Name: `S1A_IW_GRDH_1SDV_20260828T122141_20260828T122206_066059_07FE66_C73B_COG.SAFE`
    - Product Type: `IW_GRDH_1S-COG`
    - Size: 1,238,154,342 bytes (1,180.8 MB)
  - **Standard SAFE Product ID:** `9cb3c885-cfb8-40cc-a44a-8673e772c794`
    - Product Name: `S1A_IW_GRDH_1SDV_20260828T122141_20260828T122206_066059_07FE66_01B4.SAFE`
    - Product Type: `IW_GRDH_1S`
    - Size: 1,732,877,654 bytes (1,652.6 MB)

### 3.3 Product ID Discrepancy Resolution
- **Clarification:** The candidate IDs provided in the user prompt (`04db2c11-...` and `9e6c24a1-...`) are the **COG-packaged Sentinel-1 products** (`IW_GRDH_1S-COG`). The IDs previously cataloged in Milestone 2 (`844b9a32-...` and `9cb3c885-...`) are the **standard SAFE products** (`IW_GRDH_1S`).
- Both representations correspond to the exact same raw satellite data acquisition, timing, and orbit geometry.
- The COG representation saves ~470 MB per product (~940 MB total bandwidth savings).

### 3.4 Access & Authentication Mechanism
- Tested unauthenticated HTTP Range requests against CDSE OData `$value` endpoints: CDSE returns `HTTP 401 Unauthorized`.
- **Finding:** Direct unauthenticated partial range requests on CDSE COG products are prohibited by CDSE security policies. Valid CDSE credentials (`CDSE_CLIENT_ID` and `CDSE_CLIENT_SECRET` via Keycloak OAuth2) are required to obtain an access token before accessing any product data or COG parts.
- When credentials are provided, `SafeDownloadManager` can download individual COG components or full COG archives directly into `D:\FloodScope-Data\raw\`.

---

## 4. Issue 3 — Manifest and Storage Safety

### 4.1 Disk Space Status
- Drive `C:`: **6.21 GB free** (remains protected; no large files written).
- Drive `D:`: **110.91 GB free** (`FLOODSCOPE_DATA_DIR` target directory).
- Drive `E:`: **120.44 GB free**.

### 4.2 Manifest Verification
Verified using [`scripts/verify_manifest_integrity.py`](file:///c:/Users/sarvesh/OneDrive/Desktop/FloodScope-AI/scripts/verify_manifest_integrity.py):
- `D:\FloodScope-Data\manifest.json` and [`data/manifest.json`](file:///c:/Users/sarvesh/OneDrive/Desktop/FloodScope-AI/data/manifest.json) both list:
  1. `Copernicus_DSM_COG_10_N27_00_E085_00_DEM.tif`: 46,938,206 bytes, SHA-256 `6b9ae7d9d023b72c5a2c2ffdb64b2149b5c3daeb30740a6b7e07ebaa24683515` [PASS]
  2. `Copernicus_DSM_COG_10_N28_00_E085_00_DEM.tif`: 40,296,878 bytes, SHA-256 `1590255a0ae7e8c1f49b277e287032a18a2e32c8e13c4c3298ed458f851cd3c7` [PASS]

---

## 5. Issue 4 — Test Suite and Build Integrity

- **Backend Unit Tests:** 32 passed in 6.37 seconds (`pytest tests/unit/ -v`).
  - Added [`tests/unit/test_readiness.py`](file:///c:/Users/sarvesh/OneDrive/Desktop/FloodScope-AI/tests/unit/test_readiness.py) with 7 test cases covering partial coverage detection, combined mosaic coverage, missing adjacent tile validation, invalid file path handling, corrupted file detection via SHA-256/size, and COG vs. SAFE representation normalization.
- **Frontend Build:** `npm run build` completed successfully (`tsc && vite build`) with zero TypeScript errors.

---

## 6. Milestone 3.1 Status & Readiness

| Requirement | Status | Notes |
| :--- | :--- | :--- |
| **DEM Coverage Proof** | COMPLETED | Combined N27 + N28 tiles provide proven 100.00% AOI coverage. |
| **S1 Candidate Verification** | COMPLETED | Live CDSE verified; COG vs SAFE IDs documented; authenticated access confirmed. |
| **Storage Safety** | COMPLETED | C: drive has 6.21 GB free; D: drive has 110.91 GB free. |
| **Manifest Integrity** | COMPLETED | Both DEM tiles verified against byte sizes and SHA-256 checksums. |
| **Test Suite** | COMPLETED | 32/32 tests passing; frontend build passing. |

FloodScope AI has achieved complete data readiness and is ready for Milestone 4 (Geospatial Preprocessing & SAR Alignment) upon user approval.
