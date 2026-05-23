import html
import os
import urllib.parse
from datetime import date, datetime

import pandas as pd
import plotly.express as px
import requests
import streamlit as st
import base64

API_URL = os.environ.get("API_URL", "http://localhost:8000")
REASSORT_API = f"{API_URL}/reassort"

st.set_page_config(page_title="Réassort", page_icon="img/favicon.png", layout="wide")


def _svg_to_data_uri(svg_markup: str) -> str:
    """Encode un SVG en data URI — st.html() / DOMPurify supprime les balises <svg> inline."""
    return "data:image/svg+xml," + urllib.parse.quote(svg_markup, safe="")


def _kpi_theme_primary_hex() -> str:
    """Couleur primaire du thème Streamlit pour les icônes KPI (cartes claires / sombres)."""
    try:
        theme = getattr(st.context, "theme", None)
        if theme is not None:
            c = getattr(theme, "primary_color", None) or getattr(theme, "primaryColor", None)
            if c:
                return str(c)
    except Exception:
        pass
    return "#0f5152"


def _kpi_icon_html(svg_markup: str) -> str:
    """Icône KPI via <img> + data URI (trait = couleur primaire thème)."""
    colored = svg_markup.replace("currentColor", _kpi_theme_primary_hex())
    uri = _svg_to_data_uri(colored)
    return (
        '<span class="metric-card-icon">'
        f'<img src="{uri}" alt="" width="20" height="20" decoding="async" loading="lazy" />'
        "</span>"
    )


# Icônes KPI (SVG sources pour data URI) — style Lucide
_KPI_SVG = {
    "package": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" aria-hidden="true">'
        '<path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round" d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>'
        '<polyline fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round" points="3.27 6.96 12 12.01 20.73 6.96"/>'
        '<line x1="12" x2="12" y1="22.08" y2="12" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>'
    ),
    "cart": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" aria-hidden="true">'
        '<circle cx="8" cy="21" r="1" fill="none" stroke="currentColor" stroke-width="2"/>'
        '<circle cx="19" cy="21" r="1" fill="none" stroke="currentColor" stroke-width="2"/>'
        '<path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round" d="M2.05 2.05h2l2.66 12.42a2 2 0 0 0 2 1.58h9.72a2 2 0 0 0 1.95-1.57l1.65-9.15H5.12"/></svg>'
    ),
    "euro": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" aria-hidden="true">'
        '<path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round" d="M4 10h12"/><path fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" d="M4 14h9"/>'
        '<path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round" d="M19 6a7.7 7.7 0 0 0-5.2-2A7.5 7.5 0 0 0 6 20h13"/></svg>'
    ),
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
    "archive": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" aria-hidden="true">'
        '<rect width="20" height="5" x="2" y="3" rx="1" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
        '<path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round" d="M4 8v11a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8"/>'
        '<path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round" d="M10 12h4"/></svg>'
    ),
    "timer": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" aria-hidden="true">'
        '<line x1="10" x2="14" y1="2" y2="2" fill="none" stroke="currentColor" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round"/>'
        '<line x1="12" x2="15" y1="14" y2="11" fill="none" stroke="currentColor" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round"/>'
        '<circle cx="12" cy="14" r="8" fill="none" stroke="currentColor" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round"/></svg>'
    ),
}


def _kpi_metric_card_html(
    label: str,
    value: str,
    icon_svg: str | None = None,
) -> str:
    """Carte KPI (custom-header + titre + valeur ; icône SVG optionnelle)."""
    label_esc = html.escape(label)
    value_esc = html.escape(value)
    icon_block = ""
    if icon_svg:
        icon_block = _kpi_icon_html(icon_svg)
    return f"""
        <div class="custom-header metric-card">
            <div class="header-title-row">
                {icon_block}
                <p class="header-title">{label_esc}</p>
            </div>
            <p class="header-value">{value_esc}</p>
        </div>
        """


