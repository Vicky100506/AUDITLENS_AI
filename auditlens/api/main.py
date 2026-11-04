"""FastAPI Backend Service for AuditLens AI.

Provides RESTful endpoints for:
- POST /upload: Upload general ledger CSV, execute audit pipeline, cache results, return KPI summary.
- GET /results: Paginated, filterable, sortable table of flagged entries with explanations.
- GET /entry/{entry_id}: Full transaction metadata, features, rule triggers, and SHAP drivers.
- GET /export: Download flagged entries with risk scores and unified narratives as CSV.
- GET /summary: Retrieve current dataset summary and risk distribution KPIs.
- GET /health: Service and model health check.
"""

import io
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field

from auditlens.config import (
    DEFAULT_DATASET_PATH,
    HIGH_RISK_THRESHOLD,
    MEDIUM_RISK_THRESHOLD,
    SAVED_MODEL_PATH,
    WEIGHT_ML,
    WEIGHT_RULES,
)
from auditlens.engine.explain import AuditExplainer
from auditlens.engine.features import extract_features
from auditlens.engine.model import IsolationForestDetector, train_and_save_model
from auditlens.engine.rules import evaluate_rules
from auditlens.engine.scoring import compile_scored_ledger

REQUIRED_CSV_COLUMNS = [
    "entry_id",
    "posting_date",
    "posting_time",
    "account_code",
    "account_name",
    "vendor",
    "amount",
    "posted_by",
    "approved_by",
    "description",
]


class LedgerSummaryResponse(BaseModel):
    total_entries: int
    flagged_count: int
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int
    total_value_transacted: float
    flagged_value_transacted: float
    high_risk_threshold: float
    medium_risk_threshold: float


class FlaggedEntryItem(BaseModel):
    entry_id: str
    posting_date: str
    posting_time: str
    account_code: str
    account_name: str
    vendor: str
    amount: float
    posted_by: str
    approved_by: str
    description: str
    rule_score: float
    ml_score: float
    risk_score: float
    risk_level: str
    short_reasons: List[str]
    unified_narrative: Optional[str] = None


class PaginatedResultsResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    items: List[FlaggedEntryItem]


class FeatureDriverItem(BaseModel):
    feature: str
    value: float
    attribution: float
    reason: str


class EntryDetailResponse(BaseModel):
    entry_id: str
    posting_date: str
    posting_time: str
    account_code: str
    account_name: str
    vendor: str
    amount: float
    posted_by: str
    approved_by: str
    description: str
    rule_score: float
    ml_score: float
    risk_score: float
    risk_level: str
    rule_reasons: List[str]
    ml_reasons: List[str]
    top_drivers: List[FeatureDriverItem]
    unified_narrative: str
    features: Dict[str, Any]


