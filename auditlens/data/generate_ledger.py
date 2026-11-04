"""Synthetic General Ledger Generator for AuditLens AI.

Generates a realistic 50,000 journal entry general ledger in an Indian corporate
setting with INR transaction amounts, ~25 accounts, ~200 vendors, ~20 users,
and a fixed approval limit of ₹100,000. Injects ~2% known forensic audit anomalies
across 7 predefined risk patterns for ground-truth model evaluation.
"""

import datetime
import random
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from faker import Faker

from auditlens.config import (
    ANOMALY_RATE,
    APPROVAL_LIMIT,
    BELOW_LIMIT_MAX_RATIO,
    BELOW_LIMIT_MIN_RATIO,
    BUSINESS_HOUR_END,
    BUSINESS_HOUR_START,
    CHART_OF_ACCOUNTS,
    DEFAULT_DATASET_PATH,
    END_DATE,
    INDIAN_HOLIDAYS_2024,
    MIN_ROUND_AMOUNT,
    RANDOM_SEED,
    ROUND_AMOUNT_BASE,
    START_DATE,
    TOTAL_ENTRIES,
    VAGUE_DESCRIPTIONS,
)

# Known Indian Corporate Entities & Vendors
CORE_INDIAN_CORPORATES: List[str] = [
    "Tata Consultancy Services Ltd",
    "Infosys BPM Services India",
    "Wipro Enterprises Pvt Ltd",
    "Reliance Retail Ventures",
    "Bharti Airtel Enterprise Services",
    "Larsen & Toubro Infotech",
    "HCL Technologies India",
    "Tech Mahindra Global Solutions",
    "Asian Paints Industrial Supplies",
    "Bajaj Electricals & Infrastructure",
    "Mahindra Logistics Solutions",
    "Blue Dart Express Cargo",
    "Godrej Consumer & Office Solutions",
    "Titan Corporate Services",
    "Adani Total Logistics",
    "UltraTech Cement & Building Solutions",
    "Tata Communications Cloud Infra",
    "ITC Paperboards & Packaging",
    "Sun Pharma Healthcare Distribution",
    "Cipla Institutional Supplies",
]

# Business-relevant description templates per account category
DESCRIPTION_TEMPLATES: Dict[str, List[str]] = {
    "Asset": [
        "Quarterly workstation hardware procurement for Bangalore IT center",
        "Advance deposit for enterprise server lease agreement",
        "Vendor invoice settlement for networking equipment supply",
        "Disbursement for regional warehouse storage fixtures",
        "Direct bank transfer for capital equipment installment",
    ],
    "Liability": [
        "Monthly statutory deduction clearance to central tax treasury",
        "Vendor payment reconciliation against PO-{po_id}",
        "Settlement of quarterly accrued employee performance bonus",
        "Remittance of TDS liabilities under Section 194C/194J",
        "Reconciliation of GST output liability credit adjustments",
    ],
    "Equity": [
        "Approved board dividend distribution allocation",
        "Authorized share capital transfer to general reserves",
        "Quarterly retained earnings adjustments per audit resolution",
    ],
    "Revenue": [
        "Client billing milestone 3 for enterprise ERP migration",
        "Annual Maintenance Contract (AMC) renewal billing for client {vendor}",
        "Consulting retainer fee invoice settlement - Phase 2",
        "Professional services delivery fee realization",
        "Software deployment and customization project bill",
    ],
    "Expense": [
        "Monthly cloud hosting infrastructure charges (AWS & Azure)",
        "Office facility lease and utility maintenance charges",
        "Legal compliance and quarterly statutory audit retainer fee",
        "Domestic business travel, lodging and conveyance claims",
        "Bulk corporate stationery, printing and pantry supplies",
    ],
}


def build_vendor_pool(faker_instance: Faker, n_vendors: int = 200) -> List[str]:
    """Generate a realistic pool of ~200 Indian corporate and trade vendors."""
    vendors = list(CORE_INDIAN_CORPORATES)
    suffixes = ["Pvt Ltd", "Industries", "Logistics", "Enterprises", "Solutions", "Services", "Suppliers"]
    
    while len(vendors) < n_vendors:
        last_name = faker_instance.last_name()
        suffix = random.choice(suffixes)
        vendors.append(f"{last_name} {suffix}")
        
    return vendors[:n_vendors]


