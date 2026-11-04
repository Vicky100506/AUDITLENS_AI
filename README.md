# AuditLens AI: Explainable Journal Entry Anomaly Detector for Audit

**AuditLens AI** is an explainable machine learning and rule-based forensic anomaly detection platform designed for internal and external financial auditors. It ingests general ledger transactions, detects high-risk journal entries by fusing auditor heuristic tests with an unsupervised **Isolation Forest** model, provides feature-level explanations via **SHAP TreeExplainer**, and presents actionable insights in an interactive React dashboard.

---

## Architecture Overview

```text
+-----------------------------------------------------------------------------+
|                               AUDITLENS AI ARCHITECTURE                     |
+-----------------------------------------------------------------------------+
                                      |
                     [ General Ledger CSV: 50,000 Rows ]
                                      |
                                      v
       +---------------------------------------------------------------+
       |                     FEATURE ENGINEERING                       |
       |  - Temporal (day, weekend, Indian holiday, posting hour)      |
       |  - Magnitude (log_amount, round_amount, limit_ratio)          |
       |  - Governance (same_poster_approver, description_length)      |
       |  - Contextual (account z-score, user/vendor freq, dup_count)  |
       +---------------------------------------------------------------+
                         /                           \
                        /                             \
                       v                               v
       +-------------------------------+   +---------------------------+
       |       AUDIT RULE ENGINE       |   |      ISOLATION FOREST     |
       |  6 Deterministic Tests:       |   |  Unsupervised ML scoring  |
       |  - Weekend/Holiday Postings   |   |  Trained on numeric       |
       |  - Round Figures (₹10,000)    |   |  standardized features    |
       |  - Exact Duplicate Entries    |   |  Detects multi-variate    |
       |  - Below Approval Limit (95%) |   |  anomalous patterns       |
       |  - Segregation of Duties (SoD)|   +---------------------------+
       |  - Vague Descriptions         |                 |
       +-------------------------------+                 |
                        \                               /
                         \                             /
                          v                           v
       +---------------------------------------------------------------+
       |                      HYBRID RISK SCORING                      |
       |     risk_score = 0.50 * rule_score + 0.50 * ml_score          |
       |                                                               |
       |  - High Risk:   score >= 0.55 (Critical immediate review)     |
       |  - Medium Risk: 0.35 <= score < 0.55 (Audit sample testing)   |
       |  - Low Risk:    score < 0.35 (Benign baseline transactions)   |
       +---------------------------------------------------------------+
                                      |
                           (Flagged Entries Only)
                                      |
                                      v
       +---------------------------------------------------------------+
       |                       SHAP EXPLAINABILITY                     |
       |  - shap.TreeExplainer decomposes Isolation Forest path length |
       |  - Extracts top 3 feature drivers per flagged transaction     |
       |  - Translates raw attributions to plain-English audit reasons |
       |  - Merges rule triggers + ML drivers into unified narrative   |
       +---------------------------------------------------------------+
                                      |
                                      v
       +---------------------------------------------------------------+
       |                      FASTAPI REST BACKEND                     |
       |  - POST /upload   : Ingests CSV & runs complete pipeline      |
       |  - GET  /results  : Paginated, filterable, sortable items     |
       |  - GET  /entry/:id: Full transaction metadata & SHAP drivers  |
       |  - GET  /export   : Download flagged entries with narratives  |
       |  - GET  /summary  : Real-time ledger KPI audit summary        |
       +---------------------------------------------------------------+
                                      |
                                      v
       +---------------------------------------------------------------+
       |                   REACT AUDIT DASHBOARD (VITE)                |
       |  - Executive KPI Cards (Total, Flagged, High, Med, Low Risk)  |
       |  - Drag-and-drop CSV upload with instant validation           |
       |  - Interactive table with colored badges & filter tabs        |
       |  - Detail slide-over drawer with SHAP contribution bars       |
       |  - One-click CSV exception export                             |
       +---------------------------------------------------------------+
```