class AppState:
    """In-memory cache for processed ledger data, model, and explainer."""

    def __init__(self) -> None:
        self.raw_df: Optional[pd.DataFrame] = None
        self.features_df: Optional[pd.DataFrame] = None
        self.scored_df: Optional[pd.DataFrame] = None
        self.detector: Optional[IsolationForestDetector] = None
        self.explainer: Optional[AuditExplainer] = None
        self.explanations_cache: Dict[str, Dict[str, Any]] = {}
        self.summary: Optional[Dict[str, Any]] = None

    def process_and_cache(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Execute full feature extraction, rules, ML scoring, and explanations."""
        if self.detector is None:
            raise RuntimeError("Model is not initialized.")

        # 1. Feature extraction
        feat_df = extract_features(df)

        # 2. Rule evaluation
        rule_scores, rule_reasons, _ = evaluate_rules(df, feat_df)

        # 3. ML Scoring
        ml_scores = self.detector.predict_score(feat_df)

        # 4. Compile scored ledger
        scored = compile_scored_ledger(
            raw_df=df,
            rule_scores=rule_scores,
            ml_scores=ml_scores,
            rule_reasons=rule_reasons,
            weight_rules=WEIGHT_RULES,
            weight_ml=WEIGHT_ML,
            high_threshold=HIGH_RISK_THRESHOLD,
            medium_threshold=MEDIUM_RISK_THRESHOLD,
        )

        # 5. Compute SHAP explanations for flagged rows
        flagged_mask = scored["is_flagged"].values
        flagged_raw = scored[flagged_mask].copy()
        flagged_feat = feat_df[flagged_mask].copy()

        exp_map: Dict[str, Dict[str, Any]] = {}
        if len(flagged_raw) > 0 and self.explainer is not None:
            explanations_list = self.explainer.explain_flagged_entries(flagged_raw, flagged_feat)
            for exp in explanations_list:
                exp_map[str(exp["entry_id"])] = exp

        # 6. Build KPI summary
        total_cnt = len(scored)
        flagged_cnt = int(scored["is_flagged"].sum())
        high_cnt = int((scored["risk_level"] == "High").sum())
        med_cnt = int((scored["risk_level"] == "Medium").sum())
        low_cnt = int((scored["risk_level"] == "Low").sum())
        total_val = float(scored["amount"].sum())
        flagged_val = float(scored[scored["is_flagged"]]["amount"].sum()) if flagged_cnt > 0 else 0.0

        summary = {
            "total_entries": total_cnt,
            "flagged_count": flagged_cnt,
            "high_risk_count": high_cnt,
            "medium_risk_count": med_cnt,
            "low_risk_count": low_cnt,
            "total_value_transacted": round(total_val, 2),
            "flagged_value_transacted": round(flagged_val, 2),
            "high_risk_threshold": HIGH_RISK_THRESHOLD,
            "medium_risk_threshold": MEDIUM_RISK_THRESHOLD,
        }

        # Cache in state
        self.raw_df = df
        self.features_df = feat_df
        self.scored_df = scored
        self.explanations_cache = exp_map
        self.summary = summary

        return summary


state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load or train model on startup and preload default synthetic dataset if available."""
    print("Initializing AuditLens AI Service...")
    # Load or fit model
    if SAVED_MODEL_PATH.exists():
        print(f"Loading existing Isolation Forest model from {SAVED_MODEL_PATH}")
        state.detector = IsolationForestDetector.load(SAVED_MODEL_PATH)
    elif DEFAULT_DATASET_PATH.exists():
        print("Training fresh Isolation Forest on default synthetic dataset...")
        raw_df = pd.read_csv(DEFAULT_DATASET_PATH)
        feat_df = extract_features(raw_df)
        state.detector = train_and_save_model(feat_df, SAVED_MODEL_PATH)
    else:
        print("No dataset or model found. Generating synthetic dataset first...")
        from auditlens.data.generate_ledger import generate_synthetic_ledger
        raw_df = generate_synthetic_ledger()
        feat_df = extract_features(raw_df)
        state.detector = train_and_save_model(feat_df, SAVED_MODEL_PATH)

    state.explainer = AuditExplainer(state.detector)

    # Pre-process default synthetic ledger so results are ready immediately
    if DEFAULT_DATASET_PATH.exists():
        print("Preloading and scoring default dataset (50k entries)...")
        raw_df = pd.read_csv(DEFAULT_DATASET_PATH)
        state.process_and_cache(raw_df)
        print("Default dataset preloaded successfully!")

    yield
    print("Shutting down AuditLens AI Service...")


app = FastAPI(
    title="AuditLens AI API",
    description="Explainable Journal Entry Anomaly Detection Service for Auditors",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for React frontend (Vite default ports 5173, 3000, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check() -> Dict[str, Any]:
    """Health status and dataset information."""
    return {
        "status": "healthy",
        "model_loaded": state.detector is not None and state.detector.is_fitted_,
        "entries_loaded": len(state.scored_df) if state.scored_df is not None else 0,
        "flagged_entries": state.summary["flagged_count"] if state.summary else 0,
    }


@app.get("/summary", response_model=LedgerSummaryResponse)
def get_summary() -> LedgerSummaryResponse:
    """Return summary KPI metrics for current ledger."""
    if state.summary is None:
        raise HTTPException(status_code=400, detail="No ledger data has been loaded or processed yet.")
    return LedgerSummaryResponse(**state.summary)


@app.post("/upload", response_model=LedgerSummaryResponse)
async def upload_ledger(file: UploadFile = File(...)) -> LedgerSummaryResponse:
    """Accept and validate a general ledger CSV file, execute pipeline, and return summary."""
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{file.filename}'. Please upload a valid .csv file.",
        )

    try:
        content = await file.read()
        # Read into pandas DataFrame
        df = pd.read_csv(io.BytesIO(content))
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to parse CSV file: {str(exc)}. Please check file formatting.",
        )

    if len(df) == 0:
        raise HTTPException(status_code=400, detail="Uploaded CSV file is completely empty.")

    # Validate required columns
    missing_cols = [col for col in REQUIRED_CSV_COLUMNS if col not in df.columns]
    if missing_cols:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Missing required general ledger columns: {missing_cols}. "
                f"Required schema: {REQUIRED_CSV_COLUMNS}"
            ),
        )

    # Execute end-to-end pipeline
    try:
        summary = state.process_and_cache(df)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error executing anomaly detection pipeline: {str(exc)}",
        )

    return LedgerSummaryResponse(**summary)


