"""Explainability Engine for AuditLens AI using SHAP TreeExplainer.

Explains machine learning anomaly flags by decomposing Isolation Forest path lengths
using SHAP TreeExplainer. Extracts top 3 feature drivers per flagged entry, maps them
into plain-English auditor explanations, and synthesizes them with triggered rule reasons.

Explanations are computed strictly for flagged entries (High and Medium risk) to ensure
instant UI responsiveness.
"""

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import shap

from auditlens.config import APPROVAL_LIMIT, MODEL_FEATURE_COLUMNS
from auditlens.engine.model import IsolationForestDetector


def format_feature_driver(
    feature_name: str,
    feature_val: float,
    shap_val: float,
    row: pd.Series,
) -> str:
    """Translate a numeric feature and its SHAP contribution into an accurate plain-English explanation."""
    amt = float(row.get("amount", 0.0))
    account_name = str(row.get("account_name", "the account"))

    if feature_name == "amount_to_limit_ratio":
        if amt > APPROVAL_LIMIT:
            return f"Amount (INR {amt:,.2f}) exceeds the INR {APPROVAL_LIMIT:,.0f} corporate approval limit"
        elif amt >= 0.95 * APPROVAL_LIMIT:
            return f"Amount (INR {amt:,.2f}) sits directly below the INR {APPROVAL_LIMIT:,.0f} approval ceiling (structuring indicator)"
        return f"Transaction amount (INR {amt:,.2f}) is elevated relative to approval limits"

    elif feature_name == "account_amount_zscore":
        z = float(feature_val)
        return f"Amount deviates significantly from {account_name}'s baseline spending pattern (Z-score: {z:+.2f})"

    elif feature_name in ["log_amount", "amount"]:
        return f"Magnitude of INR {amt:,.2f} is an outlier compared to historical baseline journal entries"

    elif feature_name == "is_weekend":
        if int(feature_val) == 1:
            day_name = pd.to_datetime(row.get("posting_date")).day_name() if row.get("posting_date") else "Weekend"
            return f"Transaction recorded outside normal working days on a {day_name}"
        return f"Posting day patterns differ from baseline weekly distribution"

    elif feature_name == "day_of_week":
        day_name = pd.to_datetime(row.get("posting_date")).day_name() if row.get("posting_date") else "atypical day"
        return f"Posting scheduled on an atypical day ({day_name}) for this transaction type"

    elif feature_name == "is_holiday":
        if int(feature_val) == 1:
            return f"Journal entry recorded on an official Indian gazetted public holiday ({row.get('posting_date')})"
        return f"Calendar scheduling patterns deviate from historical baseline"

    elif feature_name == "hour_posted":
        hr = int(feature_val)
        if hr < 9 or hr >= 18:
            return f"Entry logged during off-business hours at {hr:02d}:00"
        return f"Entry timing at {hr:02d}:00 deviates from account-specific posting hours"

    elif feature_name == "is_round_amount":
        if int(feature_val) == 1:
            return f"Clean round figure of INR {amt:,.2f} (multiples of INR 10,000 often indicate unbacked estimates)"
        return f"Transaction precision characteristics differ from standard vendor invoices"

    elif feature_name == "same_poster_approver":
        if int(feature_val) == 1:
            return f"Segregation of duties violation: user '{row.get('posted_by')}' posted and approved this entry"
        return f"Approval routing workflow exhibits unusual pairing pattern"

    elif feature_name == "description_length":
        desc = str(row.get("description", ""))
        if len(desc) <= 3:
            return f"Journal narrative is missing or suspiciously brief ('{desc}')"
        return f"Description length ({len(desc)} characters) deviates from typical documentation"

    elif feature_name == "duplicate_count":
        cnt = int(feature_val)
        if cnt > 1:
            return f"Shares identical amount, account, vendor, and posting date with {cnt} entries"
        return f"Transaction clustering characteristics indicate repeated profile"

    elif feature_name == "vendor_posting_freq":
        return f"Vendor '{row.get('vendor')}' posting frequency deviates notably from typical trade activity"

    elif feature_name == "user_posting_freq":
        return f"Posting velocity for user '{row.get('posted_by')}' is irregular compared to peer benchmarks"

    return f"Feature '{feature_name}' (value: {feature_val:.2f}) contributed unusually to anomaly classification"


