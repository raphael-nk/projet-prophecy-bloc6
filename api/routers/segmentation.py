from __future__ import annotations

from enum import Enum
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from services import segmentation_service as svc

router = APIRouter()


class CustomerListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[dict[str, Any]]


class SegmentCount(BaseModel):
    segment: str
    count: int


class SegmentRevenue(BaseModel):
    segment: str
    ca: float


class SegmentsResponse(BaseModel):
    total_clients: int
    total_ca: float
    by_segment: list[SegmentCount]
    by_segment_ca: list[SegmentRevenue]
    names: list[str]


class InterestCount(BaseModel):
    interest: str
    count: int


class SegmentInterestBreakdown(BaseModel):
    segment: str
    total_clients: int
    by_interest: list[InterestCount]


class InterestsBySegmentResponse(BaseModel):
    title: str
    interest_column: str
    source_csv: str
    total_clients: int
    segments: list[SegmentInterestBreakdown]


class DashboardKpisResponse(BaseModel):
    source_csv: str
    total_clients: int
    average_monetary: float
    champions_count: int
    champions_pct: float
    b2b_count: int
    b2b_pct: float


class ClusterCount(BaseModel):
    cluster: int
    count: int


class ClustersSummaryResponse(BaseModel):
    total_clients: int
    k_clusters: int | None
    source_csv: str
    by_cluster: list[ClusterCount]


class RfmTag(str, Enum):
    b2b = "b2b"
    christmas = "christmas"
    holidays = "holidays"


@router.post("/reload")
def reload_cache() -> dict[str, str]:
    """Vide les caches pandas après regénération des CSV."""
    svc.reload_segmentation()
    return {"status": "cache_cleared", "caches": ["rfm", "kmeans"]}


@router.get("/segments", response_model=SegmentsResponse)
def segments_overview() -> SegmentsResponse:
    df = svc.get_df()
    vc = df["segment"].value_counts()
    names = sorted(df["segment"].astype(str).unique().tolist())
    ca_by_segment: list[SegmentRevenue] = []
    total_ca = 0.0
    if "monetary" in df.columns:
        ca_s = (
            df.groupby("segment", as_index=False)["monetary"]
            .sum()
            .sort_values("monetary", ascending=False)
        )
        ca_by_segment = [
            SegmentRevenue(segment=str(row["segment"]), ca=float(row["monetary"]))
            for _, row in ca_s.iterrows()
        ]
        total_ca = float(df["monetary"].sum())
    return SegmentsResponse(
        total_clients=len(df),
        total_ca=total_ca,
        by_segment=[SegmentCount(segment=str(k), count=int(v)) for k, v in vc.items()],
        by_segment_ca=ca_by_segment,
        names=names,
    )


@router.get("/segments/interest", response_model=InterestsBySegmentResponse)
def interests_by_segment(
    top_n_interests: int | None = Query(
        None,
        ge=1,
        le=50,
        description="Limiter aux N intérêts les plus fréquents (sur toute la base)",
    ),
) -> InterestsBySegmentResponse:
    df = svc.get_df()
    col = svc._interest_column(df)
    if not col:
        raise HTTPException(
            status_code=501,
            detail="Aucune colonne d'intérêt (Tag_Interest / interest_tag / Top_Interest)",
        )
    sub = df.dropna(subset=[col]).copy()
    sub[col] = sub[col].astype(str).str.strip()
    sub = sub[sub[col].ne("") & sub[col].ne("nan")]
    if sub.empty:
        raise HTTPException(status_code=501, detail="Aucune valeur d'intérêt exploitable")
    if top_n_interests is not None:
        top_labels = sub[col].value_counts().head(top_n_interests).index.tolist()
        sub = sub[sub[col].isin(top_labels)]
    seg_order = sorted(sub["segment"].astype(str).unique().tolist())
    breakdown: list[SegmentInterestBreakdown] = []
    for seg in seg_order:
        part = sub[sub["segment"].astype(str) == seg]
        vc = part[col].value_counts()
        by_i = [
            InterestCount(interest=str(k), count=int(v))
            for k, v in sorted(vc.items(), key=lambda kv: (-kv[1], str(kv[0])))
        ]
        breakdown.append(
            SegmentInterestBreakdown(segment=seg, total_clients=len(part), by_interest=by_i)
        )
    return InterestsBySegmentResponse(
        title="Intérêts majeurs par segment",
        interest_column=col,
        source_csv=str(svc._rfm_csv_path().resolve()),
        total_clients=len(df),
        segments=breakdown,
    )


@router.get("/dashboard/kpis", response_model=DashboardKpisResponse)
def dashboard_kpis() -> DashboardKpisResponse:
    df = svc.get_df()
    total = int(len(df))
    if total == 0:
        return DashboardKpisResponse(
            source_csv=str(svc._rfm_csv_path().resolve()),
            total_clients=0,
            average_monetary=0.0,
            champions_count=0,
            champions_pct=0.0,
            b2b_count=0,
            b2b_pct=0.0,
        )

    avg_monetary = 0.0
    if "monetary" in df.columns:
        avg_monetary = float(df["monetary"].fillna(0).mean())

    champions_count = 0
    if "segment" in df.columns:
        champions_count = int(df["segment"].astype(str).eq("Champions").sum())
    champions_pct = (champions_count / total) * 100.0

    b2b_count = 0
    if "Tag_B2B" in df.columns:
        b2b_count = int(df["Tag_B2B"].fillna(False).astype(bool).sum())
    b2b_pct = (b2b_count / total) * 100.0

    return DashboardKpisResponse(
        source_csv=str(svc._rfm_csv_path().resolve()),
        total_clients=total,
        average_monetary=avg_monetary,
        champions_count=champions_count,
        champions_pct=round(champions_pct, 2),
        b2b_count=b2b_count,
        b2b_pct=round(b2b_pct, 2),
    )


