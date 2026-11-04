import React from "react";
import { FileText, AlertTriangle, AlertCircle, ShieldAlert, CheckCircle2 } from "lucide-react";

export default function SummaryCards({ summary }) {
  if (!summary) return null;

  const formatINR = (val) => {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(val || 0);
  };

  const flaggedPct = ((summary.flagged_count / summary.total_entries) * 100).toFixed(2);
  const highPct = ((summary.high_risk_count / summary.total_entries) * 100).toFixed(2);
  const medPct = ((summary.medium_risk_count / summary.total_entries) * 100).toFixed(2);
  const lowPct = ((summary.low_risk_count / summary.total_entries) * 100).toFixed(2);

  return (
    <div className="kpi-grid">
      {/* 1. Total Entries */}
      <div className="kpi-card">
        <div className="kpi-header">
          <span>Total Ledger Entries</span>
          <FileText size={18} color="#64748b" />
        </div>
        <div className="kpi-value">{summary.total_entries.toLocaleString()}</div>
        <div className="kpi-sub">
          Total Value: {formatINR(summary.total_value_transacted)}
        </div>
      </div>

      {/* 2. Flagged Exceptions */}
      <div className="kpi-card">
        <div className="kpi-header">
          <span>Flagged Exceptions</span>
          <AlertCircle size={18} color="#0284c7" />
        </div>
        <div className="kpi-value" style={{ color: "#0369a1" }}>
          {summary.flagged_count.toLocaleString()}
        </div>
        <div className="kpi-sub">
          {flaggedPct}% of ledger | Value: {formatINR(summary.flagged_value_transacted)}
        </div>
      </div>

      {/* 3. High Risk Tier */}
      <div className="kpi-card high-risk">
        <div className="kpi-header">
          <span style={{ color: "var(--risk-high-text)" }}>High Risk Tier</span>
          <ShieldAlert size={18} color="var(--risk-high-badge)" />
        </div>
        <div className="kpi-value" style={{ color: "var(--risk-high-text)" }}>
          {summary.high_risk_count.toLocaleString()}
        </div>
        <div className="kpi-sub">
          Score ≥ {summary.high_risk_threshold} ({highPct}%)
        </div>
      </div>

      {/* 4. Medium Risk Tier */}
      <div className="kpi-card med-risk">
        <div className="kpi-header">
          <span style={{ color: "var(--risk-med-text)" }}>Medium Risk Tier</span>
          <AlertTriangle size={18} color="var(--risk-med-badge)" />
        </div>
        <div className="kpi-value" style={{ color: "var(--risk-med-text)" }}>
          {summary.medium_risk_count.toLocaleString()}
        </div>
        <div className="kpi-sub">
          {summary.medium_risk_threshold} ≤ Score &lt; {summary.high_risk_threshold} ({medPct}%)
        </div>
      </div>

      {/* 5. Low / Normal Risk Tier */}
      <div className="kpi-card low-risk">
        <div className="kpi-header">
          <span style={{ color: "var(--risk-low-text)" }}>Low / Normal Tier</span>
          <CheckCircle2 size={18} color="var(--risk-low-badge)" />
        </div>
        <div className="kpi-value" style={{ color: "var(--risk-low-text)" }}>
          {summary.low_risk_count.toLocaleString()}
        </div>
        <div className="kpi-sub">
          Score &lt; {summary.medium_risk_threshold} ({lowPct}%)
        </div>
      </div>
    </div>
  );
}
