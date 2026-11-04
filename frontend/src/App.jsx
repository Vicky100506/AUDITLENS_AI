import React, { useState, useEffect, useCallback } from "react";
import Header from "./components/Header";
import SummaryCards from "./components/SummaryCards";
import UploadSection from "./components/UploadSection";
import ResultsTable from "./components/ResultsTable";
import EntryDetailModal from "./components/EntryDetailModal";

const API_BASE = "/api";

export default function App() {
  const [summary, setSummary] = useState(null);
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [totalPages, setTotalPages] = useState(1);

  const [riskFilter, setRiskFilter] = useState("FLAGGED"); // FLAGGED, High, Medium, All
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState("risk_score");
  const [sortDir, setSortDir] = useState("desc");

  const [selectedEntry, setSelectedEntry] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [loadingResults, setLoadingResults] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState(null);

  // Fetch Summary KPI metrics
  const loadSummary = async () => {
    try {
      const res = await fetch(`${API_BASE}/summary`);
      if (res.ok) {
        const data = await res.json();
        setSummary(data);
      }
    } catch (err) {
      console.warn("Could not fetch summary:", err.message);
    }
  };

  // Fetch Table Results
  const loadResults = useCallback(async () => {
    setLoadingResults(true);
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
        sort_by: sortBy,
        sort_dir: sortDir,
      });

      if (riskFilter === "FLAGGED") {
        params.append("only_flagged", "true");
      } else if (riskFilter === "All") {
        params.append("only_flagged", "false");
      } else {
        params.append("only_flagged", "false");
        params.append("risk_level", riskFilter);
      }

      if (searchQuery.trim()) {
        params.append("search", searchQuery.trim());
      }

      const res = await fetch(`${API_BASE}/results?${params.toString()}`);
      if (res.ok) {
        const data = await res.json();
        setItems(data.items);
        setTotal(data.total);
        setTotalPages(data.total_pages);
      }
    } catch (err) {
      console.error("Error loading results:", err);
    } finally {
      setLoadingResults(false);
    }
  }, [page, pageSize, riskFilter, searchQuery, sortBy, sortDir]);

  // Initial load
  useEffect(() => {
    loadSummary();
  }, []);

  useEffect(() => {
    loadResults();
  }, [loadResults]);

  // Handle CSV file upload
  const handleUpload = async (file) => {
    setUploading(true);
    setError(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${API_BASE}/upload`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Failed to process ledger file.");
      }

      const summaryData = await res.json();
      setSummary(summaryData);
      setPage(1);
      loadResults();
    } catch (err) {
      console.error("Upload error:", err);
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  // Handle row click -> open detail drawer
  const handleSelectEntry = async (entryId) => {
    try {
      const res = await fetch(`${API_BASE}/entry/${entryId}`);
      if (res.ok) {
        const data = await res.json();
        setSelectedEntry(data);
      }
    } catch (err) {
      console.error("Failed to load entry details:", err);
    }
  };

  // Handle CSV export
  const handleExport = async () => {
    setExporting(true);
    try {
      const levelParam = riskFilter !== "FLAGGED" && riskFilter !== "All" ? `?risk_level=${riskFilter}` : "";
      const res = await fetch(`${API_BASE}/export${levelParam}`);
      if (!res.ok) throw new Error("Failed to export CSV.");

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `auditlens_exceptions_${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert("Export failed: " + err.message);
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="app-container">
      <Header
        summary={summary}
        onExport={handleExport}
        exporting={exporting}
      />

      <main className="main-content">
        {/* Upload Section */}
        <UploadSection
          onUpload={handleUpload}
          uploading={uploading}
          error={error}
        />

        {/* KPI Cards */}
        <SummaryCards summary={summary} />

        {/* Filterable Table */}
        <ResultsTable
          items={items}
          total={total}
          page={page}
          pageSize={pageSize}
          totalPages={totalPages}
          onPageChange={setPage}
          riskFilter={riskFilter}
          onRiskFilterChange={(rf) => {
            setRiskFilter(rf);
            setPage(1);
          }}
          searchQuery={searchQuery}
          onSearchChange={(sq) => {
            setSearchQuery(sq);
            setPage(1);
          }}
          sortBy={sortBy}
          sortDir={sortDir}
          onSortChange={(sb, sd) => {
            setSortBy(sb);
            setSortDir(sd);
            setPage(1);
          }}
          onSelectEntry={handleSelectEntry}
          loading={loadingResults}
        />
      </main>

      {/* Slide-over Detail Modal */}
      {selectedEntry && (
        <EntryDetailModal
          entry={selectedEntry}
          onClose={() => setSelectedEntry(null)}
        />
      )}
    </div>
  );
}
