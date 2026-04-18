from __future__ import annotations

from enum import Enum


class WorkflowType(str, Enum):
    SAAS = "saas"
    HEALTHCARE = "healthcare"


class Role(str, Enum):
    EMPLOYEE = "employee"
    VENDOR = "vendor"
    LEGAL = "legal"
    FINANCE = "finance"
    IT = "it"
    COMPLIANCE_OFFICER = "compliance_officer"
    ADMIN = "admin"
    PROCUREMENT = "procurement"
    SYSTEM = "system"


class VendorStatusEnum(str, Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    HIPAA_REVIEW_TRIGGERED = "HIPAA_REVIEW_TRIGGERED"
    INVITATION_SENT = "INVITATION_SENT"
    DOCUMENTS_SUBMITTED = "DOCUMENTS_SUBMITTED"
    VERIFICATION_IN_PROGRESS = "VERIFICATION_IN_PROGRESS"
    RISK_ASSESSMENT_COMPLETE = "RISK_ASSESSMENT_COMPLETE"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    FULLY_APPROVED = "FULLY_APPROVED"
    REJECTED = "REJECTED"
    SUBMISSION_EXPIRED = "SUBMISSION_EXPIRED"
    REQUEST_CHANGES = "REQUEST_CHANGES"


class VerificationKind(str, Enum):
    GST = "gst"
    PAN = "pan"
    BANK = "bank"
    MCA = "mca"
    SANCTIONS = "sanctions"
    SOC2 = "soc2"
    OIG = "oig"
    HEALTHCARE_SANCTIONS = "healthcare_sanctions"
    BAA = "baa"
    HIPAA_ATTESTATION = "hipaa_attestation"
    EPHI_FLOW = "ephi_flow"
    SUBPROCESSORS = "subprocessors"


class VerificationStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    FLAGGED = "flagged"
    SKIPPED = "skipped"


class ApprovalDecisionType(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_CHANGES = "request_changes"


class RiskTier(str, Enum):
    TIER_1 = "Tier 1"
    TIER_2 = "Tier 2"
    TIER_3 = "Tier 3"
    AUTO_REJECT = "Auto-Reject"