def _kpi_metrics_section_html(data_stats: dict, cost_display: str, coverage_display: str) -> str:
    """Grille responsive : 1 col. mobile, 2 tablette, 3 desktop ; couverture sur toute la largeur."""
    cards = [
        _kpi_metric_card_html(
            "Total des produits",
            str(data_stats["total_products"]),
            icon_svg=_KPI_SVG["package"],
        ),
        _kpi_metric_card_html(
            "Produits à commander",
            str(data_stats["products_to_order"]),
            icon_svg=_KPI_SVG["cart"],
        ),
        _kpi_metric_card_html(
            "Coût estimé du réassort",
            cost_display,
            icon_svg=_KPI_SVG["euro"],
        ),
        _kpi_metric_card_html(
            "Rupture imminente",
            str(data_stats["rupture_imminente"]),
            icon_svg=_KPI_SVG["alert"],
        ),
        _kpi_metric_card_html(
            "Forte demande",
            str(data_stats["forte_demande"]),
            icon_svg=_KPI_SVG["trending_up"],
        ),
        _kpi_metric_card_html(
            "Produits obsolètes",
            str(data_stats["obsolete"]),
            icon_svg=_KPI_SVG["archive"],
        ),
    ]
    # coverage = _kpi_metric_card_html(
    #     "Couverture stock",
    #     coverage_display,
    #     icon_svg=_KPI_SVG["timer"],
    # )
    cells = "".join(f'<div class="kpi-grid-item">{c}</div>' for c in cards)
    return f'<div class="kpi-grid" role="region" aria-label="Indicateurs clés">{cells}</div>'


def _fmt_compact_number(n) -> str:
    """Équivalent visuel proche de st.metric(..., format='compact')."""
    try:
        x = float(n)
    except (TypeError, ValueError):
        return str(n)
    ax = abs(x)
    if ax >= 1_000_000_000:
        return f"{x / 1_000_000_000:.1f}B".rstrip("0").rstrip(".")
    if ax >= 1_000_000:
        return f"{x / 1_000_000:.1f}M".rstrip("0").rstrip(".")
    if ax >= 1_000:
        return f"{x / 1_000:.1f}k".rstrip("0").rstrip(".")
    if x == int(x):
        return str(int(x))
    return str(x)


_MOIS_FR = (
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre",
)


def _reassort_to_datetime(val):
    """Normalise une valeur (API, pandas, numpy) en datetime naïf ou None."""
    if pd.isna(val):
        return None
    if isinstance(val, datetime):
        return val.replace(tzinfo=None) if val.tzinfo else val
    try:
        ts = pd.to_datetime(val, errors="coerce")
        if pd.isna(ts):
            return None
        dt = ts.to_pydatetime()
        if getattr(dt, "tzinfo", None) is not None:
            dt = dt.replace(tzinfo=None)
        return dt
    except Exception:
        return None


def _reassort_format_date_french(val) -> str:
    """Date lisible en français, ex. « 15 mars 2025 »."""
    dt = _reassort_to_datetime(val)
    if dt is None:
        return "—"
    return f"{dt.day} {_MOIS_FR[dt.month - 1]} {dt.year}"


def _reassort_scalar_str(val) -> str:
    """Valeur affichable pour une cellule (hors badge)."""
    if pd.isna(val):
        return "—"
    if isinstance(val, date):
        return _reassort_format_date_french(val)
    if isinstance(val, pd.Timestamp):
        return _reassort_format_date_french(val)
    if type(val).__name__ == "datetime64" and getattr(type(val), "__module__", "") == "numpy":
        return _reassort_format_date_french(val)
    try:
        x = float(val)
        if x == int(x) and abs(x) < 1e15:
            return str(int(x))
    except (TypeError, ValueError):
        pass
    return str(val)


def _reassort_stock_badge_variant(raw) -> str:
    """Variante visuelle pour l'alerte stock (alignée sur les libellés API / formulaire)."""
    if pd.isna(raw):
        return "muted"
    s = str(raw).strip().lower()
    if "rupture" in s or "imminent" in s:
        return "destructive"
    if "forte" in s and "demande" in s:
        return "warning"
    if "ne pas" in s or "pas recommander" in s:
        return "muted"
    if "à commander" in s or "a commander" in s:
        return "default"
    if "stable" in s:
        return "secondary"
    if "stock ok" in s or s == "ok":
        return "success"
    return "outline"


