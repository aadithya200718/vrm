"""
Unit tests for tool implementations.
"""
import json
import os
import pytest
from unittest.mock import patch, MagicMock


# ═══════════════════════════════════════════════════════════════════
# Test Intake Tools
# ═══════════════════════════════════════════════════════════════════

class TestParsePdf:
    """Tests for the parse_pdf tool."""

    def test_parse_valid_pdf(self, tmp_path):
        """Test parsing a valid PDF file."""
        # Create a minimal PDF for testing
        from app.tools.intake_tools import parse_pdf

        # We can't easily create a real PDF in tests, so we test with a mock
        with patch("pdfplumber.open") as mock_open:
            mock_pdf = MagicMock()
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "Sample PDF content"
            mock_page.extract_tables.return_value = []
            mock_pdf.pages = [mock_page]
            mock_pdf.metadata = {"Author": "Test"}
            mock_open.return_value.__enter__ = MagicMock(return_value=mock_pdf)
            mock_open.return_value.__exit__ = MagicMock(return_value=False)

            result = parse_pdf.invoke({"file_path": str(tmp_path / "test.pdf")})
            data = json.loads(result)
            assert data["status"] == "success"
            assert data["num_pages"] == 1
            assert "Sample PDF content" in data["text"]

    def test_parse_nonexistent_pdf(self):
        """Test parsing a non-existent PDF file."""
        from app.tools.intake_tools import parse_pdf

        result = parse_pdf.invoke({"file_path": "/nonexistent/test.pdf"})
        data = json.loads(result)
        assert data["status"] == "error"


class TestParseDocx:
    """Tests for the parse_docx tool."""

    def test_parse_invalid_docx(self):
        """Test parsing an invalid DOCX file."""
        from app.tools.intake_tools import parse_docx

        result = parse_docx.invoke({"file_path": "/nonexistent/test.docx"})
        data = json.loads(result)
        assert data["status"] == "error"


class TestClassifyDocument:
    """Tests for the classify_document tool."""

    @patch("app.tools.intake_tools.get_llm")
    def test_classify_soc2(self, mock_llm):
        """Test classifying a SOC2 document."""
        from app.tools.intake_tools import classify_document

        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "classification": "SOC2",
            "confidence": 0.95,
            "reasoning": "Document contains SOC 2 Type 2 audit report language",
        })
        mock_llm.return_value.invoke.return_value = mock_response

        result = classify_document.invoke(
            {"text": "SOC 2 Type 2 Report for Acme Corp, covering the period..."}
        )
        data = json.loads(result)
        assert data["status"] == "success"
        assert data["classification"] == "SOC2"
        assert data["confidence"] >= 0.9


class TestExtractDates:
    """Tests for the extract_dates tool."""

    @patch("app.tools.intake_tools.get_llm")
    def test_extract_dates_regex(self, mock_llm):
        """Test date extraction with regex patterns."""
        from app.tools.intake_tools import extract_dates

        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "expiration_dates": ["2025-12-31"],
            "effective_dates": ["2024-01-01"],
            "issue_dates": [],
        })
        mock_llm.return_value.invoke.return_value = mock_response

        text = "This certificate expires on 12/31/2025 and is effective from 01/01/2024."
        result = extract_dates.invoke({"text": text})
        data = json.loads(result)
        assert data["status"] == "success"
        assert len(data["regex_dates"]) > 0


# ═══════════════════════════════════════════════════════════════════
# Test Security Tools
# ═══════════════════════════════════════════════════════════════════

class TestCheckCertificateExpiry:
    """Tests for the check_certificate_expiry tool."""

    def test_expired_certificate(self):
        """Test an expired certificate."""
        from app.tools.security_tools import check_certificate_expiry

        result = check_certificate_expiry.invoke({
            "certificate_type": "SOC2",
            "expiry_date": "2020-01-01",
        })
        data = json.loads(result)
        assert data["status"] == "success"
        assert data["expiry_status"] == "expired"
        assert data["severity"] == "critical"

    def test_valid_certificate(self):
        """Test a valid certificate far from expiry."""
        from app.tools.security_tools import check_certificate_expiry

        result = check_certificate_expiry.invoke({
            "certificate_type": "ISO27001",
            "expiry_date": "2028-12-31",
        })
        data = json.loads(result)
        assert data["status"] == "success"
        assert data["expiry_status"] == "valid"
        assert data["severity"] == "info"

    def test_invalid_date_format(self):
        """Test invalid date format handling."""
        from app.tools.security_tools import check_certificate_expiry

        result = check_certificate_expiry.invoke({
            "certificate_type": "SOC2",
            "expiry_date": "not-a-date",
        })
        data = json.loads(result)
        assert data["status"] == "error"