---

## Real Evaluation Results (Ground Truth Benchmark)

Evaluated on 50,000 synthetic journal entries with 1,000 (2.00%) injected anomalies across 7 audit failure categories.

### 1. Overall Performance at Risk Thresholds

| Metric | Medium Risk Threshold (`>= 0.35`) | High Risk Threshold (`>= 0.55`) |
| :--- | :---: | :---: |
| **Total Flagged** | **1,362 entries (2.72% of ledger)** | **575 entries (1.15% of ledger)** |
| **True Positives (TP)** | **992** | **432** |
| **False Positives (FP)** | **370** | **143** |
| **False Negatives (FN)** | **8** | **568** |
| **True Negatives (TN)** | **48,630** | **48,857** |
| **Precision** | **72.83%** (`0.728341`) | **75.13%** (`0.751304`) |
| **Recall** | **99.20%** (`0.992000`) | **43.20%** (`0.432000`) |
| **F1-Score** | **0.839966** | **0.548571** |

> *Note*: At the Medium Risk threshold, the system captures **992 out of 1,000 injected anomalies (99.20% recall)**.

### 2. Recall Breakdown by Anomaly Category (at Medium Threshold)

| Anomaly Category | Injected | Detected | Recall Rate (%) | High-Risk Tier Detection |
| :--- | :---: | :---: | :---: | :---: |
| **`weekend_holiday`** | 143 | 143 | **100.00%** | 93 / 143 (65.03%) |
| **`round_amount`** | 143 | 143 | **100.00%** | 34 / 143 (23.78%) |
| **`duplicate`** | 143 | 143 | **100.00%** | 143 / 143 (100.00%) |
| **`below_approval_limit`** | 143 | 143 | **100.00%** | 17 / 143 (11.89%) |
| **`same_poster_approver`** | 143 | 143 | **100.00%** | 137 / 143 (95.80%) |
| **`vague_description`** | 143 | 143 | **100.00%** | 8 / 143 (5.59%) |
| **`unusual_account_amount`** | 142 | 134 | **94.37%** | 0 / 142 (0.00%) |
| **Total / Overall** | **1,000** | **992** | **99.20%** | **432 / 1,000 (43.20%)** |

### 3. Comparison: Rules Only vs. ML Only vs. Hybrid Model

| Model Approach | Total Flagged | Precision | Recall | F1-Score | Key Strength / Limitation |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Rules Only** (`rule_score >= 0.50`) | 1,001 | 85.71% | 85.80% | 0.8576 | Excellent on explicit rules, but **completely misses** `unusual_account_amount` (0% recall). |
| **ML Only** (`ml_score >= 0.60`) | 765 | 24.31% | 18.60% | 0.2108 | Detects multi-dimensional statistical outliers, but suffers from noise on discrete policy rules. |
| **Hybrid AuditLens** (`risk_score >= 0.35`) | **1,362** | **72.83%** | **99.20%** | **0.8400** | **Best overall**: Captures both discrete policy breaches and statistical outliers (94.4% on unusual amounts). |

### 4. False Positives Analysis

Out of 49,000 clean baseline entries, 370 were flagged at the Medium Risk threshold:
1. **Duplicate Counterparts (143 entries = 38.6% of FPs)**: When duplicate anomalies were injected, one copy was labeled `is_injected_anomaly = 1` while the source row remained `is_injected_anomaly = 0`. In actual audit practice, **both halves of a duplicate pair are genuine violations**. Thus, 143 of the 370 "false positives" are true duplicate transaction pairs.
2. **Extreme Statistical Tail Transactions (227 entries = 0.46% of clean ledger)**: Genuine transactions in the upper tail of the log-normal distribution (e.g. valid capital dividend allocations or large cloud hosting invoices) that deviate from median amounts. Auditors routinely sample these high-dollar transactions for substantive testing.

---

## Project Structure

