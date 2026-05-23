# Prophecy — Plateforme unifiée

Réassort XGBoost + segmentation RFM/KMeans, exposés via **une API FastAPI** et **un dashboard Streamlit**.

## Structure

```
prophecy/
├── api/              # API unifiée (routers /reassort et /segmentation)
├── streamlit/        # Dashboard multipage
├── train/            # Notebooks et predict.py (logique ML inchangée)
├── models/           # Artefacts ML (.pkl, .joblib)
├── data/             # CSV sources
└── docker-compose.yml
```

## Démarrage rapide

```bash
cd prophecy
docker compose up --build
```

- API : http://localhost:8000/docs
- Dashboard : http://localhost:8501

## Vérifications

```bash
curl http://localhost:8000/health
curl http://localhost:8000/reassort/stats
curl http://localhost:8000/segmentation/segments
curl http://localhost:8000/segmentation/clusters
```

## Variables d'environnement

| Variable | Description |
|----------|-------------|
| `DATA_DIR` | Répertoire des CSV |
| `MODELS_DIR` | Répertoire des modèles |
| `MODEL_REASSORT` | Chemin du modèle XGBoost |
| `MODEL_SEGMENTATION` | Bundle KMeans joblib |
| `RFM_SEGMENTS_CSV` | Export RFM |
| `CUSTOMER_RECOMMENDATION_CSV` | Export reco KMeans |
| `API_URL` | URL de l'API pour Streamlit (ex. `http://api:8000`) |

## Développement local (API)

```bash
cd api
pip install -r requirements.txt
export DATA_DIR=../data TRAIN_DIR=../train MODEL_REASSORT=../models/xgboost_30d_final.pkl
uvicorn main:app --reload --port 8000
```
