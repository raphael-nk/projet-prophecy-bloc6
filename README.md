# Prophecy — Plateforme unifiée

**Prophecy** est la plateforme d'aide à la décision de **Nexthope** : elle combine deux briques ML — **réassort prédictif** (XGBoost) et **segmentation clients** (RFM + KMeans) — derrière une **API FastAPI** et un **dashboard Streamlit**.

Projet présenté lors des **Demo Days Jedha** pour répondre aux défis opérationnels des **sites e-commerce** : réassort de stock et commandes fournisseurs souvent passées **à l'aveugle**, faute de visibilité sur la demande future. Prophecy **collecte les données d'activité** (ventes, stock, clients) et **prédit / anticipe** les besoins pour piloter les décisions.

## Liens

| Environnement | URL |
|---------------|-----|
| **Production** (dashboard) | [https://prophecy.origino.app/](https://prophecy.origino.app/) |
| **MLflow** (expériences & modèles) | [https://stephane-nxt-demodaymlflow.hf.space/](https://stephane-nxt-demodaymlflow.hf.space/) |

## Auteurs

- Henintsoa HASINAVALONA
- Raphaël RANJAKASOA
- Stéphane CHAN HIOU KONG
- Rindra RAMILIARIJAONA

## Cœur du projet

| Brique | Modèle / méthode | Rôle |
|--------|------------------|------|
| **Réassort** | XGBoost (`xgboost_30d_final.pkl`) | Prédit la demande sur 30 jours par produit, calcule stock de sécurité, couverture et quantités à commander |
| **Segmentation** | RFM + KMeans (`kmeans_bundle_v1.joblib`) | Segmente les clients (Champions, Fidèles, À risque…), profils d'intérêts et recommandations macro-catégories |

**Flux de données :**

```
data/ (CSV)  →  train/ (notebooks + predict.py)  →  models/ (artefacts ML)
                                                        ↓
                                              api/ (FastAPI, cache au démarrage)
                                                        ↓
                                              streamlit/ (dashboard consommateur)
```

- L'**API** pré-calcule le réassort au démarrage (1 à 3 min) pour des réponses instantanées ensuite.
- Le **dashboard** ne fait aucun calcul ML : il interroge l'API via `streamlit/api_client.py`.

## Structure

```
projet-prophecy-bloc6/
├── api/
│   ├── main.py                 # Point d'entrée FastAPI + warm-up réassort
│   ├── routers/
│   │   ├── reassort.py         # Endpoints /reassort/*
│   │   └── segmentation.py     # Endpoints /segmentation/*
│   └── services/               # Logique métier (cache, chargement modèles)
├── streamlit/
│   ├── app.py                  # Navigation multipage (st.navigation)
│   ├── dashboard_page.py       # Tableau de bord — KPIs globaux
│   ├── reassort_page.py        # Tableau réassort + alertes
│   ├── segmentation_page.py    # Segments RFM & profils clients
│   └── api_client.py           # Client HTTP vers l'API
├── train/
│   ├── reassort/               # Notebooks + predict.py (pipeline réassort)
│   └── segmentation/           # Notebooks RFM & KMeans
├── models/                     # xgboost_30d_final.pkl, kmeans_bundle_v1.joblib
├── data/                       # CSV sources (ventes, stock, RFM, reco…)
└── docker-compose.yml
```

## Démarrage rapide

```bash
docker compose up --build
```

Attendre le message **`Réassort prêt`** dans les logs de l'API avant d'utiliser le dashboard réassort.

| Service | URL (local) |
|---------|-------------|
| API (Swagger) | http://localhost:8000/docs |
| Dashboard | http://localhost:8501 |

> Version déployée en production : [https://prophecy.origino.app/](https://prophecy.origino.app/)

### Pages Streamlit

| Page | Route |
|------|-------|
| Tableau de bord | `/` |
| Réassort | `/reassort` |
| Segmentation RFM & Profils | `/segmentation` |

## API — endpoints principaux

**Système**

- `GET /health` — statut + `reassort_ready`

**Réassort** (`/reassort`)

- `GET /stats` — KPIs globaux (ruptures, coût estimé, couverture…)
- `GET /categories` — liste des catégories
- `GET /products` — tableau réassort (filtres : catégorie, alerte, recherche)
- `GET /alerts` — produits en alerte
- `GET /obsolescence` — produits obsolètes / inactifs
- `POST /reload` — recalcul du cache réassort

**Segmentation** (`/segmentation`)

- `GET /segments` — répartition par segment RFM
- `GET /dashboard/kpis` — KPIs clients (panier moyen, champions, B2B…)
- `GET /customers` — liste paginée des clients
- `GET /customers/{partner_id}` — fiche client
- `GET /clusters` — résumé des clusters KMeans
- `GET /reco/customers` — recommandations par client
- `POST /reload` — rechargement des CSV / modèle

## Vérifications rapides

```bash
curl http://localhost:8000/health
curl http://localhost:8000/reassort/stats
curl http://localhost:8000/segmentation/segments
curl http://localhost:8000/segmentation/clusters
```

## Variables d'environnement

| Variable | Description | Défaut (Docker) |
|----------|-------------|-----------------|
| `DATA_DIR` | Répertoire des CSV | `/app/data` |
| `MODELS_DIR` | Répertoire des modèles | `/app/models` |
| `TRAIN_DIR` | Répertoire train (predict.py) | `/app/train` |
| `MODEL_REASSORT` | Modèle XGBoost | `/app/models/xgboost_30d_final.pkl` |
| `MODEL_SEGMENTATION` | Bundle KMeans joblib | `/app/models/kmeans_bundle_v1.joblib` |
| `RFM_SEGMENTS_CSV` | Export segments RFM | `/app/data/rfm_segments.csv` |
| `CUSTOMER_RECOMMENDATION_CSV` | Export reco KMeans | `/app/data/customer_recommendation.csv` |
| `API_URL` | URL de l'API pour Streamlit | `http://api:8000` |

## Développement local

**API**

```bash
cd api
pip install -r requirements.txt
export DATA_DIR=../data TRAIN_DIR=../train MODEL_REASSORT=../models/xgboost_30d_final.pkl
uvicorn main:app --reload --port 8000
```

**Dashboard**

```bash
cd streamlit
pip install streamlit pandas numpy plotly requests
export API_URL=http://localhost:8000
streamlit run app.py
```

## Données & modèles

Les notebooks dans `train/` produisent les artefacts consommés par l'API :

- **Réassort** : `train/reassort/final_main.ipynb` → `models/xgboost_30d_final.pkl`
- **Segmentation** : `train/segmentation/rfm_segment.ipynb` + `train_kmeans.ipynb` → CSV + `models/kmeans_bundle_v1.joblib`

Pour régénérer les prédictions réassort en CLI :

```bash
cd train/reassort
python predict.py
```
