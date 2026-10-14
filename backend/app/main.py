from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.api.health import router as health_router
from backend.app.api.catalog import router as catalog_router
from backend.app.api.downloads import router as downloads_router
from backend.app.api.analysis import router as analysis_router

app = FastAPI(
    title="FloodScope AI Backend",
    description=(
        "Geospatial disaster-intelligence platform providing evidence-based "
        "satellite flood mapping, infrastructure exposure, and settlement connectivity analysis."
    ),
    version=settings.version,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    settings.frontend_url,
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(health_router, prefix="/api", tags=["System Health"])
app.include_router(catalog_router, prefix="/api/catalog", tags=["Satellite Discovery"])
app.include_router(downloads_router, prefix="/api/downloads", tags=["Data Acquisition"])
app.include_router(analysis_router, prefix="/api/analysis", tags=["Geospatial Analysis"])


@app.get("/")
def root_redirect():
    return {
        "message": "FloodScope AI Backend Operational",
        "documentation": "/docs",
        "health": "/api/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=settings.api_host, port=settings.api_port, reload=True)
