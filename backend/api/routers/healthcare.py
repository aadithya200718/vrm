from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.api.deps import approver_roles, service_dependency
from backend.core.services import VendorOnboardingService
from backend.models.enums import Role
from backend.models.requests import ComplianceQueryRequest, HealthcareChatRequest


router = APIRouter()


@router.get("/healthcare/ephi-log/{vendor_id}")
def get_ephi_log(
    vendor_id: str,
    service: VendorOnboardingService = Depends(service_dependency),
    _auth=Depends(approver_roles(Role.COMPLIANCE_OFFICER)),
):
    return service.get_ephi_logs(vendor_id)


@router.post("/rag/compliance/query")
def compliance_query(
    payload: ComplianceQueryRequest,
    service: VendorOnboardingService = Depends(service_dependency),
    _auth=Depends(approver_roles(Role.COMPLIANCE_OFFICER, Role.ADMIN)),
):
    return service.rag_compliance_query(payload.query, payload.vendor_id)


@router.post("/chat/vendor/healthcare")
def healthcare_chat(
    payload: HealthcareChatRequest,
    service: VendorOnboardingService = Depends(service_dependency),
):
    return service.healthcare_chat(payload)
