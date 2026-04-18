from __future__ import annotations

import json

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import StreamingResponse

from backend.api.deps import employee_only, procurement_only, service_dependency
from backend.core.event_bus import broker
from backend.core.services import VendorOnboardingService
from backend.models.requests import HealthcareVendorRequestSchema, VendorRequestSchema


router = APIRouter()


@router.post("/vendor/request")
def create_vendor_request(
    payload: VendorRequestSchema,
    service: VendorOnboardingService = Depends(service_dependency),
    auth=Depends(employee_only),
):
    return service.create_vendor_request(payload, actor_email=auth.email)


@router.post("/healthcare/vendor/request")
def create_healthcare_vendor_request(
    payload: HealthcareVendorRequestSchema,
    service: VendorOnboardingService = Depends(service_dependency),
    auth=Depends(employee_only),
):
    return service.create_vendor_request(
        payload,
        actor_email=auth.email,
        healthcare_endpoint=True,
    )


@router.post("/vendor/invite/{request_id}")
def invite_vendor(
    request_id: str,
    service: VendorOnboardingService = Depends(service_dependency),
    _auth=Depends(procurement_only),
):
    return service.invite_vendor(request_id)


@router.post("/healthcare/vendor/invite/{request_id}")
def invite_healthcare_vendor(
    request_id: str,
    service: VendorOnboardingService = Depends(service_dependency),
    _auth=Depends(procurement_only),
):
    return service.invite_vendor(request_id, healthcare_endpoint=True)


@router.get("/vendor/validate-token/{token}")
def validate_vendor_token(
    token: str,
    service: VendorOnboardingService = Depends(service_dependency),
):
    return service.validate_token(token)


@router.post("/vendor/upload/{token}")
async def upload_vendor_documents_with_token(
    token: str,
    service: VendorOnboardingService = Depends(service_dependency),
    files: list[UploadFile] = File(...),
):
    return await service.upload_documents_with_token(token, files)


@router.post("/healthcare/vendor/upload/{token}")
async def upload_healthcare_documents_with_token(
    token: str,
    service: VendorOnboardingService = Depends(service_dependency),
    files: list[UploadFile] = File(...),
):
    return await service.upload_documents_with_token(token, files, healthcare_endpoint=True)


@router.get("/vendors")
def list_vendors(
    service: VendorOnboardingService = Depends(service_dependency),
    status: str | None = Query(default=None),
):
    return service.list_vendors(status_filter=status)


@router.get("/vendors/{vendor_id}/status")
def get_vendor_status(
    vendor_id: str,
    service: VendorOnboardingService = Depends(service_dependency),
):
    return service.get_vendor_status(vendor_id)


@router.get("/vendors/{vendor_id}/report")
def get_vendor_report(
    vendor_id: str,
    service: VendorOnboardingService = Depends(service_dependency),
):
    return service.get_vendor_report(vendor_id)


@router.get("/vendors/{vendor_id}/events")
async def vendor_events(
    vendor_id: str,
    request: Request,
    service: VendorOnboardingService = Depends(service_dependency),
):
    async def event_stream():
        existing = service.repo.list_events(vendor_id)
        for item in existing[-20:]:
            yield f"data: {json.dumps({'vendor_id': vendor_id, 'event_type': item.event_type, 'data': item.data}, default=str)}\n\n"
        async for item in broker.subscribe(vendor_id):
            if await request.is_disconnected():
                break
            yield f"data: {json.dumps(item, default=str)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/vendors/{vendor_id}/documents")
def get_vendor_documents(
    vendor_id: str,
    service: VendorOnboardingService = Depends(service_dependency),
):
    return service.get_vendor_documents(vendor_id)


@router.post("/vendors/{vendor_id}/documents")
async def upload_vendor_documents(
    vendor_id: str,
    service: VendorOnboardingService = Depends(service_dependency),
    files: list[UploadFile] = File(...),
):
    return await service.upload_documents_for_vendor(vendor_id, files)


@router.get("/vendors/{vendor_id}/security")
def get_vendor_security(
    vendor_id: str,
    service: VendorOnboardingService = Depends(service_dependency),
):
    return service.get_vendor_security(vendor_id)


@router.get("/vendors/{vendor_id}/compliance")
def get_vendor_compliance(
    vendor_id: str,
    service: VendorOnboardingService = Depends(service_dependency),
):
    return service.get_vendor_compliance(vendor_id)


@router.get("/vendors/{vendor_id}/financial")
def get_vendor_financial(
    vendor_id: str,
    service: VendorOnboardingService = Depends(service_dependency),
):
    return service.get_vendor_financial(vendor_id)


@router.get("/vendors/{vendor_id}/risk-assessment")
def get_vendor_risk_assessment(
    vendor_id: str,
    service: VendorOnboardingService = Depends(service_dependency),
):
    return service.get_vendor_risk_assessment(vendor_id)


@router.get("/vendors/{vendor_id}/evidence-gaps")
def get_vendor_evidence_gaps(
    vendor_id: str,
    service: VendorOnboardingService = Depends(service_dependency),
):
    return service.get_vendor_evidence_gaps(vendor_id)


@router.get("/vendors/{vendor_id}/evidence-status")
def get_vendor_evidence_status(
    vendor_id: str,
    service: VendorOnboardingService = Depends(service_dependency),
):
    return service.get_vendor_evidence_status(vendor_id)


@router.post("/vendors/{vendor_id}/request-evidence")
def request_vendor_evidence(
    vendor_id: str,
    service: VendorOnboardingService = Depends(service_dependency),
):
    return service.request_vendor_evidence(vendor_id)


@router.get("/vendors/{vendor_id}/approval-packet")
def get_vendor_approval_packet(
    vendor_id: str,
    service: VendorOnboardingService = Depends(service_dependency),
):
    return service.get_vendor_approval_packet(vendor_id)


@router.get("/vendors/{vendor_id}/approval-workflow")
def get_vendor_approval_workflow(
    vendor_id: str,
    service: VendorOnboardingService = Depends(service_dependency),
):
    return service.get_vendor_approval_workflow(vendor_id)


@router.get("/vendors/{vendor_id}/approvals")
def get_vendor_approval_decisions(
    vendor_id: str,
    service: VendorOnboardingService = Depends(service_dependency),
):
    return service.get_vendor_approval_decisions(vendor_id)


@router.get("/vendors/{vendor_id}/approval-status")
def get_vendor_approval_status(
    vendor_id: str,
    service: VendorOnboardingService = Depends(service_dependency),
):
    return service.get_vendor_approval_status(vendor_id)


@router.get("/vendors/{vendor_id}/audit-trail")
def get_vendor_audit_trail(
    vendor_id: str,
    service: VendorOnboardingService = Depends(service_dependency),
):
    return service.get_vendor_audit_trail(vendor_id)


@router.post("/vendors/onboard")
async def onboard_from_prompt(
    service: VendorOnboardingService = Depends(service_dependency),
    prompt: str = Form(...),
    files: list[UploadFile] | None = File(default=None),
):
    result = service.onboard_from_prompt(prompt)
    if files:
        await service.upload_documents_for_vendor(result["vendor_id"], files)
    return result
