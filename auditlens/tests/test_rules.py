"""Unit tests for individual audit heuristic rules and rule evaluation engine."""

import pandas as pd
import pytest

from auditlens.engine.rules import (
    check_below_approval_limit,
    check_duplicate_entry,
    check_round_amount,
    check_same_poster_approver,
    check_vague_description,
    check_weekend_or_holiday,
    evaluate_rules,
)


def test_check_weekend_or_holiday():
    # Saturday (2024-01-27)
    viol, reason = check_weekend_or_holiday({"posting_date": "2024-01-27"})
    assert viol is True
    assert "Saturday" in reason

    # Sunday (2024-01-28)
    viol, reason = check_weekend_or_holiday({"posting_date": "2024-01-28"})
    assert viol is True
    assert "Sunday" in reason

    # Indian Public Holiday: Republic Day (2024-01-26, Friday)
    viol, reason = check_weekend_or_holiday({"posting_date": "2024-01-26"})
    assert viol is True
    assert "gazetted Indian public holiday" in reason

    # Normal business day: Thursday (2024-01-25)
    viol, reason = check_weekend_or_holiday({"posting_date": "2024-01-25"})
    assert viol is False
    assert reason == ""


def test_check_round_amount():
    # Round ₹50,000 (multiple of ₹10,000 and >= ₹10,000)
    viol, reason = check_round_amount({"amount": 50000.0})
    assert viol is True
    assert "multiple of INR 10,000" in reason

    # Non-round ₹48,720.50
    viol, reason = check_round_amount({"amount": 48720.50})
    assert viol is False
    assert reason == ""

    # Small round ₹5,000 (below MIN_ROUND_AMOUNT of 10,000)
    viol, reason = check_round_amount({"amount": 5000.0})
    assert viol is False


def test_check_duplicate_entry():
    # Explicit duplicate count > 1
    viol, reason = check_duplicate_entry({}, duplicate_count=2)
    assert viol is True
    assert "Duplicate transaction detected" in reason

    # Unique entry
    viol, reason = check_duplicate_entry({}, duplicate_count=1)
    assert viol is False
    assert reason == ""


def test_check_below_approval_limit():
    # ₹98,500.00 (within 95% - 99.9% of ₹100,000 approval limit)
    viol, reason = check_below_approval_limit({"amount": 98500.00})
    assert viol is True
    assert "just below the INR 100,000" in reason

    # ₹94,000.00 (below 95% threshold)
    viol, reason = check_below_approval_limit({"amount": 94000.00})
    assert viol is False

    # ₹105,000.00 (above approval limit, standard authorization required, not evasion)
    viol, reason = check_below_approval_limit({"amount": 105000.00})
    assert viol is False


def test_check_same_poster_approver():
    # SoD breach
    viol, reason = check_same_poster_approver({"posted_by": "rohit.sharma", "approved_by": "rohit.sharma"})
    assert viol is True
    assert "Segregation of duties breach" in reason

    # Valid segregation
    viol, reason = check_same_poster_approver({"posted_by": "rohit.sharma", "approved_by": "priya.nair"})
    assert viol is False
    assert reason == ""


def test_check_vague_description():
    # Missing / empty
    assert check_vague_description({"description": ""})[0] is True
    assert check_vague_description({"description": None})[0] is True
    assert check_vague_description({"description": " . "})[0] is True

    # Generic keywords
    assert check_vague_description({"description": "misc"})[0] is True
    assert check_vague_description({"description": "adjustment"})[0] is True
    assert check_vague_description({"description": "test"})[0] is True

    # Descriptive business purpose
    viol, reason = check_vague_description({"description": "Monthly software license subscription for cloud ERP"})
    assert viol is False
    assert reason == ""


def test_evaluate_rules_dataframe():
    sample_df = pd.DataFrame([
        {
            "entry_id": "JE-001",
            "posting_date": "2024-01-27",  # Weekend (Sat)
            "amount": 98500.0,             # Below approval limit
            "posted_by": "user.a",
            "approved_by": "user.a",       # SoD breach
            "description": "misc",         # Vague
            "duplicate_count": 1,
        },
        {
            "entry_id": "JE-002",
            "posting_date": "2024-01-25",  # Normal weekday
            "amount": 25420.75,            # Normal amount
            "posted_by": "user.a",
            "approved_by": "user.b",       # Segregated
            "description": "Standard vendor payment for raw materials",
            "duplicate_count": 1,
        },
    ])

    scores, reasons, flags = evaluate_rules(sample_df)
    assert len(scores) == 2
    # JE-001 triggers 4 rules, score should be capped at 1.0
    assert scores[0] == 1.0
    assert len(reasons[0]) >= 4

    # JE-002 is completely clean
    assert scores[1] == 0.0
    assert len(reasons[1]) == 0