def build_user_pool() -> List[str]:
    """Generate 20 distinct Indian enterprise user identifiers."""
    first_names = [
        "aarav", "priya", "ananya", "arjun", "vikram",
        "neha", "suresh", "kavita", "deepak", "sunita",
        "aditya", "pooja", "manish", "divya", "sanjay",
        "swati", "rajesh", "amit", "meera", "harish"
    ]
    last_names = [
        "sharma", "patel", "iyer", "verma", "singh",
        "gupta", "menon", "reddy", "joshi", "nair",
        "kulkarni", "bose", "tiwari", "krishnan", "mehta",
        "deshmukh", "pillai", "kumar", "sen", "rao"
    ]
    return [f"{fn}.{ln}" for fn, ln in zip(first_names, last_names)]


def generate_normal_timestamp(date_obj: datetime.date) -> datetime.time:
    """Generate a normal transaction timestamp concentrated during business hours (09:00 - 18:00)."""
    # Centered around 13:30 (peak transaction time) with std 2.5 hours
    hour_float = np.random.normal(loc=13.5, scale=2.2)
    # Clip to normal operating range 08:30 to 18:30
    hour_float = np.clip(hour_float, 8.5, 18.5)
    hour = int(hour_float)
    minute = int((hour_float - hour) * 60)
    second = random.randint(0, 59)
    return datetime.time(hour=hour, minute=minute, second=second)


