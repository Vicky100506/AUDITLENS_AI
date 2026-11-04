import React from "react";
import { ShieldCheck, Download, Activity, FileSpreadsheet } from "lucide-react";

export default function Header({ summary, onExport, exporting }) {
  return (
    <header className="header">
      <div className="brand">
        <div className="brand-icon">
          <ShieldCheck size={26} strokeWidth={2.2} />
        </div>
        <div>
          <div style={{ display: "flex", alignItems: "center" }}>
            <span className="brand-title">AuditLens AI</span>
            <span className="brand-tag">Explainable Anomaly Detector</span>
          </div>
          <span className="brand-sub">
            Forensic Journal Entry Risk Scoring & SHAP Explanations for Financial Auditors
          </span>
        </div>
      </div>

      <div className="header-actions">
        <div className="status-pill">
          <span className="status-dot"></span>
          <span>Engine Active</span>
        </div>

        <button
          className="btn btn-secondary"
          onClick={onExport}
          disabled={exporting || !summary}
          title="Download flagged entries with audit explanations as CSV"
        >
          <Download size={16} />
          {exporting ? "Exporting..." : "Export Flagged CSV"}
        </button>
      </div>
    </header>
  );
}