def _reassort_cycle_badge_variant(raw) -> str:
    """Variante pour le cycle de vie produit."""
    if pd.isna(raw):
        return "muted"
    s = str(raw).strip().lower()
    if "croissance" in s:
        return "success"
    if "maturité" in s or "maturite" in s:
        return "info"
    if "déclin" in s or "declin" in s:
        return "warning"
    if "obsolescence" in s or "obsolète" in s or "obsolete" in s:
        return "destructive"
    if "inactif" in s:
        return "muted"
    return "outline"


# Couleurs de trait des icônes badges (alignées sur le texte des pastilles)
_BADGE_ICON_STROKE = {
    "default": "#0f5152",
    "secondary": "#374151",
    "destructive": "#991b1b",
    "warning": "#92400e",
    "success": "#065f46",
    "info": "#1e40af",
    "muted": "#6b7280",
    "outline": "#374151",
}


# Petites icônes pour les badges (état stock / cycle)
_BADGE_SVG_STOCK = {
    "destructive": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" aria-hidden="true">'
        '<path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round" d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/>'
        '<line x1="12" x2="12" y1="9" y2="13"/><line x1="12" x2="12.01" y1="17" y2="17"/></svg>'
    ),
    "warning": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" aria-hidden="true">'
        '<circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="2"/>'
        '<line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/></svg>'
    ),
    "default": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" aria-hidden="true">'
        '<circle cx="8" cy="21" r="1" fill="none" stroke="currentColor" stroke-width="2"/>'
        '<circle cx="19" cy="21" r="1" fill="none" stroke="currentColor" stroke-width="2"/>'
        '<path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round" d="M2.05 2.05h2l2.66 12.42a2 2 0 0 0 2 1.58h9.72a2 2 0 0 0 1.95-1.57l1.65-9.15H5.12"/></svg>'
    ),
    "secondary": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" aria-hidden="true">'
        '<path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round" d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>'
    ),
    "success": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" aria-hidden="true">'
        '<path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round" d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>'
        '<polyline fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round" points="22 4 12 14.01 9 11.01"/></svg>'
    ),
    "muted": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" aria-hidden="true">'
        '<circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="2"/>'
        '<path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round" d="m4.93 4.93 14.14 14.14"/></svg>'
    ),
    "outline": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" aria-hidden="true">'
        '<circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="2"/></svg>'
    ),
    "info": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" aria-hidden="true">'
        '<circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="2"/>'
        '<line x1="12" x2="12" y1="16" y2="12"/><line x1="12" x2="12.01" y1="8" y2="8"/></svg>'
    ),
}

_BADGE_SVG_CYCLE = {
    "success": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" aria-hidden="true">'
        '<polyline fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round" points="22 7 13.5 15.5 8.5 10.5 2 17"/>'
        '<polyline points="16 7 22 7 22 13" fill="none" stroke="currentColor" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round"/></svg>'
    ),
    "info": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" aria-hidden="true">'
        '<circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="2"/>'
        '<line x1="12" x2="12" y1="16" y2="12"/><line x1="12" x2="12.01" y1="8" y2="8"/></svg>'
    ),
    "warning": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" aria-hidden="true">'
        '<polyline fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round" points="23 18 13.5 8.5 8.5 13.5 1 6"/>'
        '<polyline fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round" points="17 18 23 18 23 12"/></svg>'
    ),
    "destructive": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" aria-hidden="true">'
        '<rect width="20" height="5" x="2" y="3" rx="1" fill="none" stroke="currentColor" '
        'stroke-width="2"/><path fill="none" stroke="currentColor" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round" d="M4 8v11a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8"/>'
        '<path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round" d="M10 12h4"/></svg>'
    ),
    "muted": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" aria-hidden="true">'
        '<circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="2"/>'
        '<line x1="10" x2="10" y1="15" y2="9"/><line x1="14" x2="14" y1="15" y2="9"/></svg>'
    ),
    "default": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" aria-hidden="true">'
        '<path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round" d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>'
    ),
    "secondary": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" aria-hidden="true">'
        '<path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round" d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/></svg>'
    ),
    "outline": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" aria-hidden="true">'
        '<circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="2"/></svg>'
    ),
}


