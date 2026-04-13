"""
LangGraph shared state schema for the multi-agent vendor review workflow.
"""
from __future__ import annotations

from typing import Annotated, Any, Optional
from pydantic import BaseModel, Field
from langgraph.graph.message import add_messages


class DocumentInfo(BaseModel):
    """Represents a processed document."""
    doc_id: str = ""
    file_name: str = ""
    file_type: str = ""
    classification: str = ""
    classification_confidence: float = 0.0
    extracted_text: str = ""
    extracted_metadata: dict = Field(default_factory=dict)
    extracted_dates: dict = Field(default_factory=dict)
    processing_status: str = "pending"
    error: Optional[str] = None


class SecurityFinding(BaseModel):
    """A single security finding."""
    category: str = ""
    title: str = ""
    severity: str = "info"  # critical, high, medium, low, info
    description: str = ""
    evidence: str = ""
    recommendation: str = ""


class SecurityReviewResult(BaseModel):
    """Result of the security review agent."""
    overall_score: float = 0.0
    grade: str = "F"
    certificate_score: float = 0.0
    domain_security_score: float = 0.0
    breach_history_score: float = 0.0
    questionnaire_score: float = 0.0
    findings: list[SecurityFinding] = Field(default_factory=list)
    critical_issues: list[dict] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    report: dict = Field(default_factory=dict)


class VendorReviewState(BaseModel):
    """
    The shared state object used by all agents in the LangGraph workflow.
    This is the single source of truth for the entire review process.
    """

    # ── Vendor Information ──────────────────────────────
    vendor_id: str = ""
    vendor_name: str = ""
    vendor_type: str = ""
    contract_value: float = 0.0
    vendor_domain: str = ""

    # ── Documents ───────────────────────────────────────
    submitted_documents: list[str] = Field(default_factory=list)
    classified_documents: list[DocumentInfo] = Field(default_factory=list)

    # ── Review Results ──────────────────────────────────
    security_findings: Optional[SecurityReviewResult] = None

    # ── Agent Communication ─────────────────────────────
    messages: Annotated[list, add_messages] = Field(default_factory=list)

    # ── Workflow Control ────────────────────────────────
    current_phase: str = "init"  # init, intake, security_review, compiling, done, error
    current_agent: str = ""
    progress_percentage: float = 0.0
    errors: list[str] = Field(default_factory=list)

    # ── Audit ───────────────────────────────────────────
    audit_trail: list[dict] = Field(default_factory=list)


# Helper to convert state to a serializable dict (for Redis / DB)
def state_to_dict(state: VendorReviewState) -> dict:
    """Convert a VendorReviewState to a JSON-serializable dict."""
    return state.model_dump(mode="json")


def dict_to_state(data: dict) -> VendorReviewState:
    """Reconstruct a VendorReviewState from a dict."""
    return VendorReviewState.model_validate(data)
