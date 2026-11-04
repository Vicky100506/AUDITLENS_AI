import React from "react";
import { Search, ChevronLeft, ChevronRight, ArrowUpDown, Info, Eye } from "lucide-react";

export default function ResultsTable({
  items,
  total,
  page,
  pageSize,
  totalPages,
  onPageChange,
  riskFilter,
  onRiskFilterChange,
  searchQuery,
  onSearchChange,
  sortBy,
  sortDir,
  onSortChange,
  onSelectEntry,
  loading,
}) {
  const formatINR = (val) => {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 2,
    }).format(val || 0);
  };

  const getBadgeClass = (level) => {
    if (level === "High") return "badge badge-high";
    if (level === "Medium") return "badge badge-med";
    return "badge badge-low";
  };

  return (
    <div className="table-card">
      {/* Toolbar */}
      <div className="table-toolbar">
        {/* Risk Level Filter Tabs */}
        <div className="filter-tabs">
          <button
            className={`tab-btn ${riskFilter === "FLAGGED" ? "active" : ""}`}
            onClick={() => onRiskFilterChange("FLAGGED")}
          >
            Flagged Only
          </button>
          <button
            className={`tab-btn ${riskFilter === "High" ? "active" : ""}`}
            onClick={() => onRiskFilterChange("High")}
          >
            High Risk
          </button>
          <button
            className={`tab-btn ${riskFilter === "Medium" ? "active" : ""}`}
            onClick={() => onRiskFilterChange("Medium")}
          >
            Medium Risk
          </button>
          <button
            className={`tab-btn ${riskFilter === "All" ? "active" : ""}`}
            onClick={() => onRiskFilterChange("All")}
          >
            All Ledger Rows
          </button>
        </div>

        {/* Search & Sort Controls */}
        <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
          <div style={{ position: "relative" }}>
            <Search
              size={16}
              color="#94a3b8"
              style={{ position: "absolute", left: 10, top: 10 }}
            />
            <input
              type="text"
              placeholder="Search vendor, user, ID..."
              className="search-input"
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
            />
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "0.8125rem" }}>
            <ArrowUpDown size={15} color="#64748b" />
            <select
              style={{
                padding: "8px 10px",
                borderRadius: "6px",
                border: "1px solid var(--border-color)",
                fontSize: "0.8125rem",
                outline: "none",
                background: "#ffffff",
              }}
              value={`${sortBy}:${sortDir}`}
              onChange={(e) => {
                const [sb, sd] = e.target.value.split(":");
                onSortChange(sb, sd);
              }}
            >
              <option value="risk_score:desc">Risk Score (Highest First)</option>
              <option value="risk_score:asc">Risk Score (Lowest First)</option>
              <option value="amount:desc">Amount (Highest First)</option>
              <option value="amount:asc">Amount (Lowest First)</option>
              <option value="posting_date:desc">Posting Date (Newest)</option>
            </select>
          </div>
        </div>
      </div>

      {/* Table Data */}
      <div className="data-table-wrapper">
        <table className="data-table">
          <thead>
            <tr>
              <th>Entry ID</th>
              <th>Date & Time</th>
              <th>Account</th>
              <th>Vendor</th>
              <th style={{ textAlign: "right" }}>Amount (INR)</th>
              <th>Posted / Approved By</th>
              <th style={{ textAlign: "center" }}>Risk Tier</th>
              <th style={{ textAlign: "center" }}>Risk Score</th>
              <th>Audit Policy & Anomaly Flags</th>
              <th style={{ textAlign: "center" }}>Action</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={10} style={{ textAlign: "center", padding: "40px" }}>
                  <div style={{ display: "inline-flex", alignItems: "center", gap: "10px" }}>
                    <div className="spinner"></div>
                    <span style={{ color: "var(--text-secondary)" }}>Filtering & sorting entries...</span>
                  </div>
                </td>
              </tr>
            ) : items.length === 0 ? (
              <tr>
                <td colSpan={10} style={{ textAlign: "center", padding: "40px", color: "var(--text-muted)" }}>
                  No transactions match the selected filter criteria.
                </td>
              </tr>
            ) : (
              items.map((row) => (
                <tr
                  key={row.entry_id}
                  className="row-interactive"
                  onClick={() => onSelectEntry(row.entry_id)}
                >
                  <td style={{ fontWeight: 600, color: "var(--primary)" }}>{row.entry_id}</td>
                  <td style={{ whiteSpace: "nowrap" }}>
                    <div>{row.posting_date}</div>
                    <div style={{ fontSize: "0.725rem", color: "var(--text-muted)" }}>{row.posting_time}</div>
                  </td>
                  <td>
                    <div style={{ fontWeight: 500 }}>{row.account_name}</div>
                    <div style={{ fontSize: "0.725rem", color: "var(--text-muted)" }}>
                      Code: {row.account_code}
                    </div>
                  </td>
                  <td style={{ maxWidth: "160px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {row.vendor}
                  </td>
                  <td style={{ textAlign: "right", fontWeight: 600, whiteSpace: "nowrap" }}>
                    {formatINR(row.amount)}
                  </td>
                  <td>
                    <div>{row.posted_by}</div>
                    <div style={{ fontSize: "0.725rem", color: row.posted_by === row.approved_by ? "#dc2626" : "var(--text-muted)" }}>
                      Appr: {row.approved_by} {row.posted_by === row.approved_by ? "(SoD Breach!)" : ""}
                    </div>
                  </td>
                  <td style={{ textAlign: "center" }}>
                    <span className={getBadgeClass(row.risk_level)}>{row.risk_level}</span>
                  </td>
                  <td style={{ textAlign: "center", fontWeight: 700 }}>
                    {(row.risk_score * 100).toFixed(1)}%
                  </td>
                  <td>
                    <div style={{ display: "flex", flexWrap: "wrap", maxWidth: "340px" }}>
                      {row.short_reasons && row.short_reasons.length > 0 ? (
                        row.short_reasons.slice(0, 2).map((r, i) => (
                          <span key={i} className="rule-pill" title={r}>
                            {r}
                          </span>
                        ))
                      ) : (
                        <span style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>None</span>
                      )}
                      {row.short_reasons && row.short_reasons.length > 2 && (
                        <span className="rule-pill" style={{ background: "#e2e8f0" }}>
                          +{row.short_reasons.length - 2} more
                        </span>
                      )}
                    </div>
                  </td>
                  <td style={{ textAlign: "center" }}>
                    <button
                      className="btn btn-secondary"
                      style={{ padding: "4px 8px", fontSize: "0.75rem" }}
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectEntry(row.entry_id);
                      }}
                      title="Inspect SHAP drivers and policy violations"
                    >
                      <Eye size={14} /> Explain
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Bar */}
      <div className="pagination-bar">
        <div>
          Showing {items.length > 0 ? (page - 1) * pageSize + 1 : 0} to{" "}
          {Math.min(page * pageSize, total)} of {total.toLocaleString()} entries
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <button
            className="btn btn-secondary"
            style={{ padding: "5px 10px" }}
            onClick={() => onPageChange(page - 1)}
            disabled={page <= 1}
          >
            <ChevronLeft size={16} /> Prev
          </button>

          <span style={{ fontWeight: 600, padding: "0 6px" }}>
            Page {page} of {totalPages}
          </span>

          <button
            className="btn btn-secondary"
            style={{ padding: "5px 10px" }}
            onClick={() => onPageChange(page + 1)}
            disabled={page >= totalPages}
          >
            Next <ChevronRight size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