def generate_synthetic_ledger(
    seed: int = RANDOM_SEED,
    n_entries: int = TOTAL_ENTRIES,
    anomaly_rate: float = ANOMALY_RATE,
    output_path: Optional[Path] = DEFAULT_DATASET_PATH,
) -> pd.DataFrame:
    """Generate synthetic general ledger entries with realistic Indian enterprise context

    and injected forensic audit anomalies.
    """
    np.random.seed(seed)
    random.seed(seed)
    faker_in = Faker("en_IN")
    Faker.seed(seed)

    vendors = build_vendor_pool(faker_in, n_vendors=200)
    users = build_user_pool()
    account_codes = list(CHART_OF_ACCOUNTS.keys())

    # Build calendar of valid business dates (Monday-Friday excluding Indian public holidays)
    start_dt = datetime.datetime.strptime(START_DATE, "%Y-%m-%d").date()
    end_dt = datetime.datetime.strptime(END_DATE, "%Y-%m-%d").date()
    all_dates = [start_dt + datetime.timedelta(days=i) for i in range((end_dt - start_dt).days + 1)]
    
    weekday_dates = [d for d in all_dates if d.weekday() < 5 and d.strftime("%Y-%m-%d") not in INDIAN_HOLIDAYS_2024]
    weekend_dates = [d for d in all_dates if d.weekday() >= 5]
    holiday_dates = [datetime.datetime.strptime(h, "%Y-%m-%d").date() for h in INDIAN_HOLIDAYS_2024]

    # Calculate count of anomalies
    n_anomalies = int(round(n_entries * anomaly_rate))
    n_normal = n_entries - n_anomalies

    # Determine distribution across the 7 anomaly types
    anomaly_types_list = [
        "weekend_holiday",
        "round_amount",
        "duplicate",
        "below_approval_limit",
        "same_poster_approver",
        "vague_description",
        "unusual_account_amount",
    ]
    base_count = n_anomalies // len(anomaly_types_list)
    anomaly_counts = {atype: base_count for atype in anomaly_types_list}
    # Allocate remainder
    remainder = n_anomalies - sum(anomaly_counts.values())
    for atype in anomaly_types_list[:remainder]:
        anomaly_counts[atype] += 1

    print(f"Generating {n_entries:,} total entries ({n_normal:,} normal + {n_anomalies:,} injected anomalies)...")
    for atype, cnt in anomaly_counts.items():
        print(f"  - {atype}: {cnt} entries")

    rows: List[Dict[str, any]] = []

    # 1. Generate Normal Entries
    for i in range(n_normal):
        # Pick date (strictly weekdays, non-holiday for normal)
        posting_date = random.choice(weekday_dates)
        posting_time = generate_normal_timestamp(posting_date)
        
        # Pick account
        account_code = random.choice(account_codes)
        account_meta = CHART_OF_ACCOUNTS[account_code]
        account_name = account_meta["name"]
        category = account_meta["category"]
        
        # Vendor selection (weighted towards primary suppliers)
        vendor = random.choice(vendors)
        
        # Normal Log-normal amount calibrated per account
        # Expected value E[X] = exp(mu + sigma^2 / 2) -> mu = ln(mean) - sigma^2 / 2
        mean_amt = account_meta["mean_amount"]
        sigma = account_meta["sigma"]
        mu = np.log(mean_amt) - 0.5 * (sigma ** 2)
        raw_amt = np.random.lognormal(mean=mu, sigma=sigma)
        # Round to 2 decimal places, ensure non-zero
        amount = round(float(np.clip(raw_amt, 150.0, 5_000_000.0)), 2)
        
        # Avoid accidental round amount (multiples of 10k) in normal transactions
        if amount >= ROUND_AMOUNT_BASE and (amount % ROUND_AMOUNT_BASE < 1.0 or amount % ROUND_AMOUNT_BASE > 9999.0):
            amount += round(random.uniform(12.50, 487.75), 2)
            
        # Avoid accidental structuring (95k - 99.9k) in normal transactions
        if APPROVAL_LIMIT * BELOW_LIMIT_MIN_RATIO <= amount <= APPROVAL_LIMIT * BELOW_LIMIT_MAX_RATIO:
            amount = round(amount - 8500.0, 2)
            
        # Users: Segregation of duties strictly enforced (poster != approver)
        posted_by = random.choice(users)
        approved_by = random.choice([u for u in users if u != posted_by])
        
        # Description: Clear, audit-ready descriptive text
        template = random.choice(DESCRIPTION_TEMPLATES[category])
        description = template.format(po_id=random.randint(10000, 99999), vendor=vendor)

        rows.append({
            "posting_date": posting_date.strftime("%Y-%m-%d"),
            "posting_time": posting_time.strftime("%H:%M:%S"),
            "account_code": account_code,
            "account_name": account_name,
            "vendor": vendor,
            "amount": amount,
            "posted_by": posted_by,
            "approved_by": approved_by,
            "description": description,
            "is_injected_anomaly": 0,
            "anomaly_type": "none",
        })

    # 2. Generate Injected Anomalies

    # Type A: Weekend or Holiday Postings
    for _ in range(anomaly_counts["weekend_holiday"]):
        # 50% weekend, 50% national holiday
        if random.random() < 0.5 and len(holiday_dates) > 0:
            p_date = random.choice(holiday_dates)
        else:
            p_date = random.choice(weekend_dates)
            
        # Often posted late at night or unusual off-hours
        off_hour = random.choice([21, 22, 23, 0, 1, 2, 3, 4, 5, 6])
        p_time = datetime.time(hour=off_hour, minute=random.randint(0, 59), second=random.randint(0, 59))
        
        account_code = random.choice(account_codes)
        account_meta = CHART_OF_ACCOUNTS[account_code]
        mean_amt = account_meta["mean_amount"]
        mu = np.log(mean_amt) - 0.5 * (account_meta["sigma"] ** 2)
        amount = round(float(np.random.lognormal(mean=mu, sigma=account_meta["sigma"])), 2)
        
        posted_by = random.choice(users)
        approved_by = random.choice([u for u in users if u != posted_by])
        desc = random.choice(DESCRIPTION_TEMPLATES[account_meta["category"]]).format(
            po_id=random.randint(10000, 99999), vendor="Vendor"
        )
        
        rows.append({
            "posting_date": p_date.strftime("%Y-%m-%d"),
            "posting_time": p_time.strftime("%H:%M:%S"),
            "account_code": account_code,
            "account_name": account_meta["name"],
            "vendor": random.choice(vendors),
            "amount": amount,
            "posted_by": posted_by,
            "approved_by": approved_by,
            "description": desc,
            "is_injected_anomaly": 1,
            "anomaly_type": "weekend_holiday",
        })

    # Type B: Round Amounts (multiples of ₹10,000)
    round_multipliers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 15, 20, 25, 30, 40, 50]
    for _ in range(anomaly_counts["round_amount"]):
        p_date = random.choice(weekday_dates)
        p_time = generate_normal_timestamp(p_date)
        account_code = random.choice(account_codes)
        account_meta = CHART_OF_ACCOUNTS[account_code]
        
        multiplier = random.choice(round_multipliers)
        amount = float(multiplier * 10_000)
        
        posted_by = random.choice(users)
        approved_by = random.choice([u for u in users if u != posted_by])
        desc = random.choice(DESCRIPTION_TEMPLATES[account_meta["category"]]).format(
            po_id=random.randint(10000, 99999), vendor="Vendor"
        )
        
        rows.append({
            "posting_date": p_date.strftime("%Y-%m-%d"),
            "posting_time": p_time.strftime("%H:%M:%S"),
            "account_code": account_code,
            "account_name": account_meta["name"],
            "vendor": random.choice(vendors),
            "amount": amount,
            "posted_by": posted_by,
            "approved_by": approved_by,
            "description": desc,
            "is_injected_anomaly": 1,
            "anomaly_type": "round_amount",
        })

    # Type C: Duplicate Entries (matching account, vendor, amount, date)
    for _ in range(anomaly_counts["duplicate"]):
        # Pick an existing normal row to duplicate
        src_row = random.choice(rows[:n_normal])
        # Slight time variation (e.g. 5 minutes later or duplicate system posting)
        src_time = datetime.datetime.strptime(src_row["posting_time"], "%H:%M:%S")
        dup_time = (src_time + datetime.timedelta(minutes=random.randint(2, 30))).time()
        
        rows.append({
            "posting_date": src_row["posting_date"],
            "posting_time": dup_time.strftime("%H:%M:%S"),
            "account_code": src_row["account_code"],
            "account_name": src_row["account_name"],
            "vendor": src_row["vendor"],
            "amount": src_row["amount"],
            "posted_by": src_row["posted_by"],
            "approved_by": src_row["approved_by"],
            "description": src_row["description"],
            "is_injected_anomaly": 1,
            "anomaly_type": "duplicate",
        })

    # Type D: Just-Below-Approval-Limit (95% to 99.9% of ₹100,000 = ₹95,000 to ₹99,900)
    for _ in range(anomaly_counts["below_approval_limit"]):
        p_date = random.choice(weekday_dates)
        p_time = generate_normal_timestamp(p_date)
        account_code = random.choice(account_codes)
        account_meta = CHART_OF_ACCOUNTS[account_code]
        
        # Exact range [95,000.0, 99,900.0]
        amount = round(random.uniform(APPROVAL_LIMIT * BELOW_LIMIT_MIN_RATIO, APPROVAL_LIMIT * BELOW_LIMIT_MAX_RATIO), 2)
        
        posted_by = random.choice(users)
        approved_by = random.choice([u for u in users if u != posted_by])
        desc = random.choice(DESCRIPTION_TEMPLATES[account_meta["category"]]).format(
            po_id=random.randint(10000, 99999), vendor="Vendor"
        )
        
        rows.append({
            "posting_date": p_date.strftime("%Y-%m-%d"),
            "posting_time": p_time.strftime("%H:%M:%S"),
            "account_code": account_code,
            "account_name": account_meta["name"],
            "vendor": random.choice(vendors),
            "amount": amount,
            "posted_by": posted_by,
            "approved_by": approved_by,
            "description": desc,
            "is_injected_anomaly": 1,
            "anomaly_type": "below_approval_limit",
        })

    # Type E: Same User Posting and Approving (Segregation of Duties breach)
    for _ in range(anomaly_counts["same_poster_approver"]):
        p_date = random.choice(weekday_dates)
        p_time = generate_normal_timestamp(p_date)
        account_code = random.choice(account_codes)
        account_meta = CHART_OF_ACCOUNTS[account_code]
        
        mean_amt = account_meta["mean_amount"]
        mu = np.log(mean_amt) - 0.5 * (account_meta["sigma"] ** 2)
        amount = round(float(np.random.lognormal(mean=mu, sigma=account_meta["sigma"])), 2)
        
        same_user = random.choice(users)
        desc = random.choice(DESCRIPTION_TEMPLATES[account_meta["category"]]).format(
            po_id=random.randint(10000, 99999), vendor="Vendor"
        )
        
        rows.append({
            "posting_date": p_date.strftime("%Y-%m-%d"),
            "posting_time": p_time.strftime("%H:%M:%S"),
            "account_code": account_code,
            "account_name": account_meta["name"],
            "vendor": random.choice(vendors),
            "amount": amount,
            "posted_by": same_user,
            "approved_by": same_user,  # Violation!
            "description": desc,
            "is_injected_anomaly": 1,
            "anomaly_type": "same_poster_approver",
        })

    # Type F: Vague or Empty Descriptions
    for _ in range(anomaly_counts["vague_description"]):
        p_date = random.choice(weekday_dates)
        p_time = generate_normal_timestamp(p_date)
        account_code = random.choice(account_codes)
        account_meta = CHART_OF_ACCOUNTS[account_code]
        
        mean_amt = account_meta["mean_amount"]
        mu = np.log(mean_amt) - 0.5 * (account_meta["sigma"] ** 2)
        amount = round(float(np.random.lognormal(mean=mu, sigma=account_meta["sigma"])), 2)
        
        posted_by = random.choice(users)
        approved_by = random.choice([u for u in users if u != posted_by])
        vague_desc = random.choice(VAGUE_DESCRIPTIONS)
        
        rows.append({
            "posting_date": p_date.strftime("%Y-%m-%d"),
            "posting_time": p_time.strftime("%H:%M:%S"),
            "account_code": account_code,
            "account_name": account_meta["name"],
            "vendor": random.choice(vendors),
            "amount": amount,
            "posted_by": posted_by,
            "approved_by": approved_by,
            "description": vague_desc,
            "is_injected_anomaly": 1,
            "anomaly_type": "vague_description",
        })

    # Type G: Unusual Account and Amount Combinations
    # Low-cost accounts getting extreme 10x-50x normal amounts
    low_cost_accounts = ["6050", "6030", "1010"]  # Supplies (mean 8.5k), Travel (mean 22k), Cash (mean 15k)
    for _ in range(anomaly_counts["unusual_account_amount"]):
        p_date = random.choice(weekday_dates)
        p_time = generate_normal_timestamp(p_date)
        account_code = random.choice(low_cost_accounts)
        account_meta = CHART_OF_ACCOUNTS[account_code]
        
        # Inject extreme amount: ₹800,000 to ₹2,500,000 for stationery or petty cash
        amount = round(random.uniform(750_000.0, 2_200_000.0), 2)
        
        posted_by = random.choice(users)
        approved_by = random.choice([u for u in users if u != posted_by])
        desc = "Urgent bulk procurement reconciliation"
        
        rows.append({
            "posting_date": p_date.strftime("%Y-%m-%d"),
            "posting_time": p_time.strftime("%H:%M:%S"),
            "account_code": account_code,
            "account_name": account_meta["name"],
            "vendor": random.choice(vendors),
            "amount": amount,
            "posted_by": posted_by,
            "approved_by": approved_by,
            "description": desc,
            "is_injected_anomaly": 1,
            "anomaly_type": "unusual_account_amount",
        })

    # Convert to DataFrame
    df = pd.DataFrame(rows)
    
    # Shuffle dataset thoroughly to distribute anomalies evenly
    df = df.sample(frac=1.0, random_state=seed).reset_index(drop=True)
    
    # Assign sequential entry_id: JE-00001 to JE-50000
    df.insert(0, "entry_id", [f"JE-{i+1:05d}" for i in range(len(df))])

    # Reorder columns explicitly
    expected_columns = [
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
        "is_injected_anomaly",
        "anomaly_type",
    ]
    df = df[expected_columns]

    # Save to CSV if path provided
    if output_path is not None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)
        print(f"Saved synthetic ledger ({len(df):,} records) to {output_path}")

    return df