```text
auditlens/
  config.py                 # Central configuration (thresholds, weights, holidays, accounts)
  data/
    generate_ledger.py      # 50,000 synthetic GL entries generator with Indian business context
    synthetic_ledger_50k.csv# Generated dataset (ground-truth labels excluded from model)
  engine/
    features.py             # Feature engineering pipeline (13 temporal, amount, SoD variables)
    rules.py                # 6 independent heuristic audit test functions + weighted scorer
    model.py                # Isolation Forest training, scoring, and joblib serialization
    scoring.py              # Hybrid risk scoring (0.5 rules + 0.5 ML) & tier assignment
    explain.py              # SHAP TreeExplainer & plain-English narrative synthesizer
  api/
    main.py                 # FastAPI service with CORS, pagination, filtering, export
  frontend/                 # Modern React dashboard built with Vite
    src/
      components/
        Header.jsx          # Header with branding and export trigger
        SummaryCards.jsx    # 5 KPI cards with INR currency formatting
        UploadSection.jsx   # Drag-and-drop CSV upload with validation
        ResultsTable.jsx    # Filterable, sortable exception table with risk badges
        EntryDetailModal.jsx# Slide-over panel with SHAP contribution bars
      App.jsx               # Application state and API integration
      index.css             # Executive audit design system styling
  notebooks/
    evaluation.ipynb        # Jupyter evaluation notebook with ground-truth analysis
  tests/
    test_rules.py           # Unit tests for each rule function
    test_scoring.py         # Unit tests for hybrid scoring and risk tiering
    test_api.py             # Integration tests for FastAPI endpoints
  requirements.txt          # Python library dependencies
  README.md                 # Project documentation and audit guide
```

---

## Setup and Local Run Instructions

### 1. Prerequisites
- Python 3.11+
- Node.js v18+ and npm

### 2. Backend Installation & Run
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Generate the 50,000 synthetic journal entry dataset (if not already generated)
python -m auditlens.data.generate_ledger

# 3. Train and serialize the Isolation Forest model
python -m auditlens.engine.model

# 4. Start the FastAPI backend server
uvicorn auditlens.api.main:app --host 127.0.0.1 --port 8000 --reload
```
The API documentation is available at `http://127.0.0.1:8000/docs`.

### 3. Frontend Installation & Run
```bash
# In a new terminal:
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser.

### 4. Running Automated Tests
```bash
pytest auditlens/tests -v
```

---

## Example Usage

### 1. Uploading a General Ledger via cURL
```bash
curl -X POST "http://127.0.0.1:8000/upload" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@auditlens/data/synthetic_ledger_50k.csv"
```

### 2. Fetching High-Risk Flagged Entries
```bash
curl -X GET "http://127.0.0.1:8000/results?page=1&page_size=10&risk_level=High"
```

### 3. Inspecting SHAP Drivers for an Entry
```bash
curl -X GET "http://127.0.0.1:8000/entry/JE-37676"
```

### 4. Exporting Flagged Exceptions to CSV
```bash
curl -X GET "http://127.0.0.1:8000/export?risk_level=High" --output high_risk_exceptions.csv
```

---

## Limitations and Auditor Guidance

> [!WARNING]
> **Synthetic Data Disclaimer**: The dataset used to benchmark AuditLens AI was synthetically generated to simulate an Indian corporate environment. Real-world corporate general ledgers contain industry-specific account structures, seasonality, ERP-specific journal types, and varied manual entry workflows. Model performance and optimal threshold calibrations will differ on production client ledgers.

> [!IMPORTANT]
> **Human Auditor Judgment Required**: Machine learning models and heuristic rules identify statistical anomalies and policy deviations; **they do not prove fraud or error**. A high risk score indicates an entry warranting substantive audit testing (e.g., inspecting source purchase orders, verifying vendor GST registration, or obtaining supervisory sign-off). Professional skepticism and human judgment remain mandatory.
