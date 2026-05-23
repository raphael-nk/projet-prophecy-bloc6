import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import reassort, segmentation
from services.reassort_service import is_reassort_ready, warm_reassort_cache

log = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Pré-charge le réassort XGBoost avant d'accepter le trafic (sinon /stats bloque 2–3 min)."""
    log.info("Pré-calcul du réassort XGBoost en cours (1 à 3 min au premier démarrage)…")
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, warm_reassort_cache)
    log.info("Réassort prêt — cache chargé (%s produits).", "ok" if is_reassort_ready() else "?")
    yield


app = FastAPI(
    title="Prophecy API",
    description="Réassort XGBoost + Segmentation KMeans — Nexthope",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(reassort.router, prefix="/reassort", tags=["Réassort"])
app.include_router(segmentation.router, prefix="/segmentation", tags=["Segmentation"])


@app.get("/health", tags=["Système"])
def health():
    return {
        "status": "ok",
        "version": "2.0.0",
        "reassort_ready": is_reassort_ready(),
    }


@app.get("/", tags=["Système"])
def root():
    return {
        "docs": "/docs",
        "reassort": [
            "/reassort/stats",
            "/reassort/products",
            "/reassort/alerts",
            "/reassort/obsolescence",
        ],
        "segmentation": [
            "/segmentation/customers",
            "/segmentation/segments",
            "/segmentation/clusters",
            "/segmentation/reco/customers",
        ],
    }
