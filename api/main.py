from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import reassort, segmentation

app = FastAPI(
    title="Prophecy API",
    description="Réassort XGBoost + Segmentation KMeans — Nexthope",
    version="2.0.0",
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
    return {"status": "ok", "version": "2.0.0"}


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