def _reassort_badge_icon_markup(variant: str, badge_kind: str) -> str:
    if badge_kind == "stock":
        table = _BADGE_SVG_STOCK
    elif badge_kind == "cycle":
        table = _BADGE_SVG_CYCLE
    else:
        return ""
    svg = table.get(variant) or table.get("outline", "")
    if not svg:
        return ""
    color = _BADGE_ICON_STROKE.get(variant, "#374151")
    colored = svg.replace("currentColor", color)
    uri = _svg_to_data_uri(colored)
    return (
        '<span class="reassort-badge-icon" aria-hidden="true">'
        f'<img src="{uri}" alt="" width="14" height="14" decoding="async" />'
        "</span>"
    )


def _reassort_badge_html(
    text: str,
    variant: str,
    badge_kind: str | None = None,
    inline_style: str | None = None,
) -> str:
    esc = html.escape(text.strip() if text else "")
    safe_variant = variant if variant in {
        "destructive", "warning", "success", "default", "secondary",
        "info", "muted", "outline",
    } else "outline"
    icon_html = ""
    if badge_kind in ("stock", "cycle"):
        icon_html = _reassort_badge_icon_markup(safe_variant, badge_kind)
    style_attr = f' style="{inline_style}"' if inline_style else ""
    return (
        f'<span class="reassort-badge reassort-badge--{safe_variant}"{style_attr}>'
        f'{icon_html}<span class="reassort-badge-label">{esc}</span></span>'
    )


def _hex_text_color(hex_color: str) -> str:
    """Choisit automatiquement une couleur de texte avec meilleur contraste WCAG."""
    h = (hex_color or "").strip().lstrip("#")
    if len(h) != 6:
        return "#111827"
    try:
        r = int(h[0:2], 16) / 255.0
        g = int(h[2:4], 16) / 255.0
        b = int(h[4:6], 16) / 255.0
    except ValueError:
        return "#111827"

    def _srgb_to_linear(c: float) -> float:
        if c <= 0.03928:
            return c / 12.92
        return ((c + 0.055) / 1.055) ** 2.4

    l_bg = (
        (0.2126 * _srgb_to_linear(r))
        + (0.7152 * _srgb_to_linear(g))
        + (0.0722 * _srgb_to_linear(b))
    )
    l_dark = 0.0      # ~ noir
    l_light = 1.0     # blanc
    contrast_dark = (max(l_bg, l_dark) + 0.05) / (min(l_bg, l_dark) + 0.05)
    contrast_light = (max(l_bg, l_light) + 0.05) / (min(l_bg, l_light) + 0.05)
    return "#111827" if contrast_dark >= contrast_light else "#ffffff"


def _reassort_cell_html(column_name: str, val, stock_color_map: dict[str, str] | None = None) -> str:
    """Contenu HTML d’une cellule : badges pour les colonnes d'état, sinon texte échappé."""
    if column_name == "Date idéale pour commander":
        return html.escape(_reassort_format_date_french(val))
    if column_name == "Etat du stock":
        s = _reassort_scalar_str(val)
        if s == "—":
            return s
        v = _reassort_stock_badge_variant(val)
        custom_bg = stock_color_map.get(s) if stock_color_map else None
        if custom_bg:
            text_color = _hex_text_color(custom_bg)
            return _reassort_badge_html(
                s,
                v,
                badge_kind="stock",
                inline_style=f"background: {custom_bg}; color: {text_color};",
            )
        return _reassort_badge_html(s, v, badge_kind="stock")
    if column_name == "Etat de l'article":
        s = _reassort_scalar_str(val)
        if s == "—":
            return s
        v = _reassort_cycle_badge_variant(val)
        return _reassort_badge_html(s, v, badge_kind="cycle")
    return html.escape(_reassort_scalar_str(val))


