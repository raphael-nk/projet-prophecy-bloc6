from typing import Optional

import pandas as pd
from fastapi import APIRouter, Query

from services.reassort_service import get_categories, get_reassort_df, reload_reassort

router = APIRouter()


def df_to_records(df: pd.DataFrame) -> list:
    """Convertit un DataFrame en liste de dicts pour JSON (NaN/inf → None)."""
    sub = df.replace({float("inf"): None, float("-inf"): None})
    return sub.where(sub.notna(), None).to_dict(orient="records")


@router.get("/stats")
def get_stats():
    """KPIs globaux du réassort."""
    df = get_reassort_df()

    alerts = df["alert"].value_counts().to_dict()
    cycle = df["cycle_status"].value_counts().to_dict()

    n_to_order = int((df["qty_to_order"] > 0).sum())
    total_cost = float(df["estimated_cost"].sum())
    n_rupture = int((df["alert"] == "Rupture imminente").sum())
    n_forte_demande = int((df["alert"] == "Forte demande").sum())
    n_obsolete = int(df["cycle_status"].isin(["Obsolescence", "Inactif"]).sum())
    avg_coverage = (
        float(df[df["coverage_days"] < 999]["coverage_days"].mean())
        if (df["coverage_days"] < 999).any()
        else 0
    )

    return {
        "total_products": len(df),
        "products_to_order": n_to_order,
        "estimated_total_cost": round(total_cost, 0),
        "rupture_imminente": n_rupture,
        "forte_demande": n_forte_demande,
        "obsolete": n_obsolete,
        "avg_coverage_days": round(avg_coverage, 1),
        "alerts": alerts,
        "cycle_status": cycle,
    }


@router.get("/categories")
def list_categories():
    """Liste des catégories."""
    return {"data": get_categories()}


@router.get("/products")
def get_reassort(
    alert: Optional[str] = Query(
        None,
        description="Filtrer par alerte (Rupture imminente, Forte demande, À commander, Stable, Stock OK, Ne pas recommander)",
    ),
    cycle: Optional[str] = Query(
        None, description="Filtrer par cycle (Croissance, Maturité, Déclin, Obsolescence, Inactif)"
    ),
    category_id: Optional[int] = Query(None, description="Filtrer par category_id"),
    min_qty: Optional[int] = Query(None, description="Quantité à commander minimum"),
    limit: int = Query(100, description="Nombre max de résultats"),
    offset: int = Query(0, description="Offset pour pagination"),
):
    """Tableau complet de réassort avec filtres."""
    df = get_reassort_df().copy()

    if alert:
        df = df[df["alert"] == alert]
    if cycle:
        df = df[df["cycle_status"] == cycle]
    if category_id:
        df = df[df["category_id"] == category_id]
    if min_qty is not None:
        df = df[df["qty_to_order"] >= min_qty]

    total = len(df)
    df = df.iloc[offset : offset + limit]

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "data": df_to_records(df),
    }


@router.get("/grouped-reassort")
def get_grouped_reassort():
    """Réassort groupé par alerte."""
    df = get_reassort_df().copy()
    df = (
        df[["alert", "qty_to_order"]]
        .groupby("alert")
        .agg({"qty_to_order": "sum"})
        .reset_index()
        .sort_values("qty_to_order", ascending=False)
    )
    return {"data": df_to_records(df)}


@router.get("/products/{product_id}")
def get_product_reassort(product_id: int):
    """Détail du réassort pour un produit spécifique."""
    df = get_reassort_df()
    df = df[df["product_id"] == product_id]

    if df.empty:
        return {"error": f"Produit {product_id} non trouvé"}

    row = df.iloc[0].to_dict()

    for k, v in row.items():
        if isinstance(v, float) and (pd.isna(v) or v == float("inf")):
            row[k] = None

    return row


@router.get("/alerts")
def get_alerts(
    level: Optional[str] = Query(None, description="Filtrer: Rupture imminente, Forte demande, À commander"),
):
    """Produits en alerte uniquement (à commander)."""
    df = get_reassort_df()
    df = df[df["qty_to_order"] > 0].copy()

    if level:
        df = df[df["alert"] == level]

    return {
        "total": len(df),
        "data": df_to_records(df),
    }


@router.get("/obsolescence")
def get_obsolescence(
    min_score: float = Query(0.5, description="Score minimum d'obsolescence (0-1)"),
):
    """Produits à risque d'obsolescence."""
    df = get_reassort_df()
    df = df[df["obsolescence_score"] >= min_score].copy()
    df = df.sort_values("obsolescence_score", ascending=False)

    return {
        "total": len(df),
        "threshold": min_score,
        "data": df_to_records(df),
    }


@router.post("/reload")
def refresh_reassort():
    """Recalcule le réassort (après mise à jour des données)."""
    reload_reassort()
    df = get_reassort_df()
    return {
        "status": "ok",
        "products": len(df),
        "message": "Réassort recalculé",
    }