@router.get("/interests", response_model=list[dict[str, Any]])
def interests_list(
    min_clients: int = Query(1, ge=1, description="Nombre minimum de clients pour inclure la macro"),
) -> list[dict[str, Any]]:
    df = svc.get_df()
    col = svc._interest_column(df)
    if not col:
        return []
    vc = df[col].astype(str).value_counts()
    return [
        {"interest": str(k), "count": int(v)}
        for k, v in vc.items()
        if v >= min_clients
    ]


@router.get("/customers", response_model=CustomerListResponse)
def list_customers(
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
    min_r_score: int | None = Query(None, ge=1, le=5),
    max_r_score: int | None = Query(None, ge=1, le=5),
    min_f_score: int | None = Query(None, ge=1, le=5),
    max_f_score: int | None = Query(None, ge=1, le=5),
    min_m_score: int | None = Query(None, ge=1, le=5),
    max_m_score: int | None = Query(None, ge=1, le=5),
    limit: int = Query(100, ge=1, le=2000),
    offset: int = Query(0, ge=0),
) -> CustomerListResponse:
    df = svc._apply_filters(
        svc.get_df(),
        segment=segment,
        tag_b2b=tag_b2b,
        tag_christmas=tag_christmas,
        tag_holidays=tag_holidays,
        interest=interest,
        interest_contains=interest_contains,
        partner_id=partner_id,
        partner_name_contains=partner_name_contains,
        min_monetary=min_monetary,
        max_monetary=max_monetary,
        min_recency_days=min_recency_days,
        max_recency_days=max_recency_days,
        min_frequency=min_frequency,
        max_frequency=max_frequency,
        min_r_score=min_r_score,
        max_r_score=max_r_score,
        min_f_score=min_f_score,
        max_f_score=max_f_score,
        min_m_score=min_m_score,
        max_m_score=max_m_score,
    )
    total = len(df)
    items = svc._records_slice(df, limit, offset)
    return CustomerListResponse(total=total, limit=limit, offset=offset, items=items)


@router.get("/customers/{partner_id}")
def get_customer(partner_id: int) -> dict[str, Any]:
    df = svc._apply_filters(svc.get_df(), partner_id=partner_id)
    if df.empty:
        raise HTTPException(status_code=404, detail="Client introuvable")
    return svc._records_slice(df, 1, 0)[0]


@router.get("/by-tag/{tag}/customers", response_model=CustomerListResponse)
def customers_by_tag(
    tag: RfmTag,
    value: bool = Query(
        True,
        description="b2b: True=B2B ; christmas/holidays: True=avec le tag saisonnier",
    ),
    limit: int = Query(100, ge=1, le=2000),
    offset: int = Query(0, ge=0),
) -> CustomerListResponse:
    kw: dict[str, Any] = {}
    if tag is RfmTag.b2b:
        kw["tag_b2b"] = value
    elif tag is RfmTag.christmas:
        kw["tag_christmas"] = value
    else:
        kw["tag_holidays"] = value
    df = svc._apply_filters(svc.get_df(), **kw)
    total = len(df)
    return CustomerListResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=svc._records_slice(df, limit, offset),
    )


@router.get("/clusters", response_model=ClustersSummaryResponse)
def clusters_summary() -> ClustersSummaryResponse:
    df = svc.get_kmeans_df()
    if "cluster_affinity" not in df.columns:
        raise HTTPException(status_code=501, detail="Colonne cluster_affinity absente")
    vc = df["cluster_affinity"].value_counts().sort_index()
    k = None
    if "k_clusters" in df.columns and len(df):
        try:
            k = int(df["k_clusters"].iloc[0])
        except (TypeError, ValueError):
            k = None
    return ClustersSummaryResponse(
        total_clients=len(df),
        k_clusters=k,
        source_csv=str(svc.kmeans_source_path().resolve()),
        by_cluster=[ClusterCount(cluster=int(k), count=int(v)) for k, v in vc.items()],
    )


@router.get("/reco/customers", response_model=CustomerListResponse)
def reco_list_customers(
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
    limit: int = Query(100, ge=1, le=2000),
    offset: int = Query(0, ge=0),
) -> CustomerListResponse:
    df = svc.get_kmeans_df()
    if leaf_contains or recommended_leaf_primary:
        if "recommended_leaf_primary" not in df.columns:
            raise HTTPException(
                status_code=501,
                detail="Colonnes recommended_leaf_* absentes (exporter customer_recommendation.csv)",
            )
    df = svc._apply_kmeans_filters(
        df,
        cluster_affinity=cluster_affinity,
        segment=segment,
        partner_id=partner_id,
        partner_name_contains=partner_name_contains,
        cluster_profile_macro=cluster_profile_macro,
        recommended_macro_primary=recommended_macro_primary,
        recommended_macro_secondary=recommended_macro_secondary,
        recommended_macro_tertiary=recommended_macro_tertiary,
        macro_contains=macro_contains,
        recommended_leaf_primary=recommended_leaf_primary,
        leaf_contains=leaf_contains,
    )
    total = len(df)
    return CustomerListResponse(
        total=total, limit=limit, offset=offset, items=svc._records_slice(df, limit, offset)
    )


@router.get("/reco/customers/{partner_id}")
def reco_get_customer(partner_id: int) -> dict[str, Any]:
    df = svc._apply_kmeans_filters(svc.get_kmeans_df(), partner_id=partner_id)
    if df.empty:
        raise HTTPException(status_code=404, detail="Client introuvable dans les données de recommandation")
    return svc._records_slice(df, 1, 0)[0]