def _reassort_dataframe_html(df: pd.DataFrame, stock_color_map: dict[str, str] | None = None) -> str:
    """Un seul <table> (thead + tbody) : colonnes alignées par le moteur HTML, scroll dans le conteneur."""
    cols = list(df.columns)
    thead_cells = "".join(f"<th scope='col'>{html.escape(c)}</th>" for c in cols)
    tbody_rows: list[str] = []
    cards: list[str] = []
    for _, row in df.iterrows():
        cells = "".join(
            f"<td>{_reassort_cell_html(c, row[c], stock_color_map=stock_color_map)}</td>" for c in cols
        )
        tbody_rows.append(f"<tr>{cells}</tr>")
        card_inner = "".join(
            f'<div class="reassort-card-row">'
            f'<span class="reassort-card-label">{html.escape(c)}</span>'
            f'<span class="reassort-card-value">{_reassort_cell_html(c, row[c], stock_color_map=stock_color_map)}</span>'
            f"</div>"
            for c in cols
        )
        cards.append(f'<article class="reassort-card">{card_inner}</article>')
    return f"""
<div class="reassort-wrap" role="region" aria-label="Résultats réassort">
  <div class="reassort-x-scroll">
    <table class="reassort-table">
      <thead><tr>{thead_cells}</tr></thead>
      <tbody>{"".join(tbody_rows)}</tbody>
    </table>
  </div>
  <div class="reassort-cards">
    {"".join(cards)}
  </div>
</div>
"""