class TestCalculateSecurityScore:
    """Tests for the calculate_security_score tool."""

    def test_perfect_score(self):
        """Test calculation with perfect scores."""
        from app.tools.security_tools import calculate_security_score

        result = calculate_security_score.invoke({
            "certificate_score": 100.0,
            "domain_security_score": 100.0,
            "breach_history_score": 100.0,
            "questionnaire_score": 100.0,
        })
        data = json.loads(result)
        assert data["status"] == "success"
        assert data["overall_score"] == 100.0
        assert data["grade"] == "A"

    def test_failing_score(self):
        """Test calculation with failing scores."""
        from app.tools.security_tools import calculate_security_score

        result = calculate_security_score.invoke({
            "certificate_score": 20.0,
            "domain_security_score": 20.0,
            "breach_history_score": 20.0,
            "questionnaire_score": 20.0,
        })
        data = json.loads(result)
        assert data["status"] == "success"
        assert data["overall_score"] == 20.0
        assert data["grade"] == "F"

    def test_weighted_calculation(self):
        """Test that weights are applied correctly."""
        from app.tools.security_tools import calculate_security_score

        result = calculate_security_score.invoke({
            "certificate_score": 100.0,
            "domain_security_score": 0.0,
            "breach_history_score": 0.0,
            "questionnaire_score": 0.0,
        })
        data = json.loads(result)
        assert data["status"] == "success"
        # Certificates weight is 0.40, so 100 * 0.40 = 40
        assert data["overall_score"] == 40.0


class TestScanDomainSecurity:
    """Tests for the scan_domain_security tool."""

    @patch("app.tools.security_tools.httpx.get")
    @patch("app.tools.security_tools.ssl.create_default_context")
    def test_scan_with_mocked_services(self, mock_ssl, mock_httpx):
        """Test domain scan with mocked external services."""
        from app.tools.security_tools import scan_domain_security

        # Mock SSL
        mock_ssl.side_effect = Exception("Connection refused")

        # Mock HTTPX
        mock_resp = MagicMock()
        mock_resp.headers = {
            "strict-transport-security": "max-age=31536000",
            "x-frame-options": "DENY",
        }
        mock_httpx.return_value = mock_resp

        result = scan_domain_security.invoke({"domain": "example.com"})
        data = json.loads(result)
        assert data["status"] == "success"
        assert "domain" in data


# ═══════════════════════════════════════════════════════════════════
# Test State Management
# ═══════════════════════════════════════════════════════════════════

class TestVendorReviewState:
    """Tests for the VendorReviewState model."""

    def test_state_creation(self):
        """Test creating a new state."""
        from app.core.state import VendorReviewState

        state = VendorReviewState(
            vendor_id="test-123",
            vendor_name="Test Corp",
            current_phase="init",
        )
        assert state.vendor_id == "test-123"
        assert state.vendor_name == "Test Corp"
        assert state.current_phase == "init"

    def test_state_serialization(self):
        """Test state serialization and deserialization."""
        from app.core.state import VendorReviewState, state_to_dict, dict_to_state

        state = VendorReviewState(
            vendor_id="test-456",
            vendor_name="Acme Corp",
            vendor_type="technology",
            contract_value=50000.0,
        )
        data = state_to_dict(state)
        restored = dict_to_state(data)

        assert restored.vendor_id == state.vendor_id
        assert restored.vendor_name == state.vendor_name
        assert restored.contract_value == state.contract_value


# ═══════════════════════════════════════════════════════════════════
# Test Configuration
# ═══════════════════════════════════════════════════════════════════

class TestConfig:
    """Tests for application configuration."""

    def test_default_settings(self):
        """Test default configuration values."""
        from app.config import Settings

        settings = Settings()
        assert settings.ollama_model == "llama3.1:8b"
        assert settings.qdrant_url == "http://localhost:6333"
        assert settings.redis_url == "redis://localhost:6379/0"
