import html
import os
import urllib.parse

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

from api_client import SEG_API, get_segmentation_kpis, get_segmentation_segments
from formatting import fmt_money_mga

API_URL = os.environ.get("API_URL", "http://localhost:8000")


def _prophecy_stylesheet_path() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "prophecy_styles.css")


def _inject_prophecy_styles() -> None:
    css_path = _prophecy_stylesheet_path()
    with open(css_path, encoding="utf-8") as f:
        css = f.read()
    st.html(f"<style>\n{css}\n</style>")


def _svg_to_data_uri(svg_markup: str) -> str:
    return "data:image/svg+xml," + urllib.parse.quote(svg_markup, safe="")


def _kpi_theme_primary_hex() -> str:
    try:
        theme = getattr(st.context, "theme", None)
        if theme is not None:
            c = getattr(theme, "primary_color", None) or getattr(theme, "primaryColor", None)
            if c:
                return str(c)
    except Exception:
        pass
    return "#0f5152"


def _kpi_icon_html(svg_markup: str, color_hex: str | None = None) -> str:
    icon_color = color_hex or _kpi_theme_primary_hex()
    colored = svg_markup.replace("currentColor", icon_color)
    uri = _svg_to_data_uri(colored)
    return (
        '<span class="metric-card-icon">'
        f'<img src="{uri}" alt="" width="20" height="20" decoding="async" loading="lazy" />'
        "</span>"
    )


_KPI_SVG = {
    "alert": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" aria-hidden="true">'
        '<path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round" d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/>'
        '<line x1="12" x2="12" y1="9" y2="13" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
        '<line x1="12" x2="12.01" y1="17" y2="17" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>'
    ),
    "trending_up": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" aria-hidden="true">'
        '<polyline fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round" points="22 7 13.5 15.5 8.5 10.5 2 17"/>'
        '<polyline fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round" points="16 7 22 7 22 13"/></svg>'
    ),
    "cart": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" aria-hidden="true">'
        '<circle cx="8" cy="21" r="1" fill="none" stroke="currentColor" stroke-width="2"/>'
        '<circle cx="19" cy="21" r="1" fill="none" stroke="currentColor" stroke-width="2"/>'
        '<path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round" d="M2.05 2.05h2l2.66 12.42a2 2 0 0 0 2 1.58h9.72a2 2 0 0 0 1.95-1.57l1.65-9.15H5.12"/></svg>'
    ),
}


def _rfm_kpi_card_html(
    label: str,
    value: str,
    subtitle: str,
    icon_svg: str | None = None,
    icon_emoji: str | None = None,
    icon_color: str | None = None,
) -> str:
    label_esc = html.escape(label)
    value_esc = html.escape(value)
    subtitle_esc = html.escape(subtitle)
    icon_block = ""
    if icon_emoji:
        icon_block = f'<span class="metric-card-icon" aria-hidden="true">{html.escape(icon_emoji)}</span>'
    elif icon_svg:
        icon_block = _kpi_icon_html(icon_svg, color_hex=icon_color)
    return f"""
        <div class="custom-header metric-card">
            <div class="header-title-row">
                {icon_block}
                <p class="header-title">{label_esc}</p>
            </div>
            <p class="header-value">{value_esc}</p>
            <p class="metric-subtitle">{subtitle_esc}</p>
        </div>
        """


def _fmt_grouped_int(n) -> str:
    try:
        return f"{int(float(n)):,}".replace(",", " ")
    except (TypeError, ValueError):
        return str(n)


def _fmt_percent(n, decimals: int = 2) -> str:
    try:
        value = f"{float(n):.{decimals}f}".replace(".", ",")
        return f"{value}%"
    except (TypeError, ValueError):
        return str(n)


def _fmt_number_fr(n, decimals: int = 0) -> str:
    try:
        value = float(n)
    except (TypeError, ValueError):
        return str(n)
    if decimals <= 0:
        return f"{int(round(value)):,}".replace(",", " ")
    return f"{value:,.{decimals}f}".replace(",", " ").replace(".", ",")