class AuditExplainer:
    """Generates combined rule and SHAP audit narratives for flagged general ledger entries."""

    def __init__(self, detector: IsolationForestDetector) -> None:
        self.detector = detector
        self.model = detector.model
        self.scaler = detector.scaler
        self.feature_names = list(detector.feature_names_)
        # TreeExplainer for Isolation Forest
        self.explainer = shap.TreeExplainer(self.model)

    def explain_flagged_entries(
        self,
        flagged_raw_df: pd.DataFrame,
        flagged_features_df: pd.DataFrame,
        top_k: int = 3,
    ) -> List[Dict[str, Any]]:
        """Compute SHAP explanations and synthesis for flagged entries.

        Parameters:
            flagged_raw_df: Raw ledger DataFrame containing only flagged entries.
            flagged_features_df: Feature DataFrame for the flagged entries.
            top_k: Number of top anomalous features to extract per entry (default 3).

        Returns:
            List of dictionaries containing top features, attributions, plain-English factors,
            and synthesized audit narrative.
        """
        if len(flagged_raw_df) == 0:
            return []

        # Standardize features using fitted scaler
        features_subset = flagged_features_df[self.feature_names]
        X_scaled = self.scaler.transform(features_subset)

        # In Isolation Forest TreeExplainer, smaller path lengths (more negative SHAP values)
        # push an instance toward anomaly isolation.
        # So anomaly contribution = -1 * shap_value
        shap_matrix = self.explainer.shap_values(X_scaled)
        anomaly_contributions = -shap_matrix

        explanations: List[Dict[str, Any]] = []

        for i in range(len(flagged_raw_df)):
            row_raw = flagged_raw_df.iloc[i]
            row_features = flagged_features_df.iloc[i]
            contribs = anomaly_contributions[i]

            # Sort features by anomaly contribution descending
            top_indices = np.argsort(contribs)[::-1][:top_k]

            top_drivers: List[Dict[str, Any]] = []
            ml_reasons: List[str] = []

            for idx in top_indices:
                feat_name = self.feature_names[idx]
                feat_val = float(row_features[feat_name])
                attr_val = float(contribs[idx])

                # Generate plain English reason
                reason_str = format_feature_driver(feat_name, feat_val, attr_val, row_raw)
                top_drivers.append({
                    "feature": feat_name,
                    "value": round(feat_val, 4),
                    "attribution": round(attr_val, 4),
                    "reason": reason_str,
                })
                ml_reasons.append(reason_str)

            # Retrieve rule reasons from raw row if present
            rule_reasons = row_raw.get("rule_reasons", [])
            if isinstance(rule_reasons, str):
                rule_reasons = [rule_reasons]
            elif not isinstance(rule_reasons, list):
                rule_reasons = []

            # Synthesize into unified narrative
            unified_narrative = self._synthesize_narrative(
                entry_id=str(row_raw.get("entry_id", "")),
                risk_level=str(row_raw.get("risk_level", "Medium")),
                rule_reasons=rule_reasons,
                ml_reasons=ml_reasons,
            )

            explanations.append({
                "entry_id": row_raw.get("entry_id"),
                "top_drivers": top_drivers,
                "rule_reasons": rule_reasons,
                "ml_reasons": ml_reasons,
                "unified_narrative": unified_narrative,
            })

        return explanations

    def _synthesize_narrative(
        self,
        entry_id: str,
        risk_level: str,
        rule_reasons: List[str],
        ml_reasons: List[str],
    ) -> str:
        """Create a cohesive, executive auditor narrative combining deterministic rule violations

        and machine learning statistical anomalies.
        """
        parts: List[str] = []

        if rule_reasons:
            rule_text = "; ".join(rule_reasons)
            parts.append(f"Audit Policy Violations: {rule_text}.")

        if ml_reasons:
            ml_text = "; ".join(ml_reasons)
            parts.append(f"Statistical Anomaly Drivers (Isolation Forest): {ml_text}.")

        if not parts:
            return f"Entry flagged as {risk_level} Risk based on multivariate anomalous score profile."

        return " ".join(parts)


if __name__ == "__main__":
    from auditlens.config import DEFAULT_DATASET_PATH, SAVED_MODEL_PATH
    from auditlens.engine.features import extract_features
    from auditlens.engine.rules import evaluate_rules
    from auditlens.engine.scoring import compile_scored_ledger
    import sys

    print("Testing SHAP Explanations Engine...")
    if not DEFAULT_DATASET_PATH.exists() or not SAVED_MODEL_PATH.exists():
        print("Required dataset or model missing.")
        sys.exit(1)

    raw_df = pd.read_csv(DEFAULT_DATASET_PATH)
    features_df = extract_features(raw_df)
    rule_scores, rule_reasons, _ = evaluate_rules(raw_df, features_df)

    detector = IsolationForestDetector.load(SAVED_MODEL_PATH)
    ml_scores = detector.predict_score(features_df)
    scored_df = compile_scored_ledger(raw_df, rule_scores, ml_scores, rule_reasons)

    # Filter to flagged entries only (High + Medium)
    flagged_df = scored_df[scored_df["is_flagged"]].copy()
    flagged_feat_df = features_df.loc[flagged_df.index].copy()

    print(f"Total Flagged Entries to Explain: {len(flagged_df):,}")

    explainer = AuditExplainer(detector)
    # Test explain on first 5 flagged entries
    sample_explanations = explainer.explain_flagged_entries(flagged_df.head(5), flagged_feat_df.head(5))

    print("\nSample Explanations Generated:")
    for exp in sample_explanations:
        print(f"\n--- Entry {exp['entry_id']} ---")
        print(f"Unified Narrative: {exp['unified_narrative']}")
        print("Top 3 ML Drivers:")
        for driver in exp["top_drivers"]:
            print(f"  * {driver['feature']} (+{driver['attribution']:.4f}): {driver['reason']}")

    print("\nStage 6 Explainability Engine successfully verified!")