def _prophecy_stylesheet_path() -> str:
    """Chemin vers prophecy_styles.css (répertoire streamlit/)."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "prophecy_styles.css")


def _inject_prophecy_styles() -> None:
    """Charge prophecy_styles.css et injecte les styles dans la page Streamlit."""
    css_path = _prophecy_stylesheet_path()
    with open(css_path, encoding="utf-8") as f:
        css = f.read()
    st.html(f"<style>\n{css}\n</style>")


def load_stats():
    response = requests.get(f"{REASSORT_API}/stats")
    return response.json()

def load_categories():
    response = requests.get(f"{REASSORT_API}/categories")
    return response.json()['data']


def make_reassort(category_id, urgency_selected, growth_selected, quantity_selected, limit_selected, offset_selected):
    payload = {
        'category_id': category_id,
        'alert': urgency_selected,
        'cycle': growth_selected,
        'min_qty': quantity_selected,
        'limit': limit_selected,
        'offset': offset_selected
    }
    response = requests.get(f"{REASSORT_API}/products", params=payload)
    result = []
    if response.status_code == 200:
        data = response.json()
        if len(data['data']) > 0:
            for item in data['data']:
                result.append({
                    'Article': item['product_name'],
                    'Ventes prévues en 30 jours': item['ventes_prevues_30j'],
                    'Quantité en stock': item['qty_available'],
                    'Quantité à commander': item['qty_to_order'],
                    'Etat de l\'article': item['cycle_status'],
                    'Etat du stock': item['alert'],
                    'Date idéale pour commander': item['order_by_date']
                })
            df = pd.DataFrame(result)
            return df
        else:
            return pd.DataFrame()
    else:
        return pd.DataFrame()


@st.cache_data
def load_data():
    s3 = boto3.client(
        's3',
        aws_access_key_id = os.environ.get('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key = os.environ.get('AWS_SECRET_ACCESS_KEY'),
        region_name = os.environ.get('AWS_REGION'),
    )

    response = s3.get_object(Bucket=os.environ.get('AWS_BUCKET_NAME'), Key="demoday-dataset/sales_history.parquet")

    status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")
    if status == 200:
        body = response.get('Body')
        buffer = io.BytesIO(body.read())
        data = pd.read_parquet(buffer)
        data['is_sold'] = data['qty_sold'].apply(lambda x: "Sold" if x > 0 else "Not Sold")
        return data
    else:
        return None

def top_data(data, column_name, top_n=None):
    value_counts = data[column_name].value_counts(normalize=False)
    result = pd.DataFrame({
        column_name: value_counts.index,
        "count": value_counts.values
    })
    if top_n is not None:
        return result.head(top_n)
    else:
        return result

def get_encoded_image():
    image_path = "img/reassort_icon.png"
    with open(image_path, "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode()
    return encoded

def load_grouped_reassort():
    response = requests.get(f"{REASSORT_API}/grouped-reassort")
    return response.json()

def main():
    data_stats = load_stats()
    data_categories = load_categories()
    encoded = get_encoded_image()
    img_tag = f'<img src="data:image/png;base64,{encoded}" width="28" style="vertical-align:middle; margin-right:10px;"/>'
    st.html(
            f"""
        <div class="custom-header">
            <div class="header-title">Prophecy</div>
            <div class="header-value" style="font-size: 28px;">Tableau de bord</div>
        </div>
        """
    )

    cost_raw = data_stats["estimated_total_cost"]
    cost_display = _fmt_compact_number(cost_raw)
    try:
        coverage_display = f"{float(data_stats['avg_coverage_days']):.2f} jours"
    except (TypeError, ValueError):
        coverage_display = str(data_stats["avg_coverage_days"])

    st.html(
        _kpi_metrics_section_html(data_stats, cost_display, coverage_display),
        )

    st.markdown(f"### {img_tag} Etat de stock sur 30 jours", unsafe_allow_html=True)
    with st.container(border=True):
        with st.container():
            data_grouped_reassort_dict = data_stats['alerts']
            
            data_grouped_reassort = [
                {"alert": key, "qty_to_order": value}
                for key, value in data_grouped_reassort_dict.items()
            ]
            base_colors = ['#025864', '#00d47e', '#f4c095', '#ee2e31', '#63474d']
            alert_to_color = {
                row["alert"]: base_colors[i % len(base_colors)]
                for i, row in enumerate(data_grouped_reassort)
            }
            fig = px.bar(
                data_grouped_reassort,
                x='alert',
                y='qty_to_order',
                color='alert',
                color_discrete_map=alert_to_color,
                labels={
                    "alert": "Etat du stock",
                    "qty_to_order": "Quantité à commander",
                },
            )
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig)
    
    
    
    st.markdown(
        f"### {img_tag} Recommandations d'approvisionnement",
        unsafe_allow_html=True
    )
    with st.container():
        category_selected = st.selectbox("Filtrer par catégorie", placeholder="Choisir une catégorie", options=[category['category'] for category in data_categories], index=None)
        col_1_1, col_1_2, col_1_3 = st.columns(3)
        col_2_1, col_2_2 = st.columns(2)
        category_id = None
        if category_selected is not None:
            category_id = [category['category_id'] for category in data_categories if category['category'] == category_selected][0]
        with col_1_1:
            # Rupture imminente, Forte demande, À commander, Stable, Stock OK, Ne pas recommander
            urgency_selected = st.selectbox("Niveau d'alerte", placeholder="Choisir un niveau d'alerte", options=["Rupture imminente", "Forte demande", "À commander", "Stable", "Stock OK", "Ne pas recommander"], index=None)
        with col_1_2:
            #Croissance, Maturité, Déclin, Obsolescence, Inactif
            growth_selected = st.selectbox("Tendance des ventes", placeholder="Choisir une tendance des ventes", options=["Croissance", "Maturité", "Déclin", "Obsolescence", "Inactif"], index=None)
        with col_1_3:
            #Quantité à commander minimum
            quantity_selected = st.number_input("Quantité à commander minimum", min_value=1, value=1, step=1)
        with col_2_1:
            limit_selected = st.number_input("Limite de résultats", min_value=1, value=100, step=50)
        with col_2_2:
            offset_selected = st.number_input("Décalage", min_value=0, value=0, step=50)
        data_reassort = make_reassort(category_id, urgency_selected, growth_selected, quantity_selected, limit_selected, offset_selected)
        st.html("<br>")
        if len(data_reassort) > 0:
            st.html(_reassort_dataframe_html(data_reassort, stock_color_map=alert_to_color))
        else:
            st.error("Pas de recommandations d'approvisionnement trouvées")


_inject_prophecy_styles()
main()