def _rfm_kpis_section_html(kpis: dict, at_risk_count: int | None = None, at_risk_pct: float | None = None) -> str:
    risk_count = at_risk_count if at_risk_count is not None else int(kpis.get("champions_count", 0) or 0)
    risk_pct = at_risk_pct if at_risk_pct is not None else float(kpis.get("champions_pct", 0) or 0)
    cards = [
        _rfm_kpi_card_html(
            "Total Clients",
            _fmt_grouped_int(kpis.get("total_clients")),
            "Base de données active",
            icon_emoji="👥",
        ),
        _rfm_kpi_card_html(
            "Valeur moyenne (MGA)",
            fmt_money_mga(kpis.get("average_monetary")),
            "Panier moyen cumulé",
            icon_emoji="💰",
        ),
        _rfm_kpi_card_html(
            "À risque",
            _fmt_grouped_int(risk_count),
            f"{_fmt_percent(risk_pct)} de la base",
            icon_svg=_KPI_SVG["alert"],
            icon_color="#dc2626",
        ),
        _rfm_kpi_card_html(
            "Clients B2B",
            _fmt_percent(kpis.get("b2b_pct")),
            f'{_fmt_grouped_int(kpis.get("b2b_count"))} clients pro',
            icon_svg=_KPI_SVG["cart"],
        ),
    ]
    cells = "".join(f'<div class="kpi-grid-item">{c}</div>' for c in cards)
    return f'<div class="kpi-grid kpi-grid--rfm" role="region" aria-label="Indicateurs RFM">{cells}</div>'


def load_segments_rfm():
    return get_segmentation_segments()


def load_rfm_dashboard_kpis():
    return get_segmentation_kpis()


def load_segment_interests(top_n: int = 3):
    response = requests.get(f"{SEG_API}/segments/interest", params={"top_n": top_n})
    if response.status_code == 200:
        return response.json()
    return {}


def load_rfm_customers(
    segment=None,
    tag_b2b=None,
    tag_christmas=None,
    tag_holidays=None,
    interest=None,
    partner_name_contains=None,
    limit=100,
    offset=0,
):
    params = {
        "segment": segment,
        "tag_b2b": tag_b2b,
        "tag_christmas": tag_christmas,
        "tag_holidays": tag_holidays,
        "interest": interest,
        "partner_name_contains": partner_name_contains,
        "limit": limit,
        "offset": offset,
    }
    response = requests.get(f"{SEG_API}/customers", params=params)
    if response.status_code == 200:
        return response.json()
    return {"items": [], "total": 0, "limit": limit, "offset": offset}


def _segment_interest_rows(segments) -> list[dict]:
    rows = []
    for seg in segments:
        if not isinstance(seg, dict):
            continue
        seg_name = seg.get("segment")
        interests = seg.get("by_interest", [])
        if not seg_name or not isinstance(interests, list):
            continue
        for item in interests:
            if not isinstance(item, dict):
                continue
            interest_name = item.get("interest")
            count = item.get("count")
            if interest_name is None or count is None:
                continue
            rows.append(
                {
                    "segment": str(seg_name),
                    "interest": str(interest_name),
                    "count": count,
                }
            )
    return rows


def _interests_dataframe(payload) -> pd.DataFrame:
    if not isinstance(payload, dict):
        return pd.DataFrame()
    segments = payload.get("segments")
    if not isinstance(segments, list):
        return pd.DataFrame()
    rows = _segment_interest_rows(segments)
    df = pd.DataFrame(rows, columns=["segment", "interest", "count"])
    if df.empty:
        return df
    df["count"] = pd.to_numeric(df["count"], errors="coerce").fillna(0)
    return df


