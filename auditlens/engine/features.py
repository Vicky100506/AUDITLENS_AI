"""Feature Engineering Pipeline for AuditLens AI.

Extracts auditor-focused risk features from general ledger entries, including:
- Temporal features: day_of_week, is_weekend, is_holiday, hour_posted
- Financial magnitude features: log_amount, is_round_amount, amount_to_limit_ratio
- Segregation & governance: same_poster_approver, description_length
- Distributional & anomaly indicators: account_amount_zscore, user_posting_freq,
  vendor_posting_freq, duplicate_count.

Labels (is_injected_anomaly, anomaly_type) are strictly ignored to prevent data leakage.
"""

from typing import List, Optional

import numpy as np
import pandas as pd

from auditlens.config import (
    APPROVAL_LIMIT,
    INDIAN_HOLIDAYS_2024,
    MIN_ROUND_AMOUNT,
    MODEL_FEATURE_COLUMNS,
    ROUND_AMOUNT_BASE,
)


def extract_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    """Extract day of week, weekend indicator, holiday indicator, and posting hour."""
    out = pd.DataFrame(index=df.index)

    # Parse posting_date to datetime
    dates = pd.to_datetime(df["posting_date"], errors="coerce")
    
    # day_of_week: Monday=0, Sunday=6
    out["day_of_week"] = dates.dt.dayofweek.fillna(0).astype(int)
    
    # is_weekend: Saturday (5) or Sunday (6)
    out["is_weekend"] = (out["day_of_week"] >= 5).astype(int)
    
    # is_holiday: Check if posting_date is in Indian public holiday list
    date_strs = dates.dt.strftime("%Y-%m-%d")
    out["is_holiday"] = date_strs.isin(INDIAN_HOLIDAYS_2024).astype(int)
    
    # hour_posted: Parse time strings (e.g. HH:MM:SS or HH:MM)
    def parse_hour(time_val: any) -> int:
        if pd.isna(time_val):
            return 12  # fallback noon
        time_str = str(time_val).strip()
        parts = time_str.split(":")
        try:
            return int(parts[0])
        except (ValueError, IndexError):
            return 12

    out["hour_posted"] = df["posting_time"].apply(parse_hour).astype(int)
    return out


def extract_amount_features(df: pd.DataFrame) -> pd.DataFrame:
    """Extract log amount, round amount flag, and approval limit ratio."""
    out = pd.DataFrame(index=df.index)
    amounts = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    # Clip negative amounts for log calculation if any
    safe_amounts = np.maximum(0.0, amounts.values)
    
    out["log_amount"] = np.log1p(safe_amounts)
    
    # is_round_amount: Multiple of ₹10,000 and at least ₹10,000
    # Use modulo with floating tolerance
    rem = np.remainder(safe_amounts, ROUND_AMOUNT_BASE)
    is_round = (safe_amounts >= MIN_ROUND_AMOUNT) & (
        (rem < 0.01) | (rem > (ROUND_AMOUNT_BASE - 0.01))
    )
    out["is_round_amount"] = is_round.astype(int)
    
    # amount_to_limit_ratio: relative to fixed approval limit
    out["amount_to_limit_ratio"] = safe_amounts / APPROVAL_LIMIT
    return out


def extract_governance_features(df: pd.DataFrame) -> pd.DataFrame:
    """Extract segregation of duties (same poster/approver) and description length."""
    out = pd.DataFrame(index=df.index)
    
    # same_poster_approver
    poster = df["posted_by"].astype(str).str.strip().str.lower()
    approver = df["approved_by"].astype(str).str.strip().str.lower()
    out["same_poster_approver"] = (poster == approver).astype(int)
    
    # description_length
    out["description_length"] = df["description"].fillna("").astype(str).str.len()
    return out


def extract_contextual_aggregations(df: pd.DataFrame) -> pd.DataFrame:
    """Extract account-level amount z-scores, user posting frequency, vendor frequency,

    and duplicate transaction count based on (account_code, vendor, amount, posting_date).
    """
    out = pd.DataFrame(index=df.index)
    amounts = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)

    # 1. Account-level amount z-score: (amount - mean_acc) / std_acc
    # Group by account_code and transform
    temp_df = pd.DataFrame({
        "account_code": df["account_code"].astype(str),
        "amount": amounts,
    })
    
    account_stats = temp_df.groupby("account_code")["amount"].agg(["mean", "std"])
    account_stats["std"] = account_stats["std"].replace(0.0, np.nan).fillna(1.0)
    
    merged = temp_df.merge(account_stats, on="account_code", how="left")
    z_scores = (merged["amount"] - merged["mean"]) / merged["std"]
    out["account_amount_zscore"] = z_scores.fillna(0.0).values

    # 2. User posting frequency (count of entries posted by each user)
    user_counts = df["posted_by"].value_counts()
    out["user_posting_freq"] = df["posted_by"].map(user_counts).fillna(1).astype(int)

    # 3. Vendor posting frequency (count of entries associated with each vendor)
    vendor_counts = df["vendor"].value_counts()
    out["vendor_posting_freq"] = df["vendor"].map(vendor_counts).fillna(1).astype(int)

    # 4. Duplicate count based on (account_code, vendor, amount, posting_date)
    dup_keys = ["account_code", "vendor", "amount", "posting_date"]
    # Count total occurrences of this tuple in the ledger
    dup_counts = df.groupby(dup_keys)["posting_date"].transform("count")
    out["duplicate_count"] = dup_counts.fillna(1).astype(int)

    return out


def extract_features(df: pd.DataFrame) -> pd.DataFrame:
    """Run full feature engineering pipeline and return DataFrame with MODEL_FEATURE_COLUMNS.

    Parameters:
        df: Raw ledger DataFrame containing standard journal entry columns.

    Returns:
        DataFrame containing only engineered numeric features ready for rule scoring
        and machine learning models. Does NOT include labels or non-feature columns.
    """
    temporal_df = extract_temporal_features(df)
    amount_df = extract_amount_features(df)
    governance_df = extract_governance_features(df)
    context_df = extract_contextual_aggregations(df)

    # Combine all feature subsets
    features_df = pd.concat([temporal_df, amount_df, governance_df, context_df], axis=1)

    # Validate all required model columns are present and properly ordered
    missing_cols = [col for col in MODEL_FEATURE_COLUMNS if col not in features_df.columns]
    if missing_cols:
        raise ValueError(f"Feature engineering pipeline failed to generate required columns: {missing_cols}")

    return features_df[MODEL_FEATURE_COLUMNS]


if __name__ == "__main__":
    from auditlens.config import DEFAULT_DATASET_PATH
    import sys

    print("Testing Feature Engineering Pipeline on synthetic dataset...")
    if not DEFAULT_DATASET_PATH.exists():
        print(f"Error: {DEFAULT_DATASET_PATH} not found. Please run Stage 1 first.")
        sys.exit(1)

    raw_df = pd.read_csv(DEFAULT_DATASET_PATH)
    features = extract_features(raw_df)

    print("\nFeature Matrix Summary:")
    print(f"Total Rows:     {len(features):,}")
    print(f"Total Features: {features.shape[1]}")
    print(f"Feature Names:  {list(features.columns)}")
    print("\nMissing Values Check:")
    print(features.isnull().sum())
    print("\nFeature Statistics:")
    print(features.describe().T[["mean", "std", "min", "max"]])
    print("\nStage 2 Feature Engineering successfully verified!")
