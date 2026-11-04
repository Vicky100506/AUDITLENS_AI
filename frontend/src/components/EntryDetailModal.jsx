import React, { useState } from "react";
import { X, ShieldAlert, Cpu, FileCheck2, AlertCircle, ChevronDown, ChevronUp } from "lucide-react";

export default function EntryDetailModal({ entry, onClose }) {
  const [showRawFeatures, setShowRawFeatures] = useState(false);

  if (!entry) return null;

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
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div
          style={{
            padding: "20px 24px",
            borderBottom: "1px solid var(--border-color)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            position: "sticky",
            top: 0,
            background: "#ffffff",
            zIndex: 10,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <span style={{ fontSize: "1.25rem", fontWeight: 700 }}>
              {entry.entry_id}
            </span>
            <span className={getBadgeClass(entry.risk_level)} style={{ fontSize: "0.8125rem" }}>
              {entry.risk_level} Risk
            </span>
            <span style={{ fontSize: "0.875rem", color: "var(--text-secondary)", fontWeight: 600 }}>
              Risk Score: {(entry.risk_score * 100).toFixed(1)}%
            </span>
          </div>

          <button
            onClick={onClose}
            style={{
              background: "transparent",
              border: "none",
              cursor: "pointer",
              padding: "4px",
              borderRadius: "4px",
              color: "var(--text-muted)",
            }}
          >
            <X size={22} />
          </button>
        </div>

        {/* Body */}
        <div style={{ padding: "24px", display: "flex", flexDirection: "column", gap: "24px" }}>
          {/* Executive Narrative */}
          <div
            style={{
              background: "#f0fdf4",
              border: "1px solid #bbf7d0",
              borderRadius: "8px",
              padding: "16px",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "6px" }}>
              <FileCheck2 size={18} color="#15803d" />
              <strong style={{ fontSize: "0.875rem", color: "#166534" }}>
                Auditor Executive Narrative
              </strong>
            </div>
            <p style={{ fontSize: "0.875rem", color: "#14532d", lineHeight: 1.5 }}>
              {entry.unified_narrative || "No unified narrative computed."}
            </p>
          </div>

          {/* Scores Breakdown */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "12px",
              background: "#f8fafc",
              padding: "14px",
              borderRadius: "8px",
              border: "1px solid var(--border-color)",
            }}
          >
            <div>
              <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", textTransform: "uppercase" }}>
                Rule Engine Score (50% Weight)
              </div>
              <div style={{ fontSize: "1.25rem", fontWeight: 700, color: "var(--text-primary)" }}>
                {(entry.rule_score * 100).toFixed(1)}%
              </div>
            </div>
            <div>
              <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", textTransform: "uppercase" }}>
                Isolation Forest ML Score (50% Weight)
              </div>
              <div style={{ fontSize: "1.25rem", fontWeight: 700, color: "var(--text-primary)" }}>
                {(entry.ml_score * 100).toFixed(1)}%
              </div>
            </div>
          </div>

          {/* Transaction Metadata Grid */}
          <div>
            <h4 style={{ fontSize: "0.875rem", fontWeight: 700, marginBottom: "12px", textTransform: "uppercase", letterSpacing: "0.04em", color: "var(--text-secondary)" }}>
              Transaction Parameters
            </h4>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: "12px",
                fontSize: "0.875rem",
              }}
            >
              <div style={{ background: "#f8fafc", padding: "10px 12px", borderRadius: "6px", border: "1px solid #f1f5f9" }}>
                <div style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>Amount (INR)</div>
                <div style={{ fontWeight: 700, fontSize: "1rem", color: "var(--primary)" }}>
                  {formatINR(entry.amount)}
                </div>
              </div>

              <div style={{ background: "#f8fafc", padding: "10px 12px", borderRadius: "6px", border: "1px solid #f1f5f9" }}>
                <div style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>Posting Timestamp</div>
                <div style={{ fontWeight: 600 }}>
                  {entry.posting_date} at {entry.posting_time}
                </div>
              </div>

              <div style={{ background: "#f8fafc", padding: "10px 12px", borderRadius: "6px", border: "1px solid #f1f5f9" }}>
                <div style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>Account</div>
                <div style={{ fontWeight: 600 }}>{entry.account_name}</div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Code: {entry.account_code}</div>
              </div>

              <div style={{ background: "#f8fafc", padding: "10px 12px", borderRadius: "6px", border: "1px solid #f1f5f9" }}>
                <div style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>Vendor / Entity</div>
                <div style={{ fontWeight: 600 }}>{entry.vendor}</div>
              </div>

              <div style={{ background: "#f8fafc", padding: "10px 12px", borderRadius: "6px", border: "1px solid #f1f5f9" }}>
                <div style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>Posted By</div>
                <div style={{ fontWeight: 600 }}>{entry.posted_by}</div>
              </div>

              <div
                style={{
                  background: entry.posted_by === entry.approved_by ? "#fef2f2" : "#f8fafc",
                  padding: "10px 12px",
                  borderRadius: "6px",
                  border: entry.posted_by === entry.approved_by ? "1px solid #fecaca" : "1px solid #f1f5f9",
                }}
              >
                <div style={{ color: entry.posted_by === entry.approved_by ? "#991b1b" : "var(--text-muted)", fontSize: "0.75rem" }}>
                  Approved By {entry.posted_by === entry.approved_by ? "(SoD Breach!)" : ""}
                </div>
                <div style={{ fontWeight: 600, color: entry.posted_by === entry.approved_by ? "#dc2626" : "inherit" }}>
                  {entry.approved_by}
                </div>
              </div>

              <div style={{ gridColumn: "span 2", background: "#f8fafc", padding: "10px 12px", borderRadius: "6px", border: "1px solid #f1f5f9" }}>
                <div style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>Journal Description Narrative</div>
                <div style={{ fontStyle: entry.description ? "normal" : "italic", color: entry.description ? "inherit" : "var(--text-muted)" }}>
                  {entry.description || "(Empty description)"}
                </div>
              </div>
            </div>
          </div>

          {/* Audit Rule Triggers */}
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "12px" }}>
              <ShieldAlert size={18} color="#dc2626" />
              <h4 style={{ fontSize: "0.875rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.04em", color: "var(--text-secondary)" }}>
                Audit Rule Violations ({entry.rule_reasons ? entry.rule_reasons.length : 0})
              </h4>
            </div>

            {entry.rule_reasons && entry.rule_reasons.length > 0 ? (
              <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                {entry.rule_reasons.map((r, i) => (
                  <div
                    key={i}
                    style={{
                      background: "#fef2f2",
                      border: "1px solid #fecaca",
                      borderRadius: "6px",
                      padding: "10px 14px",
                      fontSize: "0.875rem",
                      color: "#991b1b",
                      display: "flex",
                      alignItems: "center",
                      gap: "10px",
                    }}
                  >
                    <AlertCircle size={16} />
                    <span>{r}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ fontSize: "0.875rem", color: "var(--text-muted)", fontStyle: "italic" }}>
                No deterministic audit rules were triggered. Flagged predominantly via machine learning.
              </div>
            )}
          </div>

          {/* SHAP Machine Learning Drivers */}
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "12px" }}>
              <Cpu size={18} color="#2563eb" />
              <h4 style={{ fontSize: "0.875rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.04em", color: "var(--text-secondary)" }}>
                Top SHAP Anomaly Attribution Drivers
              </h4>
            </div>

            {entry.top_drivers && entry.top_drivers.length > 0 ? (
              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                {entry.top_drivers.map((drv, i) => (
                  <div
                    key={i}
                    style={{
                      background: "#f0f7ff",
                      border: "1px solid #bfdbfe",
                      borderRadius: "6px",
                      padding: "12px 14px",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                      <span style={{ fontWeight: 600, fontSize: "0.8125rem", color: "#1e40af" }}>
                        Driver {i + 1}: {drv.feature}
                      </span>
                      <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "#1d4ed8" }}>
                        Attribution: +{drv.attribution.toFixed(3)}
                      </span>
                    </div>
                    <div style={{ fontSize: "0.875rem", color: "#1e3a8a" }}>
                      {drv.reason}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ fontSize: "0.875rem", color: "var(--text-muted)" }}>
                SHAP drivers calculated for flagged entries.
              </div>
            )}
          </div>

          {/* Raw Feature Inspection Accordion */}
          {entry.features && Object.keys(entry.features).length > 0 && (
            <div style={{ borderTop: "1px solid var(--border-color)", paddingTop: "16px" }}>
              <button
                onClick={() => setShowRawFeatures(!showRawFeatures)}
                style={{
                  background: "transparent",
                  border: "none",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  width: "100%",
                  color: "var(--text-secondary)",
                  fontSize: "0.8125rem",
                  fontWeight: 600,
                }}
              >
                <span>Technical Model Features ({Object.keys(entry.features).length} variables)</span>
                {showRawFeatures ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
              </button>

              {showRawFeatures && (
                <div
                  style={{
                    marginTop: "12px",
                    maxHeight: "220px",
                    overflowY: "auto",
                    background: "#f8fafc",
                    border: "1px solid var(--border-color)",
                    borderRadius: "6px",
                  }}
                >
                  <table style={{ width: "100%", fontSize: "0.75rem", borderCollapse: "collapse" }}>
                    <tbody>
                      {Object.entries(entry.features).map(([k, v]) => (
                        <tr key={k} style={{ borderBottom: "1px solid #e2e8f0" }}>
                          <td style={{ padding: "6px 12px", fontWeight: 600, color: "#334155" }}>{k}</td>
                          <td style={{ padding: "6px 12px", textAlign: "right", fontFamily: "monospace" }}>
                            {typeof v === "number" ? v.toFixed(4) : String(v)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