@app.get("/results", response_model=PaginatedResultsResponse)
def get_results(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(25, ge=1, le=500, description="Items per page"),
    risk_level: Optional[str] = Query(None, description="Filter by risk tier: 'All', 'High', 'Medium', 'Low'"),
    sort_by: str = Query("risk_score", description="Column to sort by"),
    sort_dir: str = Query("desc", description="Sort direction: 'asc' or 'desc'"),
    search: Optional[str] = Query(None, description="Text search filter across ID, account, vendor, user, desc"),
    only_flagged: bool = Query(True, description="Limit to flagged entries (High & Medium)"),
) -> PaginatedResultsResponse:
    """Return paginated, filterable, and sortable journal entry anomaly results."""
    if state.scored_df is None:
        raise HTTPException(status_code=400, detail="No ledger data available. Please upload a CSV first.")

    df = state.scored_df

    # 1. Flagged filter
    if only_flagged:
        df = df[df["is_flagged"]]

    # 2. Risk level filter
    if risk_level and risk_level.lower() != "all":
        df = df[df["risk_level"].str.lower() == risk_level.lower()]

    # 3. Text search
    if search and search.strip():
        q = search.strip().lower()
        search_mask = (
            df["entry_id"].astype(str).str.lower().str.contains(q)
            | df["account_name"].astype(str).str.lower().str.contains(q)
            | df["vendor"].astype(str).str.lower().str.contains(q)
            | df["posted_by"].astype(str).str.lower().str.contains(q)
            | df["description"].astype(str).str.lower().str.contains(q)
        )
        df = df[search_mask]

    # 4. Sorting
    ascending = sort_dir.lower() == "asc"
    valid_sort_cols = ["risk_score", "ml_score", "rule_score", "amount", "posting_date", "entry_id"]
    active_sort = sort_by if sort_by in valid_sort_cols else "risk_score"
    df = df.sort_values(by=active_sort, ascending=ascending)

    total_records = len(df)
    total_pages = max(1, (total_records + page_size - 1) // page_size)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size

    sliced = df.iloc[start_idx:end_idx]

    items: List[FlaggedEntryItem] = []
    for _, row in sliced.iterrows():
        eid = str(row["entry_id"])
        cached_exp = state.explanations_cache.get(eid)

        # Build short reasons list (combining rule reasons and top ML drivers)
        short_reasons: List[str] = []
        rule_reasons = row.get("rule_reasons", [])
        if isinstance(rule_reasons, list):
            short_reasons.extend(rule_reasons)
        elif isinstance(rule_reasons, str) and rule_reasons:
            short_reasons.append(rule_reasons)

        narrative = None
        if cached_exp:
            narrative = cached_exp.get("unified_narrative")
            for drv in cached_exp.get("top_drivers", []):
                if len(short_reasons) < 3:
                    short_reasons.append(drv.get("reason"))

        items.append(
            FlaggedEntryItem(
                entry_id=eid,
                posting_date=str(row["posting_date"]),
                posting_time=str(row["posting_time"]),
                account_code=str(row["account_code"]),
                account_name=str(row["account_name"]),
                vendor=str(row["vendor"]),
                amount=float(row["amount"]),
                posted_by=str(row["posted_by"]),
                approved_by=str(row["approved_by"]),
                description=str(row["description"]),
                rule_score=float(row["rule_score"]),
                ml_score=float(row["ml_score"]),
                risk_score=float(row["risk_score"]),
                risk_level=str(row["risk_level"]),
                short_reasons=short_reasons,
                unified_narrative=narrative,
            )
        )

    return PaginatedResultsResponse(
        total=total_records,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        items=items,
    )


@app.get("/entry/{entry_id}", response_model=EntryDetailResponse)
def get_entry_details(entry_id: str) -> EntryDetailResponse:
    """Return full details, feature values, rule violations, and SHAP drivers for a single entry."""
    if state.scored_df is None:
        raise HTTPException(status_code=400, detail="No ledger data loaded.")

    matches = state.scored_df[state.scored_df["entry_id"] == entry_id]
    if len(matches) == 0:
        raise HTTPException(status_code=404, detail=f"Journal entry '{entry_id}' not found.")

    row = matches.iloc[0]
    cached_exp = state.explanations_cache.get(entry_id)

    # If explanation was not precomputed (e.g. Low risk entry clicked in UI), compute dynamically
    if cached_exp is None and state.explainer is not None:
        single_raw = state.scored_df[state.scored_df["entry_id"] == entry_id]
        single_feat = state.features_df.loc[single_raw.index]
        exps = state.explainer.explain_flagged_entries(single_raw, single_feat)
        if exps:
            cached_exp = exps[0]
            state.explanations_cache[entry_id] = cached_exp

    top_drivers = []
    ml_reasons = []
    unified_narrative = ""
    if cached_exp:
        top_drivers = [FeatureDriverItem(**d) for d in cached_exp.get("top_drivers", [])]
        ml_reasons = cached_exp.get("ml_reasons", [])
        unified_narrative = cached_exp.get("unified_narrative", "")

    # Extract engineered feature dictionary for deep-dive inspection
    feat_dict = {}
    if state.features_df is not None and row.name in state.features_df.index:
        feat_dict = state.features_df.loc[row.name].to_dict()

    rule_reasons = row.get("rule_reasons", [])
    if isinstance(rule_reasons, str):
        rule_reasons = [rule_reasons]
    elif not isinstance(rule_reasons, list):
        rule_reasons = []

    return EntryDetailResponse(
        entry_id=str(row["entry_id"]),
        posting_date=str(row["posting_date"]),
        posting_time=str(row["posting_time"]),
        account_code=str(row["account_code"]),
        account_name=str(row["account_name"]),
        vendor=str(row["vendor"]),
        amount=float(row["amount"]),
        posted_by=str(row["posted_by"]),
        approved_by=str(row["approved_by"]),
        description=str(row["description"]),
        rule_score=float(row["rule_score"]),
        ml_score=float(row["ml_score"]),
        risk_score=float(row["risk_score"]),
        risk_level=str(row["risk_level"]),
        rule_reasons=rule_reasons,
        ml_reasons=ml_reasons,
        top_drivers=top_drivers,
        unified_narrative=unified_narrative,
        features=feat_dict,
    )


@app.get("/export")
def export_flagged_csv(
    risk_level: Optional[str] = Query(None, description="Optional filter by risk level"),
) -> StreamingResponse:
    """Export flagged entries with risk scores and explanation narratives as a downloadable CSV."""
    if state.scored_df is None:
        raise HTTPException(status_code=400, detail="No ledger data to export.")

    df = state.scored_df[state.scored_df["is_flagged"]].copy()

    if risk_level and risk_level.lower() != "all":
        df = df[df["risk_level"].str.lower() == risk_level.lower()]

    # Attach explanation narratives
    narratives = [
        state.explanations_cache.get(str(eid), {}).get("unified_narrative", "")
        for eid in df["entry_id"]
    ]
    df["audit_explanation"] = narratives

    # Format rule reasons as clean string
    df["rule_violations"] = df["rule_reasons"].apply(
        lambda r: "; ".join(r) if isinstance(r, list) else str(r)
    )

    export_cols = [
        "entry_id",
        "posting_date",
        "posting_time",
        "account_code",
        "account_name",
        "vendor",
        "amount",
        "posted_by",
        "approved_by",
        "description",
        "rule_score",
        "ml_score",
        "risk_score",
        "risk_level",
        "rule_violations",
        "audit_explanation",
    ]
    export_df = df[[c for c in export_cols if c in df.columns]]

    stream = io.StringIO()
    export_df.to_csv(stream, index=False)
    stream.seek(0)

    filename = f"auditlens_flagged_entries_{risk_level or 'all'}.csv"
    return StreamingResponse(
        io.BytesIO(stream.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("auditlens.api.main:app", host="0.0.0.0", port=8000, reload=True)
