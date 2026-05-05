"""
ArchiText Backend — FastAPI Application

Endpoints:
  POST /api/generate              Submit text for floorplan generation
  GET  /api/status/{job_id}       Poll generation progress
  GET  /api/download/{job_id}     Download generated .ifc file
  GET  /api/preview/{job_id}      Get room summary JSON (for 2D preview)
  GET  /api/health                Health check

Run with:
  cd d:\\Work\\Uni\\FYP\\architext
  .\\venv\\Scripts\\uvicorn backend.main:app --reload --port 8000
"""

# ── Path setup — MUST be first, before any other imports ──────────────────────
import sys
from pathlib import Path

_ROOT        = Path(__file__).parent.parent.resolve()
_SCRIPTS_DIR = _ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
# ──────────────────────────────────────────────────────────────────────────────


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes.generate       import router as generate_router
from backend.api.routes.status         import router as status_router
from backend.api.routes.download       import router as download_router
from backend.api.routes.preview        import router as preview_router
from backend.api.routes.ifc_from_rooms import router as ifc_from_rooms_router
from backend.models.schemas      import HealthResponse
from backend.core.nlp_adapter    import get_nlp_adapter
from backend.core.mock_gnn       import MockGNNAdapter

app = FastAPI(
    title       = "ArchiText API",
    description = "Text-to-BIM pipeline — natural language → IFC floorplan",
    version     = "0.1.0-iteration3",
    docs_url    = "/docs",
    redoc_url   = "/redoc",
)

# CORS — allow all origins in dev (restrict in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# Mount routers
app.include_router(generate_router,       prefix="/api", tags=["Generation"])
app.include_router(status_router,         prefix="/api", tags=["Status"])
app.include_router(download_router,       prefix="/api", tags=["Download"])
app.include_router(preview_router,        prefix="/api", tags=["Preview"])
app.include_router(ifc_from_rooms_router, prefix="/api", tags=["IFC"])


@app.get("/api/health", response_model=HealthResponse, tags=["Health"])
async def health():
    """Check API status and which layers are loaded."""
    nlp       = get_nlp_adapter()
    nlp_ok    = not nlp.is_fallback
    gnn_ready = not MockGNNAdapter.IS_MOCK   # False until real model is loaded

    return HealthResponse(
        status     = "ok",
        nlp_loaded = nlp_ok,
        gnn_ready  = gnn_ready,
    )


@app.get("/", tags=["Root"])
async def root():
    return {
        "name":    "ArchiText API",
        "version": "0.1.0-iteration3",
        "docs":    "/docs",
        "health":  "/api/health",
    }
