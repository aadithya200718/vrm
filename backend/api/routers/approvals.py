from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.api.deps import approver_roles, service_dependency
from backend.core.services import VendorOnboardingService
from backend.models.enums import Role
from backend.models.requests import ApprovalDecisionSchema


router = APIRouter()


@router.post("/approvals/{vendor_id}/legal")
def legal_approval(
    vendor_id: str,
    payload: ApprovalDecisionSchema,
    service: VendorOnboardingService = Depends(service_dependency),
    auth=Depends(approver_roles(Role.LEGAL)),
):
    return service.submit_approval(vendor_id, Role.LEGAL, auth.email, payload)


@router.post("/approvals/{vendor_id}/finance")
def finance_approval(
    vendor_id: str,
    payload: ApprovalDecisionSchema,
    service: VendorOnboardingService = Depends(service_dependency),
    auth=Depends(approver_roles(Role.FINANCE)),
):
    return service.submit_approval(vendor_id, Role.FINANCE, auth.email, payload)


@router.post("/approvals/{vendor_id}/it")
def it_approval(
    vendor_id: str,
    payload: ApprovalDecisionSchema,
    service: VendorOnboardingService = Depends(service_dependency),
    auth=Depends(approver_roles(Role.IT)),
):
    return service.submit_approval(vendor_id, Role.IT, auth.email, payload)


@router.post("/healthcare/approvals/{vendor_id}/compliance")
def compliance_approval(
    vendor_id: str,
    payload: ApprovalDecisionSchema,
    service: VendorOnboardingService = Depends(service_dependency),
    auth=Depends(approver_roles(Role.COMPLIANCE_OFFICER)),
):
    return service.submit_approval(vendor_id, Role.COMPLIANCE_OFFICER, auth.email, payload)
