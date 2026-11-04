"""Audit Rules Engine for AuditLens AI.

Implements standalone, auditor-grade heuristic tests:
1. Weekend or holiday posting
2. Round transaction amount (multiples of ₹10,000)
3. Duplicate transaction entries
4. Just-below-approval-limit structuring (₹95,000 - ₹99,900)
5. Same poster and approver (Segregation of Duties breach)
6. Missing or vague journal description

Each rule is implemented as an independent function returning (is_violated: bool, reason: str).
Scores are combined into a normalized rule_score in [0, 1] using weights defined in config.py.
"""

from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

from auditlens.config import (
    APPROVAL_LIMIT,
    BELOW_LIMIT_MAX_RATIO,
    BELOW_LIMIT_MIN_RATIO,
    INDIAN_HOLIDAYS_2024,
    MIN_ROUND_AMOUNT,
    ROUND_AMOUNT_BASE,
    RULE_WEIGHTS,
    VAGUE_DESCRIPTIONS,
)


def check_weekend_or_holiday(row: Union[pd.Series, Dict[str, Any]]) -> Tuple[bool, str]:
    """Check if the journal entry was posted on a weekend or an Indian public holiday.

    Returns:
        (is_violated, reason_string)
    """
    date_val = row.get("posting_date")
    if pd.isna(date_val) or not date_val:
        return False, ""

    date_str = str(date_val).strip()
    try:
        dt = pd.to_datetime(date_str)
    except Exception:
        return False, ""

    # Check weekend (Saturday = 5, Sunday = 6)
    if dt.dayofweek == 5:
        return True, "Posted on a weekend (Saturday)"
    if dt.dayofweek == 6:
        return True, "Posted on a weekend (Sunday)"

    # Check Indian national / gazetted holiday
    formatted_date = dt.strftime("%Y-%m-%d")
    if formatted_date in INDIAN_HOLIDAYS_2024:
        return True, f"Posted on a gazetted Indian public holiday ({formatted_date})"

    return False, ""


def check_round_amount(row: Union[pd.Series, Dict[str, Any]]) -> Tuple[bool, str]:
    """Check if the transaction amount is a clean round multiple of ₹10,000.

    Auditors examine round amounts because fraudulent lump sums and unbacked
    manual estimates disproportionately end with round numbers.
    """
    amt_val = row.get("amount")
    if pd.isna(amt_val):
        return False, ""

    try:
        amt = float(amt_val)
    except (ValueError, TypeError):
        return False, ""

    if amt < MIN_ROUND_AMOUNT:
        return False, ""

    rem = amt % ROUND_AMOUNT_BASE
    # Account for floating point epsilon
    if rem < 0.01 or rem > (ROUND_AMOUNT_BASE - 0.01):
        return True, f"Round transaction amount of INR {amt:,.2f} (multiple of INR 10,000)"

    return False, ""


def check_duplicate_entry(
    row: Union[pd.Series, Dict[str, Any]],
    duplicate_count: Optional[int] = None,
) -> Tuple[bool, str]:
    """Check if transaction appears more than once with identical vendor, account, amount, and date.

    If duplicate_count is provided (from feature engineering), uses that;
    otherwise looks for 'duplicate_count' in row.
    """
    count = duplicate_count if duplicate_count is not None else row.get("duplicate_count", 1)
    try:
        if int(count) > 1:
            return True, f"Duplicate transaction detected ({int(count)} entries share matching date, vendor, account, and amount)"
    except (ValueError, TypeError):
        pass

    return False, ""


def check_below_approval_limit(row: Union[pd.Series, Dict[str, Any]]) -> Tuple[bool, str]:
    """Check if the amount is between 95% and 99.9% of the ₹100,000 approval limit.

    This test identifies structuring or threshold avoidance behavior where users
    deliberately keep transactions below mandatory managerial sign-off limits.
    """
    amt_val = row.get("amount")
    if pd.isna(amt_val):
        return False, ""

    try:
        amt = float(amt_val)
    except (ValueError, TypeError):
        return False, ""

    lower_bound = APPROVAL_LIMIT * BELOW_LIMIT_MIN_RATIO  # ₹95,000
    upper_bound = APPROVAL_LIMIT * BELOW_LIMIT_MAX_RATIO  # ₹99,900

    if lower_bound <= amt <= upper_bound:
        return True, (
            f"Amount INR {amt:,.2f} is just below the INR {APPROVAL_LIMIT:,.0f} "
            f"approval limit (potential authorization evasion)"
        )

    return False, ""


def check_same_poster_approver(row: Union[pd.Series, Dict[str, Any]]) -> Tuple[bool, str]:
    """Check if the same user both posted and approved the transaction.

    Represents a direct Segregation of Duties (SoD) internal control breach.
    """
    poster = str(row.get("posted_by", "")).strip().lower()
    approver = str(row.get("approved_by", "")).strip().lower()

    if poster and approver and (poster == approver):
        return True, f"Segregation of duties breach: Entry posted and approved by the same user ('{poster}')"

    return False, ""


