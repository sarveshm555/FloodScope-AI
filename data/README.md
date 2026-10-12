# FloodScope AI - Data Directory

This directory stores data assets utilized by FloodScope AI.

- `raw/`: Downloaded satellite scenes (Sentinel-1, Sentinel-2) and pre-event OpenStreetMap extracts.
- `interim/`: Intermediate reprojections, cropped rasters, and filtered radar backscatter.
- `processed/`: Final georeferenced flood masks, exposed infrastructure GeoJSONs, and connectivity graphs.
- `evaluation/`: Copernicus EMSR927 evaluation reference layers (used strictly post-analysis for verification; never as prediction input).

> **Storage Notice**: Raw satellite products can require significant disk space. You can configure `FLOODSCOPE_DATA_DIR` in `.env` to point to a high-capacity drive (such as `D:\FloodScope-Data`).