def _inject_rfm_table_css() -> None:
    st.markdown(
        """
        <style>
        [data-testid="stPopoverButton"] {
            border: none !important;
            box-shadow: none !important;
            background: transparent !important;
            white-space: nowrap !important;
            min-width: fit-content !important;
            padding: 0 !important;
        }
        [data-testid="stPopover"] {
            display: flex !important;
            justify-content: flex-end !important;
            width: 100% !important;
        }
        /* Alignement a droite force pour colonnes numeriques (4,5,6) */
        [data-testid="stDataFrame"] [role="columnheader"][aria-colindex="4"],
        [data-testid="stDataFrame"] [role="columnheader"][aria-colindex="5"],
        [data-testid="stDataFrame"] [role="columnheader"][aria-colindex="6"],
        [data-testid="stDataFrame"] [role="columnheader"][aria-colindex="4"] *,
        [data-testid="stDataFrame"] [role="columnheader"][aria-colindex="5"] *,
        [data-testid="stDataFrame"] [role="columnheader"][aria-colindex="6"] * {
            text-align: right !important;
            justify-content: flex-end !important;
        }
        [data-testid="stDataFrame"] [role="gridcell"][aria-colindex="4"],
        [data-testid="stDataFrame"] [role="gridcell"][aria-colindex="5"],
        [data-testid="stDataFrame"] [role="gridcell"][aria-colindex="6"],
        [data-testid="stDataFrame"] [role="gridcell"][aria-colindex="4"] *,
        [data-testid="stDataFrame"] [role="gridcell"][aria-colindex="5"] *,
        [data-testid="stDataFrame"] [role="gridcell"][aria-colindex="6"] * {
            text-align: right !important;
            justify-content: flex-end !important;
        }
        .rfm-table-scroll {
            max-height: 388px;
            overflow-y: auto;
            border: 1px solid #e5e7eb;
            border-radius: 10px;
        }
        .rfm-table-scroll table {
            width: 100%;
            border-collapse: collapse;
        }
        .rfm-table-scroll thead th {
            position: sticky;
            top: 0;
            background: #f9fafb;
            z-index: 2;
            white-space: nowrap;
            text-align: left;
            font-weight: 600;
            border-bottom: 1px solid #e5e7eb;
        }
        .rfm-table-scroll th,
        .rfm-table-scroll td {
            padding: 8px 10px;
            border-bottom: 1px solid #f1f5f9;
            font-size: 0.92rem;
        }
        .rfm-table-scroll tbody td:nth-child(4),
        .rfm-table-scroll tbody td:nth-child(5),
        .rfm-table-scroll tbody td:nth-child(6) {
            text-align: right;
            font-variant-numeric: tabular-nums;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def run_segmentation():
    data_segments = load_segments_rfm()
    data_rfm_kpis = load_rfm_dashboard_kpis()
    by_segment = data_segments.get("by_segment", []) if isinstance(data_segments, dict) else []
    by_segment_ca = data_segments.get("by_segment_ca", []) if isinstance(data_segments, dict) else []
    segment_palette = ["#025864", "#00d47e", "#f4c095", "#ee2e31"]
    interests_palette = ["#025864", "#00d47e", "#f4c095", "#ee2e31", "#63474d"]

    st.html(
        """
        <div class="custom-header">
            <div class="header-title">Prophecy</div>
            <div class="header-value" style="font-size: 28px;">
                Segmentation RFM & Profils
                <span class="header-trend">Actualisé</span>
            </div>
        </div>
        """
    )

    if data_rfm_kpis:
        total_clients = float(data_rfm_kpis.get("total_clients", 0) or 0)
        at_risk_count = 0
        for row in by_segment:
            seg_name = str(row.get("segment", "")).strip().lower()
            if "risque" in seg_name:
                at_risk_count = int(row.get("count", 0) or 0)
                break
        at_risk_pct = (at_risk_count / total_clients * 100) if total_clients > 0 else 0.0
        st.html(_rfm_kpis_section_html(data_rfm_kpis, at_risk_count=at_risk_count, at_risk_pct=at_risk_pct))
        st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("### Performance des segments clients")

    if by_segment:
        seg_df = pd.DataFrame(by_segment)
        seg_df["count"] = pd.to_numeric(seg_df["count"], errors="coerce").fillna(0)
        seg_df["part"] = (seg_df["count"] / max(seg_df["count"].sum(), 1)) * 100
        seg_df = seg_df.sort_values("count", ascending=False)

        ca_df = pd.DataFrame(by_segment_ca) if by_segment_ca else pd.DataFrame(columns=["segment", "ca"])
        if not ca_df.empty:
            ca_df["ca"] = pd.to_numeric(ca_df["ca"], errors="coerce").fillna(0)
            ca_df = ca_df.sort_values("ca", ascending=False)

        col1, col2 = st.columns(2, gap="small")

        with col1:
            with st.container(border=True):
                st.markdown("#### CA par segment (MGA)")
                if not ca_df.empty:
                    fig_bar_ca = px.bar(
                        ca_df,
                        x="ca",
                        y="segment",
                        orientation="h",
                        color="segment",
                        color_discrete_sequence=segment_palette,
                        labels={"segment": "Segment", "ca": "Chiffre d'affaires"},
                    )
                    fig_bar_ca.update_layout(
                        title_text="",
                        showlegend=False,
                        margin={"l": 10, "r": 10, "t": 20, "b": 10},
                    )
                    st.plotly_chart(fig_bar_ca, use_container_width=True)
                    top_ca = ca_df.iloc[0]
                    st.caption(f"Top CA: **{top_ca['segment']}** ({fmt_money_mga(top_ca['ca'])}).")
                else:
                    st.info("Aucune donnée de CA par segment.")

        with col2:
            with st.container(border=True):
                st.markdown("#### Clients par segment")
                fig_donut = px.pie(
                    seg_df,
                    names="segment",
                    values="count",
                    hole=0.55,
                    color="segment",
                    color_discrete_sequence=segment_palette,
                )
                fig_donut.update_traces(textposition="inside", texttemplate="%{percent:.1%}")
                fig_donut.update_layout(title_text="", margin={"l": 10, "r": 10, "t": 20, "b": 10})
                st.plotly_chart(fig_donut, use_container_width=True)
                top_row = seg_df.iloc[0]
                st.caption(
                    f"Segment dominant: **{top_row['segment']}** "
                    f"({_fmt_grouped_int(top_row['count'])} clients, {_fmt_percent(top_row['part'])})."
                )

    st.markdown("<br>", unsafe_allow_html=True)
    with st.container(border=True):
        col_title, col_filter = st.columns([4, 1], gap="small")
        with col_title:
            st.markdown("#### Intérêts Majeurs par Segment")
        with col_filter:
            top_n = st.number_input("Top", min_value=1, max_value=10, value=3, step=1, key="rfm_top_interests")

        interests_payload = load_segment_interests(int(top_n))
        interests_df = _interests_dataframe(interests_payload)

        if interests_df.empty:
            st.info("Pas de données d'intérêts par segment disponibles.")
        else:
            top_interest_names = (
                interests_df.groupby("interest", as_index=False)["count"]
                .sum()
                .sort_values("count", ascending=False)
                .head(int(top_n))["interest"]
                .tolist()
            )
            top_interests_df = interests_df[interests_df["interest"].isin(top_interest_names)].copy()
            top_interests_df["interest"] = pd.Categorical(
                top_interests_df["interest"],
                categories=top_interest_names,
                ordered=True,
            )

            grouped_fig = px.bar(
                top_interests_df,
                x="segment",
                y="count",
                color="interest",
                barmode="group",
                color_discrete_sequence=interests_palette,
                labels={"segment": "Segment", "count": "Nombre de clients", "interest": "Intérêt"},
            )
            grouped_fig.update_layout(
                margin={"l": 10, "r": 10, "t": 10, "b": 10},
                legend_title_text="Intérêt",
            )
            st.plotly_chart(grouped_fig, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### Liste clients stratégiques")

    segment_options = sorted(seg_df["segment"].dropna().unique().tolist()) if by_segment else []
    interest_options = sorted(
        interests_df["interest"].dropna().unique().tolist()
    ) if "interests_df" in locals() and not interests_df.empty else []

    with st.container(border=True):
        f1, f2, f3 = st.columns(3, gap="small")
        with f1:
            selected_segment = st.selectbox(
                "Segment",
                options=["Tous"] + segment_options,
                index=0,
                help="Sélection unique, recherche possible au clavier.",
            )
        with f2:
            selected_interest = st.selectbox(
                "Intérêt",
                options=["Tous"] + interest_options,
                index=0,
                help="Sélection unique, recherche possible au clavier.",
            )
        with f3:
            name_contains = st.text_input("Nom client contient", value="", placeholder="Ex: RAKOTO")

    filter_b2b = False
    filter_noel = False
    filter_saisonnier = False
    limit = 100
    offset = 0

    st.markdown("<div style='height:3px;'></div>", unsafe_allow_html=True)
    meta_left, meta_right = st.columns([9, 2], gap="small")
    with meta_left:
        total_slot = st.empty()
    with meta_right:
        with st.popover("Plus de filtre", use_container_width=True):
            filter_b2b = st.checkbox("Client B2B", value=False, key="rfm_filter_b2b")
            filter_noel = st.checkbox("Acheteur Noël", value=False, key="rfm_filter_noel")
            filter_saisonnier = st.checkbox("Acheteur saisonnier", value=False, key="rfm_filter_saisonnier")
            limit = st.number_input("Limite", min_value=1, value=100, step=50, key="rfm_limit")
            offset = st.number_input("Décalage", min_value=0, value=0, step=50, key="rfm_offset")

    tag_b2b = True if filter_b2b else None
    tag_christmas = True if filter_noel else None
    tag_holidays = True if filter_saisonnier else None

    customers_payload = load_rfm_customers(
        segment=None if selected_segment == "Tous" else selected_segment,
        interest=None if selected_interest == "Tous" else selected_interest,
        tag_b2b=tag_b2b,
        tag_christmas=tag_christmas,
        tag_holidays=tag_holidays,
        partner_name_contains=name_contains.strip() or None,
        limit=int(limit),
        offset=int(offset),
    )

    customers = customers_payload.get("items", []) if isinstance(customers_payload, dict) else []
    total = customers_payload.get("total", 0) if isinstance(customers_payload, dict) else 0

    if not customers:
        st.info("Aucun client trouvé pour ces filtres.")
    else:
        df_customers = pd.DataFrame(customers)

        # Anti-redondance affichage: certains clients peuvent être renvoyés plusieurs fois
        # par l'API. On garde une seule ligne par `partner_name`.
        if "partner_name" in df_customers.columns:
            df_customers["partner_name"] = (
                df_customers["partner_name"].astype(str).str.strip()
            )
            sort_cols: list[str] = []
            sort_ascending: list[bool] = []

            if "last_purchase" in df_customers.columns:
                df_customers["_last_purchase_dt"] = pd.to_datetime(
                    df_customers["last_purchase"], errors="coerce"
                )
                sort_cols.append("_last_purchase_dt")
                sort_ascending.append(False)  # plus récent d'abord

            if "recency_days" in df_customers.columns:
                df_customers["recency_days"] = pd.to_numeric(
                    df_customers["recency_days"], errors="coerce"
                )
                sort_cols.append("recency_days")
                sort_ascending.append(True)  # plus petit = plus récent

            if "monetary" in df_customers.columns:
                df_customers["monetary"] = pd.to_numeric(
                    df_customers["monetary"], errors="coerce"
                )
                sort_cols.append("monetary")
                sort_ascending.append(False)  # plus élevé d'abord

            if sort_cols:
                # `mergesort` pour garder une stabilité en cas d'égalité.
                df_customers = df_customers.sort_values(
                    sort_cols, ascending=sort_ascending, kind="mergesort"
                )

            df_customers = df_customers.drop_duplicates(
                subset=["partner_name"], keep="first"
            )

            if "_last_purchase_dt" in df_customers.columns:
                df_customers.drop(columns=["_last_purchase_dt"], inplace=True)

        column_mapping = {
            "partner_name": "Client",
            "segment": "Segment RFM",
            "Tag_Interest": "Intérêt principal",
            "recency_days": "Dernier achat (jours)",
            "frequency": "Fréquence d’achat",
            "monetary": "Chiffre d’affaires (MGA)",
            "last_purchase": "Date dernier achat",
            "Tag_B2B": "Client B2B",
            "Tag_Christmas_Shopper": "Acheteur Noël",
            "Tag_Holidays_Shopper": "Acheteur saisonnier",
        }
        available_columns = [col for col in column_mapping if col in df_customers.columns]
        df_customers = df_customers[available_columns].rename(columns=column_mapping)
        bool_columns = ["Client B2B", "Acheteur Noël", "Acheteur saisonnier"]
        for bool_col in bool_columns:
            if bool_col in df_customers.columns:
                df_customers[bool_col] = df_customers[bool_col].map({True: "Oui", False: "Non"}).fillna("Non")
        fr_number_columns = {
            "Dernier achat (jours)": 0,
            "Fréquence d’achat": 0,
            "Chiffre d’affaires": 2,
        }
        numeric_display_cols = []
        for col_name, decimals in fr_number_columns.items():
            if col_name in df_customers.columns:
                numeric_display_cols.append(col_name)
                df_customers[col_name] = pd.to_numeric(df_customers[col_name], errors="coerce")

        _inject_rfm_table_css()
        total_slot.markdown(
            f"<div style='margin:0; padding-top:2px; line-height:1.1;'>{_fmt_grouped_int(total)} clients au total</div>",
            unsafe_allow_html=True,
        )
        st.markdown("<div style='height:0; margin:0; padding:0;'></div>", unsafe_allow_html=True)
        row_height = 35
        header_height = 38
        table_height = header_height + (10 * row_height)
        styled_df = df_customers.style
        if numeric_display_cols:
            formatters = {
                col: (lambda v, d=fr_number_columns[col]: _fmt_number_fr(v, d))
                for col in numeric_display_cols
            }
            styled_df = (
                styled_df
                .format(formatters)
                .set_properties(subset=numeric_display_cols, **{"text-align": "right"})
            )
        st.dataframe(styled_df, use_container_width=True, hide_index=True, height=table_height)
