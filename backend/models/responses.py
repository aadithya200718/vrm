from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class VendorRequestResponse(BaseModel):
    status: str
    request_id: str
    workflow_type: str
    message: str


class InviteVendorResponse(BaseModel):
    status: str
    token: str
    portal_url: str
    expires_at: datetime
    checklist_count: int


class TokenValidationResponse(BaseModel):
    valid: bool
    vendor_id: str | None = None
    workflow_type: str | None = None
    expires_at: datetime | None = None
    documents_required: int | None = None


class DocumentUploadResponse(BaseModel):
    status: str
    vendor_id: str
    documents_received: int
    documents_required: int
    missing: list[str]
    document_ids: list[str]


class GenericMessageResponse(BaseModel):
    status: str
    message: str
    data: dict[str, Any] | None = None
