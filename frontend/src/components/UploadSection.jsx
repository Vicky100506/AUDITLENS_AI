import React, { useRef, useState } from "react";
import { UploadCloud, FileSpreadsheet, RefreshCw, AlertCircle } from "lucide-react";

export default function UploadSection({ onUpload, onReloadDefault, uploading, error }) {
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef(null);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragOver(true);
    } else if (e.type === "dragleave") {
      setDragOver(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      handleFileSelected(file);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelected(e.target.files[0]);
    }
  };

  const handleFileSelected = (file) => {
    if (!file.name.toLowerCase().endsWith(".csv")) {
      alert("Please upload a standard CSV file.");
      return;
    }
    onUpload(file);
  };

  return (
    <div className="upload-card">
      {error && (
        <div className="alert-error">
          <AlertCircle size={20} />
          <div>
            <strong>Validation Error:</strong> {error}
          </div>
        </div>
      )}

      <div
        className={`upload-area ${dragOver ? "drag-over" : ""}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current && fileInputRef.current.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv"
          style={{ display: "none" }}
          onChange={handleFileChange}
        />

        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "8px" }}>
          {uploading ? (
            <div className="spinner" style={{ width: 32, height: 32 }}></div>
          ) : (
            <UploadCloud size={38} color="#2563eb" />
          )}

          <div style={{ fontSize: "1rem", fontWeight: 600, color: "var(--text-primary)" }}>
            {uploading ? "Ingesting & Analyzing General Ledger..." : "Upload General Ledger CSV"}
          </div>

          <p style={{ fontSize: "0.825rem", color: "var(--text-secondary)", maxWidth: "560px" }}>
            Drag and drop your general ledger export here, or click to browse. The pipeline
            executes 6 audit-style heuristic checks, Isolation Forest unsupervised scoring, and SHAP explainability.
          </p>

          <div style={{ display: "flex", gap: "10px", marginTop: "10px" }}>
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", alignSelf: "center" }}>
              Expected columns: entry_id, posting_date, posting_time, account_code, account_name, vendor, amount, posted_by, approved_by, description
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
