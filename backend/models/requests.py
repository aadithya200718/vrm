from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, EmailStr, Field

from backend.models.enums import ApprovalDecisionType


class VendorRequestSchema(BaseModel):
    vendor_name: str = Field(min_length=2)
    service_type: str = Field(min_length=2)
    reason: str = Field(min_length=4)
    contract_value: float = Field(ge=0)
    contact_email: EmailStr


class HealthcareVendorRequestSchema(VendorRequestSchema):
    ephi_involved: bool
    ephi_types: list[str] = Field(default_factory=list)


class InviteVendorRequest(BaseModel):
    support_contact: EmailStr | None = None


class ApprovalDecisionSchema(BaseModel):
    decision: ApprovalDecisionType
    comments: str = ""
    conditions: list[str] = Field(default_factory=list)
    permission_level: Literal["read-only", "read-write", "admin"] | None = None


class ComplianceQueryRequest(BaseModel):
    query: str = Field(min_length=3)
    vendor_id: str | None = None


class HealthcareChatRequest(BaseModel):
    token: str | None = None
    vendor_id: str | None = None
    message: str = Field(min_length=1)


class EvidenceRequestSchema(BaseModel):
    message: str | None = None

