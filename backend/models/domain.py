from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from backend.models.enums import (
    ApprovalDecisionType,
    RiskTier,
    Role,
    VerificationKind,
    VerificationStatus,
    VendorStatusEnum,
    WorkflowType,
)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class BaseRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class VendorRequestRecord(BaseRecord):
    employee_email: str
    vendor_name: str
    service_type: str
    reason: str
    contract_value: float
    contact_email: str
    workflow_type: WorkflowType = WorkflowType.SAAS
    ephi_involved: bool = False
    ephi_types: list[str] = Field(default_factory=list)
    hipaa_required: bool = False
    status: VendorStatusEnum = VendorStatusEnum.PENDING_REVIEW
    vendor_id: str | None = None


class VendorRecord(BaseRecord):
    request_id: str | None = None
    name: str
    service_type: str
    workflow_type: WorkflowType
    status: VendorStatusEnum = VendorStatusEnum.PENDING_REVIEW
    contract_value: float
    contact_email: str
    domain: str | None = None
    vendor_type: str | None = None
    current_phase: str = "intake"
    current_agent: str | None = None
    current_step: str | None = None
    progress_percentage: float = 0.0
    overall_risk_score: float | None = None
    risk_level: str | None = None
    approval_tier: str | None = None
    approval_status: str | None = None
    approval_id: str | None = None
    errors: list[str] = Field(default_factory=list)
    agent_errors: list[dict[str, Any]] = Field(default_factory=list)
    checklist_required: int = 8
    checklist_received: int = 0
    ephi_involved: bool = False
    ephi_types: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class VendorDocumentRecord(BaseRecord):
    vendor_id: str
    file_name: str
    file_type: str
    document_type: str | None = None
    classification: str | None = None
    classification_confidence: float | None = None
    processing_status: str = "queued"
    extracted_text: str = ""
    extracted_metadata: dict[str, Any] = Field(default_factory=dict)
    extracted_dates: dict[str, Any] = Field(default_factory=dict)
    storage_path: str | None = None


class VerificationResultRecord(BaseRecord):
    vendor_id: str
    kind: VerificationKind
    workflow_type: WorkflowType
    status: VerificationStatus
    result: str
    confidence_score: float
    details: dict[str, Any] = Field(default_factory=dict)
    agent_name: str
    queue_name: str


class HipaaVerificationRecord(VerificationResultRecord):
    pass


class BAARecord(BaseRecord):
    vendor_id: str
    status: str
    confidence_score: float
    clauses: dict[str, dict[str, Any]] = Field(default_factory=dict)
    clauses_missing: list[str] = Field(default_factory=list)
    expiry_date: str | None = None


class ApprovalWorkflowRecord(BaseRecord):
    vendor_id: str
    workflow_type: WorkflowType
    status: str = "pending"
    approval_tier: str = RiskTier.TIER_2.value
    required_approvers: list[dict[str, Any]] = Field(default_factory=list)
    current_step_role: str | None = None
    completion_percentage: float = 0.0
    deadline: datetime | None = None
    final_decision: str | None = None
    permission_level: str | None = None


class ApprovalDecisionRecord(BaseRecord):
    approval_id: str
    vendor_id: str
    role: Role
    approver_name: str
    approver_email: str
    decision: ApprovalDecisionType
    comments: str
    conditions: list[str] = Field(default_factory=list)
    permission_level: str | None = None


class OnboardingTokenRecord(BaseRecord):
    vendor_id: str
    request_id: str
    workflow_type: WorkflowType
    token: str
    expires_at: datetime
    used: bool = False


class NotificationLogRecord(BaseRecord):
    vendor_id: str | None = None
    request_id: str | None = None
    recipient: str
    template: str
    subject: str
    status: str
    payload: dict[str, Any] = Field(default_factory=dict)


class BayesianScoreRecord(BaseRecord):
    vendor_id: str
    workflow_type: WorkflowType
    probability_legitimate: float
    probability_fraud: float
    confidence_interval: dict[str, float]
    risk_tier: str
    evidence_explanation: list[str] = Field(default_factory=list)
    hard_override: str | None = None
    hipaa_overrides: list[str] = Field(default_factory=list)
    hipaa_risk_factors: list[str] = Field(default_factory=list)


class RiskAssessmentRecord(BaseRecord):
    vendor_id: str
    workflow_type: WorkflowType
    bayesian_tier: str
    rl_tier: str
    models_agree: bool
    confidence_indicator: str
    overall_risk_score: float
    risk_level: str
    approval_tier: str
    executive_summary: str
    critical_blockers: list[str] = Field(default_factory=list)
    conditional_items: list[str] = Field(default_factory=list)
    mitigation_recommendations: list[dict[str, str]] = Field(default_factory=list)
    state_vector: list[float] = Field(default_factory=list)


class RLTrainingEpisodeRecord(BaseRecord):
    vendor_id: str
    workflow_type: WorkflowType
    state_vector: list[float]
    action: int
    reward: float
    actual_outcome: str


class RiskModelFeedbackRecord(BaseRecord):
    vendor_id: str
    workflow_type: WorkflowType
    predicted_tier: str
    actual_outcome: str
    reward: float


class ModelVersionRecord(BaseRecord):
    model_name: str
    version: str
    workflow_type: WorkflowType | None = None
    accuracy: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class VendorEmbeddingRecord(BaseRecord):
    vendor_id: str
    document_id: str
    doc_type: str
    dimensions: int
    vector: list[float]


class ScheduledTaskRecord(BaseRecord):
    vendor_id: str
    task_type: str
    due_at: datetime
    status: str = "scheduled"
    metadata: dict[str, Any] = Field(default_factory=dict)


class EPHIAccessLogRecord(BaseRecord):
    vendor_id: str
    actor_email: str
    actor_role: Role
    action: str
    details: dict[str, Any] = Field(default_factory=dict)


class WorkflowEventRecord(BaseRecord):
    vendor_id: str
    event_type: str
    data: dict[str, Any] = Field(default_factory=dict)

