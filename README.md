<p align="center">
  <img src="streamlit/img/prophecy_logo.png" alt="Logo Prophecy" width="100%">
</p>

# Projet Prophecy — Plateforme de réassort prédictif et segmentation clients

**Bloc 6 — Projet Final (Lead)** · Certification RNCP CDSD — Jedha

## Accès en ligne (production)

> **Pour le jury** — application et tracking ML consultables en ligne :

| Service | URL |
|---------|-----|
| **Dashboard (production)** | [prophecy.origino.app](https://prophecy.origino.app/) |
| **MLflow (expériences)** | [stephane-nxt-demodaymlflow.hf.space](https://stephane-nxt-demodaymlflow.hf.space/) |

---

**Prophecy** est la plateforme d'aide à la décision de **Nexthope** : elle combine deux briques ML — **réassort prédictif** (XGBoost) et **segmentation clients** (RFM + KMeans) — derrière une **API FastAPI** et un **dashboard Streamlit**. Présentée lors des Demo Days Jedha, elle répond aux défis opérationnels des sites e-commerce : commandes fournisseurs passées à l'aveugle, faute de visibilité sur la demande future.

## Objectifs

- Prédire la demande sur 30 jours par produit et calculer les quantités à commander (réassort)
- Segmenter les clients par comportement d'achat (RFM + KMeans)
- Exposer les résultats via une API et un dashboard interactif
- Déployer la solution en production (Docker Compose)

## Jeu de données

| Élément | Détail |
|---------|--------|
| Ventes | `data/sales_enriched.csv`, `data/sales_step4_b2c.csv` |
| Stock | `data/products_stock.csv` |
| Fournisseurs | `data/suppliers.csv` |
| Segments RFM | `data/rfm_segments.csv` |
| Recommandations | `data/customer_recommendation.csv` |

## Structure du projet

```text
projet-prophecy-bloc6/
├── api/
│   ├── main.py
│   ├── routers/
│   │   ├── reassort.py
│   │   └── segmentation.py
│   ├── services/
│   │   ├── reassort_service.py
│   │   └── segmentation_service.py
│   ├── Dockerfile
│   └── requirements.txt
├── streamlit/
│   ├── app.py
│   ├── dashboard_page.py
│   ├── reassort_page.py
│   ├── segmentation_page.py
│   ├── api_client.py
│   ├── formatting.py
│   ├── prophecy_styles.css
│   ├── img/
│   ├── .streamlit/config.toml
│   └── Dockerfile
├── train/
│   ├── reassort/
│   │   ├── first_main.ipynb
│   │   ├── secod_rolling_main.ipynb
│   │   ├── final_main.ipynb
│   │   └── predict.py
│   └── segmentation/
│       ├── rfm_segment.ipynb
│       └── train_kmeans.ipynb
├── models/
│   ├── xgboost_30d_final.pkl
│   └── kmeans_bundle_v1.joblib
├── data/
├── docker-compose.yml
├── .gitignore
├── .python-version
├── pyproject.toml
├── LICENSE
└── README.md
```

## Architecture

```text
data/ (CSV)  →  train/ (notebooks + predict.py)  →  models/ (artefacts ML)
                                                        ↓
                                              api/ (FastAPI, cache au démarrage)
                                                        ↓
                                              streamlit/ (dashboard consommateur)
```

| Brique | Modèle / méthode | Rôle |
|--------|------------------|------|
| Réassort | XGBoost (`xgboost_30d_final.pkl`) | Prédit la demande sur 30 jours, calcule stock de sécurité, couverture et quantités à commander |
| Segmentation | RFM + KMeans (`kmeans_bundle_v1.joblib`) | Segmente les clients (Champions, Fidèles, À risque…), profils d'intérêts et recommandations |

L'API pré-calcule le réassort au démarrage (1 à 3 min) pour des réponses instantanées. Le dashboard ne fait aucun calcul ML : il interroge l'API via `api_client.py`.

## API — Endpoints principaux

**Système**

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/health` | GET | Statut + `reassort_ready` |

**Réassort** (`/reassort`)

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/stats` | GET | KPIs globaux (ruptures, coût estimé, couverture) |
| `/categories` | GET | Liste des catégories |
| `/products` | GET | Tableau réassort (filtres : catégorie, alerte, recherche) |
| `/alerts` | GET | Produits en alerte |
| `/obsolescence` | GET | Produits obsolètes / inactifs |
| `/reload` | POST | Recalcul du cache réassort |

**Segmentation** (`/segmentation`)

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/segments` | GET | Répartition par segment RFM |
| `/dashboard/kpis` | GET | KPIs clients (panier moyen, champions, B2B) |
| `/customers` | GET | Liste paginée des clients |
| `/customers/{partner_id}` | GET | Fiche client |
| `/clusters` | GET | Résumé des clusters KMeans |
| `/reco/customers` | GET | Recommandations par client |
| `/reload` | POST | Rechargement des CSV / modèle |

### Vérification rapide

```bash
curl http://localhost:8000/health
curl http://localhost:8000/reassort/stats
curl http://localhost:8000/segmentation/segments
```

## Méthodologie ML

### Réassort prédictif

Notebooks dans `train/reassort/` : exploration des ventes, feature engineering temporel (rolling windows), entraînement XGBoost sur la demande à 30 jours. Script `predict.py` pour régénérer les prédictions en CLI.

### Segmentation clients

Notebooks dans `train/segmentation/` : calcul des scores RFM (Récence, Fréquence, Montant), clustering KMeans, attribution de segments (Champions, Fidèles, À risque, etc.), recommandations par macro-catégorie.

## Installation locale

### Prérequis

- **Docker** + **Docker Compose**

### Démarrage rapide

```bash
docker compose up --build
```

Attendre le message **`Réassort prêt`** dans les logs de l'API avant d'utiliser le dashboard réassort.

| Service | URL locale |
|---------|-----------|
| API (Swagger) | [http://localhost:8000/docs](http://localhost:8000/docs) |
| Dashboard | [http://localhost:8501](http://localhost:8501) |

### Développement sans Docker

**API :**

```bash
cd api
pip install -r requirements.txt
export DATA_DIR=../data TRAIN_DIR=../train MODEL_REASSORT=../models/xgboost_30d_final.pkl
uvicorn main:app --reload --port 8000
```

**Dashboard :**

```bash
cd streamlit
pip install streamlit pandas numpy plotly requests
export API_URL=http://localhost:8000
streamlit run app.py
```

## Configuration

| Variable | Description | Défaut (Docker) |
|----------|-------------|-----------------|
| `DATA_DIR` | Répertoire des CSV | `/app/data` |
| `MODELS_DIR` | Répertoire des modèles | `/app/models` |
| `TRAIN_DIR` | Répertoire train (predict.py) | `/app/train` |
| `MODEL_REASSORT` | Modèle XGBoost | `/app/models/xgboost_30d_final.pkl` |
| `MODEL_SEGMENTATION` | Bundle KMeans | `/app/models/kmeans_bundle_v1.joblib` |
| `API_URL` | URL de l'API pour Streamlit | `http://api:8000` |

## Stack technique

- **Python 3.11+**
- **XGBoost** · **scikit-learn** — modèles ML
- **FastAPI** · **Uvicorn** — API backend
- **Streamlit** — dashboard interactif
- **Docker Compose** — orchestration des services
- **MLflow** — tracking des expériences

## Limites et pistes d'amélioration

### Limites

- Le réassort est pré-calculé au démarrage, ce qui impose un cold start de 1 à 3 min
- La segmentation est statique (recalcul manuel via `/reload`)
- Le projet est monolithique (pas de CI/CD)

### Pistes

- Automatiser le réentraînement périodique des modèles
- Ajouter des alertes push (email/Slack) pour les ruptures de stock
- Implémenter un cache Redis pour réduire le cold start
- Ajouter des tests unitaires et d'intégration
- Mettre en place un pipeline CI/CD

## Auteurs

- **RANJAKASOA Raphaël Marcellin**
- Henintsoa HASINAVALONA
- Stéphane CHAN HIOU KONG
- Rindra RAMILIARIJAONA

Projet réalisé dans le cadre du **Bloc 6 — Projet Final (Lead & Demo Day)**, certification **RNCP CDSD**, **Jedha Bootcamp**.
