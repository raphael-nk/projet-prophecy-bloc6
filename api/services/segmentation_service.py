from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

MODELS_DIR = Path(os.environ.get("MODELS_DIR", "models"))
DATA_DIR = Path(os.environ.get("DATA_DIR", "data"))

MODEL_SEGMENTATION = Path(
    os.environ.get("MODEL_SEGMENTATION", str(MODELS_DIR / "kmeans_bundle_v1.joblib"))
)
RFM_CSV = Path(os.environ.get("RFM_SEGMENTS_CSV", str(DATA_DIR / "rfm_segments.csv")))
RECO_CSV = Path(
    os.environ.get(
        "CUSTOMER_RECOMMENDATION_CSV",
        str(DATA_DIR / "customer_recommendation.csv"),
    )
)
DEFAULT_CUSTOMER_KMEANS_CSV = DATA_DIR / "customer_kmeans.csv"

_kmeans_loaded_path: Path | None = None


def _rfm_csv_path() -> Path:
    return RFM_CSV.expanduser().resolve()


def _kmeans_csv_path() -> Path:
    p = os.environ.get("CUSTOMER_RECOMMENDATION_CSV") or os.environ.get("KMEANS_CUSTOMERS_CSV")
    if p:
        return Path(p).expanduser().resolve()
    if RECO_CSV.is_file():
        return RECO_CSV.expanduser().resolve()
    return DEFAULT_CUSTOMER_KMEANS_CSV.expanduser().resolve()


@lru_cache(maxsize=1)
def _load_kmeans_bundle() -> dict:
    path = MODEL_SEGMENTATION.expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Bundle KMeans introuvable : {path}")
    return joblib.load(path)


def get_kmeans_model():
    bundle = _load_kmeans_bundle()
    return bundle["kmeans"], bundle["scaler"], bundle["macro_cols"]


@lru_cache(maxsize=1)
def _load_df() -> pd.DataFrame:
    path = _rfm_csv_path()
    if not path.is_file():
        raise FileNotFoundError(f"Fichier introuvable : {path}")
    df = pd.read_csv(path)
    for col in df.columns:
        if col.startswith("Tag_") or col in ("Tag_B2B",):
            if df[col].dtype == object:
                df[col] = df[col].map(
                    lambda x: {"true": True, "false": False, "True": True, "False": False}.get(
                        str(x), x
                    )
                )
    return df


def get_df() -> pd.DataFrame:
    return _load_df()


@lru_cache(maxsize=1)
def _load_kmeans_df() -> pd.DataFrame:
    global _kmeans_loaded_path
    path = _kmeans_csv_path()
    if not path.is_file():
        raise FileNotFoundError(
            f"Fichier K-means / reco introuvable : {path} "
            f"(générer avec train_kmeans.ipynb ou définir CUSTOMER_RECOMMENDATION_CSV)"
        )
    _kmeans_loaded_path = path
    return pd.read_csv(path)


def get_kmeans_df() -> pd.DataFrame:
    return _load_kmeans_df()


def kmeans_source_path() -> Path:
    _ = get_kmeans_df()
    return _kmeans_loaded_path or _kmeans_csv_path()


def _interest_column(df: pd.DataFrame) -> str | None:
    for name in ("Tag_Interest", "interest_tag", "Top_Interest"):
        if name in df.columns:
            return name
    return None


