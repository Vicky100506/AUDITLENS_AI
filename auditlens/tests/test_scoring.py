"""Unit tests for hybrid risk scoring calculation, tier assignment, and compilation."""

import numpy as np
import pandas as pd
import pytest

from auditlens.engine.scoring import (
    assign_risk_levels,
    calculate_risk_scores,
    compile_scored_ledger,
)


def test_calculate_risk_scores():
    rule_scores = pd.Series([0.0, 1.0, 0.5])
    ml_scores = np.array([0.0, 1.0, 0.5])

    # 50/50 weights
    combined = calculate_risk_scores(rule_scores, ml_scores, weight_rules=0.5, weight_ml=0.5)
    assert np.isclose(combined[0], 0.0)
    assert np.isclose(combined[1], 1.0)
    assert np.isclose(combined[2], 0.5)

    # Clipping check: values should never exceed 1.0 or drop below 0.0
    overshoot = calculate_risk_scores(pd.Series([1.5]), np.array([1.5]))
    assert overshoot[0] == 1.0


def test_assign_risk_levels():
    scores = np.array([0.85, 0.55, 0.45, 0.35, 0.20])
    # Thresholds: High >= 0.55, Medium >= 0.35, Low < 0.35
    levels = assign_risk_levels(scores, high_threshold=0.55, medium_threshold=0.35)

    assert levels[0] == "High"
    assert levels[1] == "High"    # Boundary check
    assert levels[2] == "Medium"
    assert levels[3] == "Medium"  # Boundary check
    assert levels[4] == "Low"


def test_compile_scored_ledger_sorting():
    raw_df = pd.DataFrame([
        {"entry_id": "JE-001", "amount": 1000.0},
        {"entry_id": "JE-002", "amount": 5000.0},
        {"entry_id": "JE-003", "amount": 2500.0},
    ])
    rule_scores = pd.Series([0.1, 0.9, 0.5])
    ml_scores = np.array([0.1, 0.8, 0.4])
    reasons = [["R1"], ["R2"], ["R3"]]

    scored = compile_scored_ledger(
        raw_df,
        rule_scores,
        ml_scores,
        reasons,
        high_threshold=0.55,
        medium_threshold=0.35,
        sort_by_risk=True,
    )

    # JE-002 has highest risk (0.5 * 0.9 + 0.5 * 0.8 = 0.85) -> should be first
    assert scored.iloc[0]["entry_id"] == "JE-002"
    assert scored.iloc[0]["risk_level"] == "High"
    assert bool(scored.iloc[0]["is_flagged"]) is True

    # JE-001 has lowest risk (0.1) -> should be last
    assert scored.iloc[-1]["entry_id"] == "JE-001"
    assert scored.iloc[-1]["risk_level"] == "Low"
    assert bool(scored.iloc[-1]["is_flagged"]) is False
