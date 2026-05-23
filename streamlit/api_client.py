"""Client HTTP vers l'API Prophecy (timeouts + cache Streamlit)."""

from __future__ import annotations

import os
from typing import Any

import pandas as pd
import requests
import streamlit as st

API_URL = os.environ.get("API_URL", "http://localhost:8000").rstrip("/")
REASSORT_API = f"{API_URL}/reassort"
SEG_API = f"{API_URL}/segmentation"

# (connexion, lecture) — la 1ère requête /reassort/stats peut prendre ~2–3 min (XGBoost)
CONNECT_TIMEOUT = 5
READ_TIMEOUT_STATS = 300
READ_TIMEOUT_DEFAULT = 60


def _get(url: str, *, read_timeout: int = READ_TIMEOUT_DEFAULT, **kwargs) -> requests.Response:
    return requests.get(
        url,
        timeout=(CONNECT_TIMEOUT, read_timeout),
        **kwargs,
    )


def api_reachable() -> bool:
    try:
        r = _get(f"{API_URL}/health", read_timeout=5)
        return r.status_code == 200
    except requests.RequestException:
        return False


def reassort_ready() -> bool:
    try:
        r = _get(f"{API_URL}/health", read_timeout=5)
        if r.status_code != 200:
            return False
        return bool(r.json().get("reassort_ready"))
    except requests.RequestException:
        return False


@st.cache_data(ttl=300, show_spinner=False)
def get_reassort_stats() -> dict[str, Any]:
    r = _get(f"{REASSORT_API}/stats", read_timeout=READ_TIMEOUT_STATS)
    r.raise_for_status()
    return r.json()


@st.cache_data(ttl=300, show_spinner=False)
def get_reassort_categories() -> list[dict[str, Any]]:
    r = _get(f"{REASSORT_API}/categories")
    r.raise_for_status()
    return r.json()["data"]


@st.cache_data(ttl=120, show_spinner=False)
def get_reassort_products(
    category_id: int | None,
    alert: str | None,
    cycle: str | None,
    min_qty: int,
    limit: int,
    offset: int,
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "limit": limit,
        "offset": offset,
    }
    if min_qty and min_qty > 0:
        params["min_qty"] = min_qty
    if category_id is not None:
        params["category_id"] = category_id
    if alert:
        params["alert"] = alert
    if cycle:
        params["cycle"] = cycle
    r = _get(f"{REASSORT_API}/products", params=params, read_timeout=READ_TIMEOUT_DEFAULT)
    r.raise_for_status()
    return r.json()


@st.cache_data(ttl=300, show_spinner=False)
def get_segmentation_kpis() -> dict[str, Any]:
    r = _get(f"{SEG_API}/dashboard/kpis")
    if r.status_code != 200:
        return {}
    return r.json()


@st.cache_data(ttl=300, show_spinner=False)
def get_segmentation_segments() -> dict[str, Any]:
    r = _get(f"{SEG_API}/segments")
    r.raise_for_status()
    return r.json()


def products_to_dataframe(data: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for item in data.get("data", []):
        rows.append(
            {
                "Article": item["product_name"],
                "Ventes prévues en 30 jours": item["ventes_prevues_30j"],
                "Quantité en stock": item["qty_available"],
                "Quantité à commander": item["qty_to_order"],
                "Etat de l'article": item["cycle_status"],
                "Etat du stock": item["alert"],
                "Date idéale pour commander": item["order_by_date"],
            }
        )
    return pd.DataFrame(rows)