def check_vague_description(row: Union[pd.Series, Dict[str, Any]]) -> Tuple[bool, str]:
    """Check if the journal entry description is missing, empty, or too vague to ascertain business purpose."""
    desc_val = row.get("description")
    if pd.isna(desc_val) or desc_val is None:
        return True, "Missing journal description (blank or null)"

    desc = str(desc_val).strip()
    if len(desc) <= 2:
        return True, f"Vague or insufficient description ('{desc}')"

    desc_lower = desc.lower()
    if desc_lower in [vd.lower() for vd in VAGUE_DESCRIPTIONS]:
        return True, f"Generic/vague description ('{desc}') lacking necessary audit context"

    return False, ""


def evaluate_rules(
    df: pd.DataFrame,
    features_df: Optional[pd.DataFrame] = None,
) -> Tuple[pd.Series, List[List[str]], pd.DataFrame]:
    """Evaluate all 6 audit rules on each row of the input general ledger DataFrame.

    Parameters:
        df: Raw ledger DataFrame containing entry fields.
        features_df: Optional precomputed features DataFrame (e.g. providing duplicate_count).

    Returns:
        tuple containing:
        - rule_scores: pd.Series of floats in [0, 1] representing the weighted rule violation score.
        - rule_reasons: List of List[str], where each sublist contains triggered reason strings for that row.
        - rule_flags_df: pd.DataFrame of boolean flags for each rule test.
    """
    n = len(df)
    rule_keys = [
        "weekend_or_holiday",
        "round_amount",
        "duplicate_entry",
        "below_approval_limit",
        "same_poster_approver",
        "vague_description",
    ]

    # Pre-extract duplicate counts if available in features_df or compute on the fly
    if features_df is not None and "duplicate_count" in features_df.columns:
        duplicate_counts = features_df["duplicate_count"].values
    elif "duplicate_count" in df.columns:
        duplicate_counts = df["duplicate_count"].values
    else:
        dup_keys = ["account_code", "vendor", "amount", "posting_date"]
        duplicate_counts = df.groupby(dup_keys)["posting_date"].transform("count").values

    # Vectorized / fast row checks
    flags: Dict[str, np.ndarray] = {k: np.zeros(n, dtype=bool) for k in rule_keys}
    reasons: List[List[str]] = [[] for _ in range(n)]

    # Iterate rows to collect reasons and flags
    # Using itertuples for high-performance iteration
    records = df.to_dict(orient="records")

    for i, row in enumerate(records):
        dup_cnt = duplicate_counts[i]

        # 1. Weekend or holiday
        viol, reason = check_weekend_or_holiday(row)
        if viol:
            flags["weekend_or_holiday"][i] = True
            reasons[i].append(reason)

        # 2. Round amount
        viol, reason = check_round_amount(row)
        if viol:
            flags["round_amount"][i] = True
            reasons[i].append(reason)

        # 3. Duplicate entry
        viol, reason = check_duplicate_entry(row, duplicate_count=dup_cnt)
        if viol:
            flags["duplicate_entry"][i] = True
            reasons[i].append(reason)

        # 4. Below approval limit
        viol, reason = check_below_approval_limit(row)
        if viol:
            flags["below_approval_limit"][i] = True
            reasons[i].append(reason)

        # 5. Same poster & approver
        viol, reason = check_same_poster_approver(row)
        if viol:
            flags["same_poster_approver"][i] = True
            reasons[i].append(reason)

        # 6. Vague description
        viol, reason = check_vague_description(row)
        if viol:
            flags["vague_description"][i] = True
            reasons[i].append(reason)

    # Compute rule score: each triggered rule contributes its severity weight, capped at 1.0
    rule_scores_arr = np.zeros(n, dtype=float)
    for rule_name, weight in RULE_WEIGHTS.items():
        if rule_name in flags:
            rule_scores_arr += flags[rule_name].astype(float) * weight

    # Clip to [0.0, 1.0]
    rule_scores_arr = np.clip(rule_scores_arr, 0.0, 1.0)
    rule_scores = pd.Series(rule_scores_arr, index=df.index, name="rule_score")
    rule_flags_df = pd.DataFrame(flags, index=df.index)

    return rule_scores, reasons, rule_flags_df


if __name__ == "__main__":
    from auditlens.config import DEFAULT_DATASET_PATH
    import sys

    print("Testing Rule Engine on synthetic dataset...")
    if not DEFAULT_DATASET_PATH.exists():
        print(f"Error: {DEFAULT_DATASET_PATH} not found.")
        sys.exit(1)

    raw_df = pd.read_csv(DEFAULT_DATASET_PATH)
    scores, reasons, flags_df = evaluate_rules(raw_df)

    print("\nRule Engine Evaluation Results:")
    print(f"Total Rows Evaluated: {len(scores):,}")
    print(f"Entries with at least 1 Rule Triggered: {(scores > 0).sum():,} ({(scores > 0).mean() * 100:.2f}%)")
    print(f"Mean Rule Score: {scores.mean():.4f}")
    print(f"Max Rule Score:  {scores.max():.4f}")
    print("\nTriggers Per Rule:")
    for col in flags_df.columns:
        cnt = flags_df[col].sum()
        pct = (cnt / len(raw_df)) * 100
        print(f"  {col:<25} : {cnt:>6,} ({pct:.2f}%)")

    # Sample flagged entries
    flagged_indices = np.where(scores > 0)[0][:3]
    print("\nSample Flagged Entries Reasons:")
    for idx in flagged_indices:
        print(f"  {raw_df.iloc[idx]['entry_id']} (Score: {scores.iloc[idx]:.2f}): {reasons[idx]}")

    print("\nStage 3 Rules Engine successfully verified!")
