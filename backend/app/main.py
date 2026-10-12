from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.api.health import router as health_router

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