def _apply_filters(
    df: pd.DataFrame,
    *,
    segment: str | None = None,
    tag_b2b: bool | None = None,
    tag_christmas: bool | None = None,
    tag_holidays: bool | None = None,
    interest: str | None = None,
    interest_contains: str | None = None,
    partner_id: int | None = None,
    partner_name_contains: str | None = None,
    min_monetary: float | None = None,
    max_monetary: float | None = None,
    min_recency_days: int | None = None,
    max_recency_days: int | None = None,
    min_frequency: int | None = None,
    max_frequency: int | None = None,
    min_r_score: int | None = None,
    max_r_score: int | None = None,
    min_f_score: int | None = None,
    max_f_score: int | None = None,
    min_m_score: int | None = None,
    max_m_score: int | None = None,
) -> pd.DataFrame:
    out = df
    if segment is not None:
        out = out[out["segment"].astype(str) == segment]
    if partner_id is not None:
        out = out[out["partner_id"] == partner_id]
    if tag_b2b is not None and "Tag_B2B" in out.columns:
        out = out[out["Tag_B2B"] == tag_b2b]
    if tag_christmas is not None and "Tag_Christmas_Shopper" in out.columns:
        out = out[out["Tag_Christmas_Shopper"] == tag_christmas]
    if tag_holidays is not None and "Tag_Holidays_Shopper" in out.columns:
        out = out[out["Tag_Holidays_Shopper"] == tag_holidays]
    icol = _interest_column(out)
    if icol and interest is not None:
        out = out[out[icol].astype(str) == interest]
    if icol and interest_contains:
        s = out[icol].astype(str).str.contains(interest_contains, case=False, na=False)
        out = out[s]
    if partner_name_contains and "partner_name" in out.columns:
        s = out["partner_name"].astype(str).str.contains(partner_name_contains, case=False, na=False)
        out = out[s]
    if min_monetary is not None and "monetary" in out.columns:
        out = out[out["monetary"] >= min_monetary]
    if max_monetary is not None and "monetary" in out.columns:
        out = out[out["monetary"] <= max_monetary]
    if min_recency_days is not None and "recency_days" in out.columns:
        out = out[out["recency_days"] >= min_recency_days]
    if max_recency_days is not None and "recency_days" in out.columns:
        out = out[out["recency_days"] <= max_recency_days]
    if min_frequency is not None and "frequency" in out.columns:
        out = out[out["frequency"] >= min_frequency]
    if max_frequency is not None and "frequency" in out.columns:
        out = out[out["frequency"] <= max_frequency]
    if min_r_score is not None and "R_score" in out.columns:
        out = out[out["R_score"] >= min_r_score]
    if max_r_score is not None and "R_score" in out.columns:
        out = out[out["R_score"] <= max_r_score]
    if min_f_score is not None and "F_score" in out.columns:
        out = out[out["F_score"] >= min_f_score]
    if max_f_score is not None and "F_score" in out.columns:
        out = out[out["F_score"] <= max_f_score]
    if min_m_score is not None and "M_score" in out.columns:
        out = out[out["M_score"] >= min_m_score]
    if max_m_score is not None and "M_score" in out.columns:
        out = out[out["M_score"] <= max_m_score]
    return out


def _records_slice(df: pd.DataFrame, limit: int, offset: int) -> list[dict[str, Any]]:
    sub = df.iloc[offset : offset + limit]
    return sub.where(sub.notna(), None).to_dict(orient="records")


def _apply_kmeans_filters(
    df: pd.DataFrame,
    *,
    cluster_affinity: int | None = None,
    segment: str | None = None,
    partner_id: int | None = None,
    partner_name_contains: str | None = None,
    cluster_profile_macro: str | None = None,
    recommended_macro_primary: str | None = None,
    recommended_macro_secondary: str | None = None,
    recommended_macro_tertiary: str | None = None,
    macro_contains: str | None = None,
    recommended_leaf_primary: str | None = None,
    leaf_contains: str | None = None,
) -> pd.DataFrame:
    out = df
    if cluster_affinity is not None and "cluster_affinity" in out.columns:
        out = out[out["cluster_affinity"] == cluster_affinity]
    if segment is not None and "segment" in out.columns:
        out = out[out["segment"].astype(str) == segment]
    if partner_id is not None and "partner_id" in out.columns:
        out = out[out["partner_id"] == partner_id]
    if partner_name_contains and "partner_name" in out.columns:
        s = out["partner_name"].astype(str).str.contains(
            partner_name_contains, case=False, na=False
        )
        out = out[s]
    if cluster_profile_macro is not None and "cluster_profile_macro" in out.columns:
        out = out[out["cluster_profile_macro"].astype(str) == cluster_profile_macro]
    if recommended_macro_primary is not None and "recommended_macro_primary" in out.columns:
        out = out[out["recommended_macro_primary"].astype(str) == recommended_macro_primary]
    if recommended_macro_secondary is not None and "recommended_macro_secondary" in out.columns:
        out = out[out["recommended_macro_secondary"].astype(str) == recommended_macro_secondary]
    if recommended_macro_tertiary is not None and "recommended_macro_tertiary" in out.columns:
        out = out[out["recommended_macro_tertiary"].astype(str) == recommended_macro_tertiary]
    if macro_contains:
        macro_cols = [
            "recommended_macro_primary",
            "recommended_macro_secondary",
            "recommended_macro_tertiary",
            "cluster_profile_macro",
        ]
        mask = pd.Series(False, index=out.index)
        for c in macro_cols:
            if c in out.columns:
                mask |= out[c].astype(str).str.contains(macro_contains, case=False, na=False)
        out = out[mask]
    if recommended_leaf_primary is not None and "recommended_leaf_primary" in out.columns:
        out = out[out["recommended_leaf_primary"].astype(str) == recommended_leaf_primary]
    if leaf_contains:
        leaf_cols = [
            "recommended_leaf_primary",
            "recommended_leaf_secondary",
            "recommended_leaf_tertiary",
        ]
        mask = pd.Series(False, index=out.index)
        for c in leaf_cols:
            if c in out.columns:
                mask |= out[c].astype(str).str.contains(leaf_contains, case=False, na=False)
        out = out[mask]
    return out


def reload_segmentation():
    _load_df.cache_clear()
    _load_kmeans_df.cache_clear()
    _load_kmeans_bundle.cache_clear()