def print_dataset_summary(df: pd.DataFrame) -> None:
    """Print an executive statistical audit summary of the generated dataset."""
    print("\n" + "=" * 70)
    print("AUDITLENS AI - SYNTHETIC GENERAL LEDGER DATA SUMMARY")
    print("=" * 70)
    print(f"Total Journal Entries:        {len(df):,}")
    print(f"Date Range:                   {df['posting_date'].min()} to {df['posting_date'].max()}")
    print(f"Unique Accounts:              {df['account_code'].nunique()} accounts")
    print(f"Unique Vendors:               {df['vendor'].nunique()} vendors")
    print(f"Unique Users (Posters):       {df['posted_by'].nunique()} users")
    print(f"Unique Users (Approvers):     {df['approved_by'].nunique()} users")
    print(f"Total Value Transacted (INR): INR {df['amount'].sum():,.2f}")
    print(f"Mean Transaction Amount:      INR {df['amount'].mean():,.2f}")
    print(f"Median Transaction Amount:    INR {df['amount'].median():,.2f}")
    print(f"Min / Max Amount:             INR {df['amount'].min():,.2f} / INR {df['amount'].max():,.2f}")
    print("-" * 70)
    print("ANOMALY INJECTION PROFILE:")
    anomaly_counts = df["anomaly_type"].value_counts()
    for atype, cnt in anomaly_counts.items():
        pct = (cnt / len(df)) * 100
        print(f"  {atype:<25} : {cnt:>6,} entries ({pct:5.2f}%)")
    total_anomalies = df["is_injected_anomaly"].sum()
    print("-" * 70)
    print(f"Total Injected Anomalies:     {total_anomalies:,} ({(total_anomalies / len(df)) * 100:.2f}%)")
    print(f"Clean Baseline Entries:       {len(df) - total_anomalies:,} ({((len(df) - total_anomalies) / len(df)) * 100:.2f}%)")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    generated_df = generate_synthetic_ledger()
    print_dataset_summary(generated_df)
