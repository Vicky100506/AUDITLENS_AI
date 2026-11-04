"""Hybrid Risk Scoring Engine for AuditLens AI.

Combines auditor-designed heuristic rule scores and unsupervised machine learning
(Isolation Forest) anomaly scores into an overall risk score:
    risk_score = weight_rules * rule_score + weight_ml * ml_score

Categorizes entries into risk tiers:
- High Risk:   risk_score >= HIGH_RISK_THRESHOLD (default 0.70)
- Medium Risk: MEDIUM_RISK_THRESHOLD <= risk_score < HIGH_RISK_THRESHOLD (default 0.40)
- Low Risk:    risk_score < MEDIUM_RISK_THRESHOLD (default 0.40)

Returns the ledger entries enriched with scores and sorted by risk_score descending.
"""

from typing import List, Optional, Tuple

import numpy as np
import pandas as pd

from auditlens.config import (
    HIGH_RISK_THRESHOLD,
    MEDIUM_RISK_THRESHOLD,
    WEIGHT_ML,
    WEIGHT_RULES,
)


def calculate_risk_scores(
    rule_scores: pd.Series,
    ml_scores: np.ndarray,
    weight_rules: float = WEIGHT_RULES,
    weight_ml: float = WEIGHT_ML,
) -> np.ndarray:
    """Calculate the weighted hybrid risk score in [0, 1].

    Parameters:
        rule_scores: Array or Series of rule heuristic scores in [0, 1].
        ml_scores: Array of Isolation Forest normalized anomaly scores in [0, 1].
        weight_rules: Weight assigned to rule violations (default 0.50).
        weight_ml: Weight assigned to ML anomaly score (default 0.50).

    Returns:
        np.ndarray of risk scores clipped to [0, 1].
    """
    # Normalize weights if they do not sum to 1.0
    total_w = weight_rules + weight_ml
    w_rules = weight_rules / total_w
    w_ml = weight_ml / total_w

    r_arr = np.asarray(rule_scores, dtype=float)
    m_arr = np.asarray(ml_scores, dtype=float)

    combined = (w_rules * r_arr) + (w_ml * m_arr)
    return np.clip(combined, 0.0, 1.0)


def assign_risk_levels(
    risk_scores: np.ndarray,
    high_threshold: float = HIGH_RISK_THRESHOLD,
    medium_threshold: float = MEDIUM_RISK_THRESHOLD,
) -> np.ndarray:
    """Categorize continuous risk scores into 'High', 'Medium', or 'Low' risk levels."""
    levels = np.empty(len(risk_scores), dtype=object)
    levels[risk_scores >= high_threshold] = "High"
    levels[(risk_scores >= medium_threshold) & (risk_scores < high_threshold)] = "Medium"
    levels[risk_scores < medium_threshold] = "Low"
    return levels


def compile_scored_ledger(
    raw_df: pd.DataFrame,
    rule_scores: pd.Series,
    ml_scores: np.ndarray,
    rule_reasons: List[List[str]],
    weight_rules: float = WEIGHT_RULES,
    weight_ml: float = WEIGHT_ML,
    high_threshold: float = HIGH_RISK_THRESHOLD,
    medium_threshold: float = MEDIUM_RISK_THRESHOLD,
    sort_by_risk: bool = True,
) -> pd.DataFrame:
    """Combine raw ledger with rule scores, ML scores, combined risk score, risk level,

    and rule reason strings, sorted by risk_score descending.
    """
    scored_df = raw_df.copy()

    # Calculate hybrid score and risk level
    risk_scores = calculate_risk_scores(
        rule_scores=rule_scores,
        ml_scores=ml_scores,
        weight_rules=weight_rules,
        weight_ml=weight_ml,
    )
    risk_levels = assign_risk_levels(
        risk_scores=risk_scores,
        high_threshold=high_threshold,
        medium_threshold=medium_threshold,
    )

    scored_df["rule_score"] = np.round(rule_scores.values, 4)
    scored_df["ml_score"] = np.round(ml_scores, 4)
    scored_df["risk_score"] = np.round(risk_scores, 4)
    scored_df["risk_level"] = risk_levels
    scored_df["rule_reasons"] = rule_reasons
    scored_df["is_flagged"] = scored_df["risk_level"].isin(["High", "Medium"])

    if sort_by_risk:
        scored_df = scored_df.sort_values(by=["risk_score", "amount"], ascending=[False, False]).reset_index(drop=True)

    return scored_df


if __name__ == "__main__":
    from auditlens.config import DEFAULT_DATASET_PATH, SAVED_MODEL_PATH
    from auditlens.engine.features import extract_features
    from auditlens.engine.model import IsolationForestDetector
    from auditlens.engine.rules import evaluate_rules
    import sys

    print("Testing Hybrid Risk Scoring Engine...")
    if not DEFAULT_DATASET_PATH.exists() or not SAVED_MODEL_PATH.exists():
        print("Missing dataset or saved model. Ensure Stages 1-4 ran.")
        sys.exit(1)

    raw_df = pd.read_csv(DEFAULT_DATASET_PATH)
    features_df = extract_features(raw_df)
    rule_scores, rule_reasons, _ = evaluate_rules(raw_df, features_df)

    detector = IsolationForestDetector.load(SAVED_MODEL_PATH)
    ml_scores = detector.predict_score(features_df)

    scored_df = compile_scored_ledger(raw_df, rule_scores, ml_scores, rule_reasons)

    print("\nRisk Scoring Profile:")
    print(f"Total Transactions: {len(scored_df):,}")
    print("\nBreakdown by Risk Level:")
    counts = scored_df["risk_level"].value_counts()
    for level in ["High", "Medium", "Low"]:
        cnt = counts.get(level, 0)
        pct = (cnt / len(scored_df)) * 100
        print(f"  {level:<8} Risk: {cnt:>6,} entries ({pct:5.2f}%)")

    total_flagged = scored_df["is_flagged"].sum()
    print(f"\nTotal Flagged (High + Medium): {total_flagged:,} ({(total_flagged / len(scored_df)) * 100:.2f}%)")

    print("\nTop 5 Highest Risk Journal Entries:")
    sample_cols = ["entry_id", "posting_date", "account_name", "amount", "rule_score", "ml_score", "risk_score", "risk_level"]
    print(scored_df[sample_cols].head(5).to_string(index=False))

    print("\nStage 5 Risk Scoring successfully verified!")
