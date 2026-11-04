"""Central configuration module for AuditLens AI.

Defines all constants, thresholds, weights, and parameters to ensure no
hardcoded magic numbers exist across the codebase.
"""

from pathlib import Path
from typing import Dict, List, Set

# Base Directories
BASE_DIR: Path = Path(__file__).resolve().parent
PROJECT_ROOT: Path = BASE_DIR.parent
DATA_DIR: Path = BASE_DIR / "data"
MODELS_DIR: Path = BASE_DIR / "models"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# Data File Paths
DEFAULT_DATASET_PATH: Path = DATA_DIR / "synthetic_ledger_50k.csv"
SAVED_MODEL_PATH: Path = MODELS_DIR / "isolation_forest.joblib"
SAVED_SCALER_PATH: Path = MODELS_DIR / "feature_scaler.joblib"

# Stage 1: Synthetic Data Generation Parameters
RANDOM_SEED: int = 42
TOTAL_ENTRIES: int = 50_000
ANOMALY_RATE: float = 0.02  # Exactly ~2% known anomalies (approx 1,000 entries)
APPROVAL_LIMIT: float = 100_000.0  # ₹100,000 INR

# Date and Time Configuration (Financial Year / Calendar Year 2024)
START_DATE: str = "2024-01-01"
END_DATE: str = "2024-12-31"
BUSINESS_HOUR_START: int = 9   # 09:00 AM
BUSINESS_HOUR_END: int = 18    # 06:00 PM

# Indian National & Gazetted Public Holidays for 2024 (YYYY-MM-DD)
INDIAN_HOLIDAYS_2024: Set[str] = {
    "2024-01-26",  # Republic Day
    "2024-03-08",  # Maha Shivratri
    "2024-03-25",  # Holi
    "2024-03-29",  # Good Friday
    "2024-04-11",  # Eid-ul-Fitr
    "2024-04-17",  # Ram Navami
    "2024-04-21",  # Mahavir Jayanti
    "2024-05-23",  # Buddha Purnima
    "2024-06-17",  # Bakrid / Eid al-Adha
    "2024-07-17",  # Muharram
    "2024-08-15",  # Independence Day
    "2024-08-26",  # Janmashtami
    "2024-09-16",  # Milad-un-Nabi
    "2024-10-02",  # Mahatma Gandhi Jayanti
    "2024-10-12",  # Dussehra
    "2024-10-31",  # Diwali / Deepavali
    "2024-11-15",  # Guru Nanak Jayanti
    "2024-12-25",  # Christmas
}

# Anomaly Thresholds
BELOW_LIMIT_MIN_RATIO: float = 0.95   # 95% of approval limit (₹95,000)
BELOW_LIMIT_MAX_RATIO: float = 0.999  # 99.9% of approval limit (₹99,900)
ROUND_AMOUNT_BASE: float = 10_000.0   # Multiples of ₹10,000
MIN_ROUND_AMOUNT: float = 10_000.0    # Minimum amount to be considered a round anomaly

# Vague Description Patterns
VAGUE_DESCRIPTIONS: List[str] = [
    "",
    " ",
    ".",
    "-",
    "misc",
    "miscellaneous",
    "adj",
    "adjustment",
    "fee",
    "payment",
    "etc",
    "test",
    "testing",
    "n/a",
    "temp",
    "entry",
    "charges",
    "fund transfer",
    "reversal",
    "office exp",
]

