"""Tableau de bord — KPIs globaux et visualisations EDA (léger)."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

from api_client import (
    API_URL,
    api_reachable,
    get_reassort_stats,
    get_segmentation_kpis,
    get_segmentation_segments,
    reassort_ready,
)
from formatting import fmt_money_mga
from reassort_page import _kpi_metrics_section_html


def _page_header(title: str, subtitle: str = "Prophecy") -> None:
    st.html(
        f"""
        <div class="custom-header">
            <div class="header-title">{subtitle}</div>
            <div class="header-value" style="font-size: 28px;">{title}</div>
        </div>
        """
    )


def _api_error_block(exc: Exception) -> None:
    st.error(
        f"Impossible de joindre l'API (`{API_URL}`).\n\n"
        f"Détail : {exc}\n\n"
        "Lancez `docker compose up --build` et attendez que l'API ait fini "
        "le pré-calcul réassort (logs : « Réassort prêt »)."
    )
    if not api_reachable():
        st.info("Le endpoint `/health` ne répond pas encore.")
    elif not reassort_ready():
        st.warning(
            "L'API répond mais le **calcul réassort** n'est pas terminé. "
            "Patientez 1–3 min puis rafraîchissez (F5)."
        )


def run_dashboard() -> None:
    _page_header("Tableau de bord")

    if api_reachable() and not reassort_ready():
        st.warning(
            "⏳ Calcul réassort en cours côté API (XGBoost, ~1–3 min au premier démarrage). "
            "Les indicateurs clients s'affichent d'abord."
        )

    stats: dict | None = None
    seg_kpis: dict = {}
    seg_data: dict = {}

    try:
        with ThreadPoolExecutor(max_workers=3) as pool:
            fut_seg_kpis = pool.submit(get_segmentation_kpis)
            fut_seg_data = pool.submit(get_segmentation_segments)
            fut_stats = pool.submit(get_reassort_stats)

            with st.spinner("Chargement segmentation clients…"):
                seg_kpis = fut_seg_kpis.result()
                seg_data = fut_seg_data.result()

        st.markdown("### Clients — vue d'ensemble")
        if seg_kpis:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total clients", f"{seg_kpis.get('total_clients', 0):,}".replace(",", " "))
            c2.metric("Panier moyen (MGA)", fmt_money_mga(seg_kpis.get("average_monetary", 0)))
            c3.metric("Champions", seg_kpis.get("champions_count", 0))
            c4.metric("Clients B2B", f"{seg_kpis.get('b2b_pct', 0)} %")
        else:
            st.caption("KPIs segmentation non disponibles.")

        by_segment = seg_data.get("by_segment") or []
        if by_segment:
            with st.container(border=True):
                st.markdown("#### Clients par segment RFM")
                df_seg = pd.DataFrame(by_segment)
                df_seg["count"] = pd.to_numeric(df_seg["count"], errors="coerce").fillna(0)
                fig_seg = px.bar(
                    df_seg.sort_values("count", ascending=True),
                    x="count",
                    y="segment",
                    orientation="h",
                    color="segment",
                    color_discrete_sequence=["#025864", "#00d47e", "#f4c095", "#ee2e31"],
                    labels={"count": "Clients", "segment": "Segment"},
                )
                fig_seg.update_layout(showlegend=False, margin=dict(l=0, r=0, t=10, b=0))
                st.plotly_chart(fig_seg, use_container_width=True)

        with st.spinner("Chargement indicateurs réassort…"):
            stats = fut_stats.result()

    except requests.RequestException as exc:
        _api_error_block(exc)
        return

    st.markdown("### Réassort — vue d'ensemble")
    cost_display = fmt_money_mga(stats.get("estimated_total_cost", 0))
    try:
        coverage_display = f"{float(stats['avg_coverage_days']):.2f} jours"
    except (TypeError, ValueError, KeyError):
        coverage_display = "—"

    st.html(_kpi_metrics_section_html(stats, cost_display, coverage_display))

    col_a, col_b = st.columns(2)
    alerts_dict = stats.get("alerts") or {}
    cycle_dict = stats.get("cycle_status") or {}

    with col_a:
        with st.container(border=True):
            st.markdown("#### Répartition des alertes stock")
            if alerts_dict:
                df_alerts = pd.DataFrame(
                    [{"alert": k, "qty_to_order": v} for k, v in alerts_dict.items()]
                )
                colors = ["#025864", "#00d47e", "#f4c095", "#ee2e31", "#63474d"]
                color_map = {
                    row["alert"]: colors[i % len(colors)]
                    for i, row in enumerate(df_alerts.to_dict("records"))
                }
                fig = px.bar(
                    df_alerts,
                    x="alert",
                    y="qty_to_order",
                    color="alert",
                    color_discrete_map=color_map,
                    labels={"alert": "Alerte", "qty_to_order": "Qté à commander"},
                )
                fig.update_layout(showlegend=False, margin=dict(l=0, r=0, t=10, b=0))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.caption("Aucune donnée d'alerte.")

    with col_b:
        with st.container(border=True):
            st.markdown("#### Cycle de vie produits")
            if cycle_dict:
                df_cycle = pd.DataFrame(
                    [{"cycle": k, "count": v} for k, v in cycle_dict.items()]
                )
                fig_pie = px.pie(
                    df_cycle,
                    names="cycle",
                    values="count",
                    hole=0.45,
                    color_discrete_sequence=["#025864", "#00d47e", "#f4c095", "#ee2e31", "#63474d"],
                )
                fig_pie.update_layout(margin=dict(l=0, r=0, t=10, b=0))
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.caption("Aucune donnée de cycle.")

    st.caption(
        "Pour le détail des commandes et filtres avancés, ouvrez **Réassort** dans le menu."
    )
