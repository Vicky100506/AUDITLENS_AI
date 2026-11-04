"""Integration tests for FastAPI endpoints."""

import io
import pytest
from fastapi.testclient import TestClient

from auditlens.api.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["model_loaded"] is True
    assert data["entries_loaded"] >= 0


def test_summary_endpoint(client):
    response = client.get("/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_entries" in data
    assert "flagged_count" in data
    assert "high_risk_count" in data
    assert "medium_risk_count" in data
    assert "low_risk_count" in data
    assert data["total_entries"] == data["high_risk_count"] + data["medium_risk_count"] + data["low_risk_count"]


def test_results_endpoint_pagination_and_filter(client):
    # Flagged entries only
    response = client.get("/results?page=1&page_size=10&only_flagged=true")
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 1
    assert data["page_size"] == 10
    assert len(data["items"]) <= 10
    assert data["total"] >= len(data["items"])

    # Filter High risk only
    res_high = client.get("/results?page=1&page_size=5&risk_level=High&only_flagged=false")
    assert res_high.status_code == 200
    for item in res_high.json()["items"]:
        assert item["risk_level"] == "High"


def test_entry_detail_endpoint(client):
    # Get first entry ID
    res = client.get("/results?page=1&page_size=1")
    assert res.status_code == 200
    entry_id = res.json()["items"][0]["entry_id"]

    # Fetch full detail
    detail_res = client.get(f"/entry/{entry_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["entry_id"] == entry_id
    assert "unified_narrative" in detail
    assert "top_drivers" in detail
    assert "features" in detail


def test_entry_not_found(client):
    response = client.get("/entry/JE-NONEXISTENT")
    assert response.status_code == 404


def test_export_csv_endpoint(client):
    response = client.get("/export")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    content = response.content.decode("utf-8")
    assert "entry_id,posting_date" in content
    assert "audit_explanation" in content


def test_upload_invalid_file_format(client):
    bad_file = io.BytesIO(b"some binary data")
    response = client.post("/upload", files={"file": ("report.pdf", bad_file, "application/pdf")})
    assert response.status_code == 400
    assert "Invalid file type" in response.json()["detail"]


def test_upload_missing_required_columns(client):
    # Missing vendor, amount, etc.
    incomplete_csv = io.BytesIO(b"entry_id,posting_date\nJE-001,2024-01-01")
    response = client.post("/upload", files={"file": ("ledger.csv", incomplete_csv, "text/csv")})
    assert response.status_code == 422
    assert "Missing required general ledger columns" in response.json()["detail"]