# Chart of Accounts (25 Indian Corporate Ledger Accounts)
CHART_OF_ACCOUNTS: Dict[str, Dict[str, any]] = {
    "1010": {"name": "Cash & Cash Equivalents", "category": "Asset", "mean_amount": 15_000.0, "sigma": 0.8},
    "1020": {"name": "HDFC Operating Bank Account", "category": "Asset", "mean_amount": 120_000.0, "sigma": 1.1},
    "1030": {"name": "ICICI Current Account", "category": "Asset", "mean_amount": 95_000.0, "sigma": 1.0},
    "1040": {"name": "SBI Statutory Tax Deposit Account", "category": "Asset", "mean_amount": 80_000.0, "sigma": 0.9},
    "1110": {"name": "Trade Accounts Receivable", "category": "Asset", "mean_amount": 180_000.0, "sigma": 1.2},
    "1210": {"name": "Finished Goods Inventory", "category": "Asset", "mean_amount": 110_000.0, "sigma": 0.9},
    "1220": {"name": "Raw Materials Inventory", "category": "Asset", "mean_amount": 150_000.0, "sigma": 1.0},
    "1510": {"name": "Office Equipment & Furniture", "category": "Asset", "mean_amount": 45_000.0, "sigma": 0.7},
    "1520": {"name": "IT Hardware & Servers", "category": "Asset", "mean_amount": 85_000.0, "sigma": 0.8},
    "2010": {"name": "Trade Accounts Payable", "category": "Liability", "mean_amount": 140_000.0, "sigma": 1.1},
    "2020": {"name": "TDS Payable (Sec 194C/J)", "category": "Liability", "mean_amount": 25_000.0, "sigma": 0.6},
    "2030": {"name": "GST Input/Output Clearing", "category": "Liability", "mean_amount": 65_000.0, "sigma": 0.8},
    "2040": {"name": "Accrued Employee Salaries & Bonus", "category": "Liability", "mean_amount": 250_000.0, "sigma": 0.7},
    "2050": {"name": "Provident Fund (PF) & ESI Payable", "category": "Liability", "mean_amount": 40_000.0, "sigma": 0.5},
    "3010": {"name": "Share Capital", "category": "Equity", "mean_amount": 500_000.0, "sigma": 0.4},
    "3020": {"name": "Retained Earnings", "category": "Equity", "mean_amount": 300_000.0, "sigma": 0.5},
    "4010": {"name": "Enterprise Software Solutions Revenue", "category": "Revenue", "mean_amount": 220_000.0, "sigma": 1.2},
    "4020": {"name": "Annual Maintenance Contract (AMC) Revenue", "category": "Revenue", "mean_amount": 75_000.0, "sigma": 0.8},
    "4030": {"name": "Consulting & Professional Services Revenue", "category": "Revenue", "mean_amount": 130_000.0, "sigma": 1.0},
    "5010": {"name": "Cost of Subcontracting Services", "category": "Expense", "mean_amount": 90_000.0, "sigma": 0.9},
    "6010": {"name": "Office Rent & Facilities Expense", "category": "Expense", "mean_amount": 115_000.0, "sigma": 0.3},
    "6020": {"name": "IT Cloud Hosting (AWS & Azure)", "category": "Expense", "mean_amount": 85_000.0, "sigma": 0.7},
    "6030": {"name": "Corporate Travel & Conveyance", "category": "Expense", "mean_amount": 22_000.0, "sigma": 0.8},
    "6040": {"name": "Legal, Compliance & Auditor Retainers", "category": "Expense", "mean_amount": 60_000.0, "sigma": 0.6},
    "6050": {"name": "Printing, Stationery & General Office Supplies", "category": "Expense", "mean_amount": 8_500.0, "sigma": 0.6},
}

# Stage 2 & 4: Features Used in Isolation Forest
MODEL_FEATURE_COLUMNS: List[str] = [
    "day_of_week",
    "is_weekend",
    "is_holiday",
    "hour_posted",
    "log_amount",
    "is_round_amount",
    "amount_to_limit_ratio",
    "same_poster_approver",
    "description_length",
    "account_amount_zscore",
    "user_posting_freq",
    "vendor_posting_freq",
    "duplicate_count",
]

# Stage 3: Audit Rule Severity Weights
# Individual rule weights reflect standard internal audit severity
RULE_WEIGHTS: Dict[str, float] = {
    "duplicate_entry": 0.85,       # Critical control failure
    "same_poster_approver": 0.85,  # Segregation of duties (SoD) breach
    "below_approval_limit": 0.80,  # Structuring / authorization evasion
    "weekend_or_holiday": 0.70,    # Off-period posting risk
    "round_amount": 0.65,          # Lump-sum manual estimation risk
    "vague_description": 0.50,     # Inadequate audit documentation
}

# Stage 4: Isolation Forest Hyperparameters
IFOREST_CONTAMINATION: float = 0.025
IFOREST_N_ESTIMATORS: int = 150
IFOREST_RANDOM_STATE: int = 42

# Stage 5: Hybrid Risk Score Weights & Classification Thresholds
WEIGHT_RULES: float = 0.50
WEIGHT_ML: float = 0.50

HIGH_RISK_THRESHOLD: float = 0.55
MEDIUM_RISK_THRESHOLD: float = 0.35
# Low Risk is anything < MEDIUM_RISK_THRESHOLD (0.35)
