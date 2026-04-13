"""
Integration tests for the API endpoints.
"""
import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    @patch("app.api.routes.check_db_health", return_value=True)
    @patch("app.api.routes.check_redis_health", return_value=True)
    @patch("app.api.routes.check_vector_health", return_value=True)
    @patch("app.api.routes.check_llm_health", return_value={"ollama": True, "groq": False})
    def test_all_healthy(self, mock_llm, mock_vec, mock_redis, mock_db, client):
        """Test health check when all services are up."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["services"]["database"]["status"] == "up"
        assert data["services"]["redis"]["status"] == "up"

    @patch("app.api.routes.check_db_health", return_value=False)
    @patch("app.api.routes.check_redis_health", return_value=True)
    @patch("app.api.routes.check_vector_health", return_value=True)
    @patch("app.api.routes.check_llm_health", return_value={"ollama": True, "groq": False})
    def test_degraded_health(self, mock_llm, mock_vec, mock_redis, mock_db, client):
        """Test health check when database is down."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"


class TestRootEndpoint:
    """Tests for the root endpoint."""

    def test_root(self, client):
        """Test root endpoint returns system info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "OPUS" in data["system"]
        assert "agents" in data


class TestVendorStatusEndpoint:
    """Tests for vendor status endpoint."""

    @patch("app.api.routes.get_vendor", return_value=None)
    def test_vendor_not_found(self, mock_get, client):
        """Test getting status for non-existent vendor."""
        response = client.get("/api/v1/vendors/nonexistent-id/status")
        assert response.status_code == 404

    @patch("app.api.routes.load_state", return_value=None)
    @patch("app.api.routes.get_vendor", return_value={
        "id": "test-id",
        "name": "Test Vendor",
        "status": "processing",
    })
    def test_vendor_found(self, mock_get, mock_state, client):
        """Test getting status for existing vendor."""
        response = client.get("/api/v1/vendors/test-id/status")
        assert response.status_code == 200
        data = response.json()
        assert data["vendor_name"] == "Test Vendor"


class TestPolicyUploadEndpoint:
    """Tests for security policy upload endpoint."""

    @patch("app.api.routes.upsert_policy")
    @patch("app.api.routes.create_policy", return_value={"id": "policy-123"})
    def test_upload_policy(self, mock_create, mock_upsert, client):
        """Test uploading a security policy."""
        response = client.post(
            "/api/v1/policies/security",
            json={
                "title": "Data Encryption Policy",
                "content": "All data must be encrypted at rest and in transit...",
                "category": "security",
                "source": "Internal",
                "version": "1.0",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["policy_id"] == "policy-123"
