from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Sequence
from uuid import uuid4

from fastapi import HTTPException, UploadFile

from backend.agents.supervisor import build_supervisor_graph, route_by_ephi
from backend.compliance.baa_parser import analyze_baa
from backend.compliance.ephi import analyze_ephi_flow
from backend.core.config import get_settings
from backend.core.event_bus import broker
from backend.core.metrics import (
    CONTINUAL_MODEL_ACCURACY,
    HIPAA_CHECK_RESULTS,
    WORKER_THROUGHPUT,
)
from backend.core.repository import RepositoryType, get_repository
from backend.core.telemetry import trace_span
from backend.learning.bayesian import calculate_bayesian_score
from backend.learning.continual import update_online_model
from backend.learning.federated import prepare_federated_update
from backend.learning.rl import build_state_vector, predict_risk_tier, reward_for_outcome
from backend.models.domain import (
    ApprovalDecisionRecord,
    ApprovalWorkflowRecord,
    BAARecord,
    BayesianScoreRecord,
    EPHIAccessLogRecord,
    HipaaVerificationRecord,
    ModelVersionRecord,
    NotificationLogRecord,
    OnboardingTokenRecord,
    RLTrainingEpisodeRecord,
    RiskAssessmentRecord,
    RiskModelFeedbackRecord,
    ScheduledTaskRecord,
    VendorDocumentRecord,
    VendorEmbeddingRecord,
    VendorRecord,
    VendorRequestRecord,
    VerificationResultRecord,
    WorkflowEventRecord,
)
from backend.models.enums import (
    ApprovalDecisionType,
    RiskTier,
    Role,
    VerificationKind,
    VerificationStatus,
    VendorStatusEnum,
    WorkflowType,
)
from backend.models.requests import (
    ApprovalDecisionSchema,
    HealthcareChatRequest,
    HealthcareVendorRequestSchema,
    VendorRequestSchema,
)
from backend.rag.service import query_compliance_knowledge
from backend.tools.comply_advantage import check_sanctions
from backend.tools.decentro import verify_bank_account
from backend.tools.oig import check_oig
from backend.tools.openai_client import classify_document, generate_embedding_vector
from backend.tools.signzy import verify_gst
from backend.tools.surepass import verify_pan


SAAS_REQUIRED_DOCUMENTS = [
    "GST Certificate",
    "PAN Card",
    "Incorporation Certificate",
    "Cancelled Cheque",
    "SOC 2 Type II",
    "ISO 27001",
    "Penetration Test Report",
    "NDA",
]
HEALTHCARE_REQUIRED_DOCUMENTS = SAAS_REQUIRED_DOCUMENTS[:4] + [
    "HIPAA Attestation",
    "BAA",
    "SOC 2 Type II",
    "ePHI Data Flow Map",
    "Subprocessor List",
    "Cyber Insurance",
    "Breach Policy",
]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _risk_label(score: float) -> str:
    if score >= 85:
        return "Low Risk"
    if score >= 65:
        return "Moderate Risk"
    return "High Risk"


def _normalize_string(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _verification_label(kind: VerificationKind) -> str:
    labels = {
        VerificationKind.GST: "GST Verification",
        VerificationKind.PAN: "PAN Verification",
        VerificationKind.BANK: "Bank Validation",
        VerificationKind.MCA: "MCA Verification",
        VerificationKind.SANCTIONS: "Sanctions Check",
        VerificationKind.SOC2: "SOC 2 Review",
        VerificationKind.OIG: "OIG Exclusion Check",
        VerificationKind.HEALTHCARE_SANCTIONS: "Healthcare Sanctions Check",
        VerificationKind.BAA: "BAA Clause Analysis",
        VerificationKind.HIPAA_ATTESTATION: "HIPAA Attestation",
        VerificationKind.EPHI_FLOW: "ePHI Flow Analysis",
        VerificationKind.SUBPROCESSORS: "Subprocessor Coverage",
    }
    return labels.get(kind, kind.value.replace("_", " ").upper())


def _required_documents(workflow_type: WorkflowType) -> list[str]:
    return (
        HEALTHCARE_REQUIRED_DOCUMENTS
        if workflow_type == WorkflowType.HEALTHCARE
        else SAAS_REQUIRED_DOCUMENTS
    )


def _extract_company_domain(email: str) -> str | None:
    if "@" not in email:
        return None
    return email.split("@", 1)[1].lower()


def _extract_text(file_name: str, content: bytes) -> str:
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        try:
            return content.decode("latin-1")
        except UnicodeDecodeError:
            return f"binary file uploaded: {file_name}"


def _extract_dates(text: str) -> dict[str, Any]:
    regex_dates = re.findall(r"\b\d{4}-\d{2}-\d{2}\b|\b\d{2}/\d{2}/\d{4}\b", text)
    return {
        "regex_dates": regex_dates[:10],
        "llm_dates": {
            "expiration_dates": regex_dates[:2],
            "effective_dates": regex_dates[2:4],
        },
    }


def _extract_metadata(text: str, vendor_name: str, contact_email: str) -> dict[str, Any]:
    pan_match = re.search(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", text.upper())
    gst_match = re.search(r"\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]Z[0-9A-Z]\b", text.upper())
    bank_match = re.search(r"\b\d{9,18}\b", text)
    return {
        "vendor_name": vendor_name,
        "contact_email": contact_email,
        "pan": pan_match.group(0) if pan_match else None,
        "gst": gst_match.group(0) if gst_match else None,
        "bank_account": bank_match.group(0) if bank_match else None,
    }


@dataclass(slots=True)
class ParsedFileResult:
    file_name: str
    file_size: int
    text: str
    classification: str
    confidence: float
    metadata: dict[str, Any]
    dates: dict[str, Any]


class VendorOnboardingService:
    def __init__(self, repo: RepositoryType) -> None:
        self.repo = repo

    async def emit_event(self, vendor_id: str, event_type: str, data: dict[str, Any]) -> None:
        record = WorkflowEventRecord(vendor_id=vendor_id, event_type=event_type, data=data)
        self.repo.add_event(record)
        await broker.publish(
            vendor_id,
            {
                "vendor_id": vendor_id,
                "event_type": event_type,
                "data": data,
            },
        )

    def dispatch_event(self, vendor_id: str, event_type: str, data: dict[str, Any]) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(self.emit_event(vendor_id, event_type, data))
        else:
            loop.create_task(self.emit_event(vendor_id, event_type, data))

    def _vendor_summary(self, vendor: VendorRecord) -> dict[str, Any]:
        return {
            "id": vendor.id,
            "name": vendor.name,
            "vendor_type": vendor.vendor_type or vendor.service_type,
            "status": vendor.status.value.lower(),
            "contract_value": vendor.contract_value,
            "domain": vendor.domain,
            "contact_email": vendor.contact_email,
            "created_at": vendor.created_at,
            "updated_at": vendor.updated_at,
            "overall_risk_score": vendor.overall_risk_score,
            "risk_level": vendor.risk_level,
            "approval_tier": vendor.approval_tier,
            "approval_status": vendor.approval_status,
            "workflow_type": vendor.workflow_type.value,
        }

    def _serialize_verification(
        self,
        item: VerificationResultRecord | HipaaVerificationRecord,
    ) -> dict[str, Any]:
        return {
            "id": item.id,
            "kind": item.kind.value,
            "label": _verification_label(item.kind),
            "result": item.result,
            "status": item.status.value,
            "confidence_score": item.confidence_score,
            "details": item.details,
            "agent_name": item.agent_name,
            "queue_name": item.queue_name,
            "created_at": item.created_at,
        }

    def list_vendors(self, status_filter: str | None = None) -> dict[str, Any]:
        vendors = self.repo.list_vendors()
        if status_filter:
            wanted = status_filter.lower()
            vendors = [item for item in vendors if wanted in item.status.value.lower()]
        return {
            "total": len(vendors),
            "vendors": [self._vendor_summary(item) for item in vendors],
        }

    def create_vendor_request(
        self,
        payload: VendorRequestSchema | HealthcareVendorRequestSchema,
        actor_email: str,
        healthcare_endpoint: bool = False,
    ) -> dict[str, Any]:
        workflow_type = route_by_ephi(
            getattr(payload, "ephi_involved", False) and healthcare_endpoint
        )
        ephi_involved = workflow_type == WorkflowType.HEALTHCARE
        existing = next(
            (
                vendor
                for vendor in self.repo.list_vendors()
                if _normalize_string(vendor.name) == _normalize_string(payload.vendor_name)
                and vendor.contact_email.lower() == payload.contact_email.lower()
            ),
            None,
        )
        if existing:
            return {
                "status": "existing",
                "request_id": existing.request_id or existing.id,
                "vendor_id": existing.id,
                "workflow_type": existing.workflow_type.value,
                "message": f"Vendor {existing.name} already exists.",
            }

        request_record = VendorRequestRecord(
            employee_email=actor_email,
            vendor_name=payload.vendor_name,
            service_type=payload.service_type,
            reason=payload.reason,
            contract_value=payload.contract_value,
            contact_email=payload.contact_email,
            workflow_type=workflow_type,
            ephi_involved=ephi_involved,
            ephi_types=getattr(payload, "ephi_types", []),
            hipaa_required=ephi_involved,
            status=(
                VendorStatusEnum.HIPAA_REVIEW_TRIGGERED
                if ephi_involved
                else VendorStatusEnum.PENDING_REVIEW
            ),
        )
        self.repo.create_vendor_request(request_record)

        vendor = VendorRecord(
            request_id=request_record.id,
            name=payload.vendor_name,
            service_type=payload.service_type,
            workflow_type=workflow_type,
            status=request_record.status,
            contract_value=payload.contract_value,
            contact_email=payload.contact_email,
            domain=_extract_company_domain(payload.contact_email),
            vendor_type=payload.service_type,
            current_phase="intake",
            current_agent="intake_agent",
            current_step="request_received",
            progress_percentage=10.0,
            checklist_required=len(_required_documents(workflow_type)),
            ephi_involved=ephi_involved,
            ephi_types=getattr(payload, "ephi_types", []),
        )
        self.repo.create_vendor(vendor)
        request_record.vendor_id = vendor.id
        self.repo.update_vendor_request(request_record)

        recipients = ["procurement@hackstrom.local"]
        if ephi_involved:
            recipients.append("compliance@hackstrom.local")
        for recipient in recipients:
            self.repo.add_notification(
                NotificationLogRecord(
                    vendor_id=vendor.id,
                    request_id=request_record.id,
                    recipient=recipient,
                    template="vendor_intake_received",
                    subject=f"Vendor request received for {vendor.name}",
                    status="queued",
                    payload={"workflow_type": workflow_type.value},
                )
            )
        self.dispatch_event(
            vendor.id,
            "status_change",
            {
                "status": vendor.status.value,
                "workflow_type": workflow_type.value,
                "graph": build_supervisor_graph(),
            },
        )
        return {
            "status": vendor.status.value.lower(),
            "request_id": request_record.id,
            "vendor_id": vendor.id,
            "workflow_type": workflow_type.value,
            "message": (
                "Healthcare workflow triggered through the ePHI gate."
                if ephi_involved
                else "Vendor request submitted successfully."
            ),
        }

    def invite_vendor(self, request_id: str, healthcare_endpoint: bool = False) -> dict[str, Any]:
        request_record = self.repo.get_vendor_request(request_id)
        if not request_record or not request_record.vendor_id:
            raise HTTPException(status_code=404, detail="Vendor request not found")
        vendor = self.repo.get_vendor(request_record.vendor_id)
        if not vendor:
            raise HTTPException(status_code=404, detail="Vendor not found")
        if healthcare_endpoint and vendor.workflow_type != WorkflowType.HEALTHCARE:
            raise HTTPException(status_code=400, detail="Vendor is not in healthcare workflow")
        if not healthcare_endpoint and vendor.workflow_type != WorkflowType.SAAS:
            raise HTTPException(status_code=400, detail="Vendor belongs to healthcare workflow")

        expires_at = _utcnow() + timedelta(days=10 if healthcare_endpoint else 7)
        token_value = str(uuid4())
        token = OnboardingTokenRecord(
            vendor_id=vendor.id,
            request_id=request_id,
            workflow_type=vendor.workflow_type,
            token=token_value,
            expires_at=expires_at,
        )
        self.repo.create_onboarding_token(token)
        vendor.status = VendorStatusEnum.INVITATION_SENT
        vendor.current_phase = "invitation"
        vendor.current_step = "vendor_invited"
        vendor.progress_percentage = 20.0
        self.repo.update_vendor(vendor)
        checklist_count = len(_required_documents(vendor.workflow_type))
        portal_path = (
            "/vendor/healthcare/register"
            if vendor.workflow_type == WorkflowType.HEALTHCARE
            else "/vendor/register"
        )
        portal_url = f"{portal_path}?token={token_value}"
        notification_portal_url = f"{get_settings().frontend_url}{portal_url}"
        self.repo.add_notification(
            NotificationLogRecord(
                vendor_id=vendor.id,
                request_id=request_id,
                recipient=vendor.contact_email,
                template=(
                    "send_hipaa_invitation_email"
                    if vendor.workflow_type == WorkflowType.HEALTHCARE
                    else "send_invitation_email"
                ),
                subject=(
                    f"Action Required: HIPAA Vendor Onboarding for {vendor.name}"
                    if vendor.workflow_type == WorkflowType.HEALTHCARE
                    else f"Action Required: Complete Vendor Onboarding for {vendor.name}"
                ),
                status="queued",
                payload={"portal_url": portal_url, "checklist_count": checklist_count},
            )
        )
        from backend.tasks.notifications import (
            send_hipaa_invitation_email_task,
            send_invitation_email_task,
        )

        if vendor.workflow_type == WorkflowType.HEALTHCARE:
            send_hipaa_invitation_email_task.delay(
                vendor.id,
                vendor.contact_email,
                notification_portal_url,
                checklist_count,
            )
        else:
            send_invitation_email_task.delay(
                vendor.id,
                vendor.contact_email,
                notification_portal_url,
                checklist_count,
            )
        self.dispatch_event(
            vendor.id,
            "approval_required",
            {"step": "vendor_submission", "portal_url": portal_url},
        )
        return {
            "status": "invited",
            "token": token_value,
            "portal_url": portal_url,
            "expires_at": expires_at,
            "checklist_count": checklist_count,
        }

    def validate_token(self, token_value: str) -> dict[str, Any]:
        token = self.repo.get_onboarding_token(token_value)
        if not token or token.expires_at < _utcnow():
            return {"valid": False}
        vendor = self.repo.get_vendor(token.vendor_id)
        return {
            "valid": True,
            "vendor_id": token.vendor_id,
            "workflow_type": token.workflow_type.value,
            "expires_at": token.expires_at,
            "documents_required": len(_required_documents(token.workflow_type)),
            "vendor_name": vendor.name if vendor else None,
        }

    def _parse_file(
        self,
        file_name: str,
        content: bytes,
        vendor_name: str,
        contact_email: str,
    ) -> ParsedFileResult:
        text = _extract_text(file_name, content)
        classification = classify_document(file_name, text)
        metadata = _extract_metadata(text, vendor_name, contact_email)
        dates = _extract_dates(text)
        return ParsedFileResult(
            file_name=file_name,
            file_size=len(content),
            text=text,
            classification=classification.classification,
            confidence=classification.confidence,
            metadata=metadata,
            dates=dates,
        )

    async def parse_documents(
        self,
        files: Sequence[UploadFile],
        vendor: VendorRecord | None = None,
    ) -> dict[str, Any]:
        results = []
        vendor_name = vendor.name if vendor else "Unknown Vendor"
        contact_email = vendor.contact_email if vendor else "unknown@example.com"
        for upload in files:
            content = await upload.read()
            parsed = self._parse_file(upload.filename or "document", content, vendor_name, contact_email)
            results.append(
                {
                    "file_name": parsed.file_name,
                    "file_size": parsed.file_size,
                    "status": "completed",
                    "steps": {
                        "parse": {
                            "status": "success",
                            "text": parsed.text[:1000],
                            "num_pages": 1,
                            "has_tables": False,
                        },
                        "classify": {
                            "status": "success",
                            "classification": parsed.classification,
                            "confidence": parsed.confidence,
                            "reasoning": "Heuristic classifier",
                        },
                        "metadata": {
                            "status": "success",
                            "metadata": parsed.metadata,
                        },
                        "dates": {
                            "status": "success",
                            **parsed.dates,
                        },
                    },
                }
            )
        return {"status": "completed", "total_files": len(results), "results": results}

    async def upload_documents_with_token(
        self,
        token_value: str,
        files: Sequence[UploadFile],
        healthcare_endpoint: bool = False,
    ) -> dict[str, Any]:
        token = self.repo.get_onboarding_token(token_value)
        if not token:
            raise HTTPException(status_code=404, detail="Invalid token")
        if token.expires_at < _utcnow():
            raise HTTPException(status_code=410, detail="Token expired")
        vendor = self.repo.get_vendor(token.vendor_id)
        if not vendor:
            raise HTTPException(status_code=404, detail="Vendor not found")
        if healthcare_endpoint and vendor.workflow_type != WorkflowType.HEALTHCARE:
            raise HTTPException(status_code=400, detail="Healthcare token required")
        return await self._persist_uploaded_documents(vendor, files)

    async def upload_documents_for_vendor(
        self,
        vendor_id: str,
        files: Sequence[UploadFile],
    ) -> dict[str, Any]:
        vendor = self.repo.get_vendor(vendor_id)
        if not vendor:
            raise HTTPException(status_code=404, detail="Vendor not found")
        return await self._persist_uploaded_documents(vendor, files)

    async def _persist_uploaded_documents(
        self,
        vendor: VendorRecord,
        files: Sequence[UploadFile],
    ) -> dict[str, Any]:
        saved_ids: list[str] = []
        with trace_span("document_upload", vendor_id=vendor.id):
            for upload in files:
                content = await upload.read()
                parsed = self._parse_file(upload.filename or "document", content, vendor.name, vendor.contact_email)
                record = VendorDocumentRecord(
                    vendor_id=vendor.id,
                    file_name=parsed.file_name,
                    file_type=(Path(parsed.file_name).suffix or ".bin").lstrip("."),
                    document_type=parsed.classification,
                    classification=parsed.classification,
                    classification_confidence=parsed.confidence,
                    processing_status="processed",
                    extracted_text=parsed.text,
                    extracted_metadata=parsed.metadata,
                    extracted_dates=parsed.dates,
                )
                self.repo.create_document(record)
                saved_ids.append(record.id)
                self.repo.upsert_embedding(
                    VendorEmbeddingRecord(
                        vendor_id=vendor.id,
                        document_id=record.id,
                        doc_type=record.document_type or "unknown",
                        dimensions=1536,
                        vector=generate_embedding_vector(record.extracted_text),
                    )
                )
                await self.emit_event(
                    vendor.id,
                    "agent_complete",
                    {
                        "agent": "document_ingestion",
                        "document_id": record.id,
                        "classification": record.classification,
                    },
                )

        documents = self.repo.list_documents(vendor.id)
        received_types = {item.classification for item in documents if item.classification}
        required = _required_documents(vendor.workflow_type)
        missing = [item for item in required if item not in received_types]
        vendor.checklist_received = len(received_types)
        vendor.progress_percentage = min(55.0, 20.0 + (vendor.checklist_received / len(required)) * 35.0)
        vendor.current_phase = "document_collection"
        vendor.current_step = "documents_uploaded"
        if not missing:
            vendor.status = VendorStatusEnum.DOCUMENTS_SUBMITTED
            vendor.current_phase = "verification"
            vendor.current_agent = "verification_supervisor"
            vendor.progress_percentage = 60.0
            self.repo.update_vendor(vendor)
            await self.emit_event(
                vendor.id,
                "status_change",
                {"status": vendor.status.value, "documents_complete": True},
            )
            self.run_verification_pipeline(vendor.id)
        else:
            self.repo.update_vendor(vendor)

        return {
            "status": "accepted",
            "vendor_id": vendor.id,
            "documents_received": vendor.checklist_received,
            "documents_required": len(required),
            "missing": missing,
            "document_ids": saved_ids,
        }

    def _verify_mca(self, vendor: VendorRecord, raw_text: str):
        age = 5 if "incorporated" in raw_text.lower() else 2
        return type(
            "Result",
            (),
            {
                "result": "verified",
                "confidence_score": 0.82,
                "details": {
                    "directors": [f"{vendor.name} Director"],
                    "company_age_years": age,
                    "status": "active",
                },
            },
        )()

    def _parse_soc2(self, document: VendorDocumentRecord | None):
        text = document.extracted_text.lower() if document else ""
        type_label = "Type II" if "type ii" in text or document else "Unknown"
        return type(
            "Result",
            (),
            {
                "result": "verified" if document else "failed",
                "confidence_score": 0.88 if document else 0.35,
                "details": {
                    "audit_type": type_label,
                    "expiry_date": _utcnow().date().isoformat(),
                    "auditing_firm": "Heuristic Audit LLP",
                    "failed_controls": [] if document else ["Missing SOC 2 report"],
                },
            },
        )()

    def _run_healthcare_verifications(
        self,
        vendor: VendorRecord,
        docs_by_type: dict[str, VendorDocumentRecord],
        raw_text: str,
    ):
        baa_doc = docs_by_type.get("BAA")
        baa_analysis = analyze_baa(baa_doc.extracted_text if baa_doc else "")
        if baa_doc:
            self.repo.upsert_baa_record(
                BAARecord(
                    vendor_id=vendor.id,
                    status=baa_analysis.status,
                    confidence_score=baa_analysis.confidence_score,
                    clauses=baa_analysis.clauses,
                    clauses_missing=baa_analysis.missing,
                    expiry_date=(_utcnow() + timedelta(days=365)).date().isoformat(),
                )
            )
        ephi_doc = docs_by_type.get("ePHI Data Flow Map")
        flow = analyze_ephi_flow(ephi_doc.extracted_text if ephi_doc else "")
        oig = check_oig([vendor.name])
        return [
            (
                VerificationKind.OIG,
                oig,
                "OIG Exclusion Check",
            ),
            (
                VerificationKind.HEALTHCARE_SANCTIONS,
                check_sanctions([vendor.name], healthcare=True),
                "Healthcare Sanctions Check",
            ),
            (
                VerificationKind.BAA,
                type(
                    "Result",
                    (),
                    {
                        "result": baa_analysis.status,
                        "confidence_score": baa_analysis.confidence_score,
                        "details": {
                            "clauses_present": [
                                key for key, value in baa_analysis.clauses.items() if value["present"]
                            ],
                            "clauses_missing": baa_analysis.missing,
                        },
                    },
                )(),
                "BAA Parser",
            ),
            (
                VerificationKind.HIPAA_ATTESTATION,
                type(
                    "Result",
                    (),
                    {
                        "result": "valid" if docs_by_type.get("HIPAA Attestation") else "invalid",
                        "confidence_score": 0.9 if docs_by_type.get("HIPAA Attestation") else 0.35,
                        "details": {
                            "year": _utcnow().year,
                            "signatory": f"{vendor.name} Compliance Lead",
                            "safeguards": ["administrative", "physical", "technical"],
                        },
                    },
                )(),
                "HIPAA Attestation Validator",
            ),
            (
                VerificationKind.EPHI_FLOW,
                type(
                    "Result",
                    (),
                    {
                        "result": flow.result,
                        "confidence_score": flow.confidence_score,
                        "details": {
                            "risks": flow.risks,
                            "encryption_verified": flow.encryption_verified,
                            "jurisdiction_verified": flow.jurisdiction_verified,
                        },
                    },
                )(),
                "ePHI Data Flow Analyzer",
            ),
            (
                VerificationKind.SUBPROCESSORS,
                type(
                    "Result",
                    (),
                    {
                        "result": "all_covered" if "subprocessor" in raw_text.lower() else "gaps_found",
                        "confidence_score": 0.82 if "subprocessor" in raw_text.lower() else 0.48,
                        "details": {
                            "subprocessors": ["AWS", "SendGrid"] if "subprocessor" in raw_text.lower() else [],
                            "gaps": [] if "subprocessor" in raw_text.lower() else ["Subprocessor clause missing"],
                        },
                    },
                )(),
                "Subprocessor Coverage Agent",
            ),
        ]

    def run_verification_pipeline(self, vendor_id: str) -> None:
        if not get_settings().celery_task_always_eager:
            from backend.tasks.verification import run_vendor_verification

            run_vendor_verification.delay(vendor_id)
            return
        self._run_verification_pipeline_sync(vendor_id)

    def _run_verification_pipeline_sync(self, vendor_id: str) -> None:
        vendor = self.repo.get_vendor(vendor_id)
        if not vendor:
            raise HTTPException(status_code=404, detail="Vendor not found")
        vendor.status = VendorStatusEnum.VERIFICATION_IN_PROGRESS
        vendor.current_phase = "verification"
        vendor.current_agent = "verification_supervisor"
        self.repo.update_vendor(vendor)
        documents = self.repo.list_documents(vendor_id)
        docs_by_type = {doc.classification or doc.document_type or "Unknown": doc for doc in documents}

        self.dispatch_event(vendor_id, "verification_started", {"workflow_type": vendor.workflow_type.value})

        standard_results: list[VerificationResultRecord] = []
        raw_text = "\n".join(doc.extracted_text for doc in documents)
        verification_jobs = [
            (VerificationKind.GST, verify_gst(raw_text, vendor.name), "GST Verification"),
            (VerificationKind.PAN, verify_pan(raw_text, vendor.name), "PAN Verification"),
            (VerificationKind.BANK, verify_bank_account(raw_text, vendor.name), "Bank Validation"),
            (VerificationKind.MCA, self._verify_mca(vendor, raw_text), "MCA Verification"),
            (VerificationKind.SANCTIONS, check_sanctions([vendor.name]), "Sanctions Check"),
            (VerificationKind.SOC2, self._parse_soc2(docs_by_type.get("SOC 2 Type II")), "SOC 2 Parser"),
        ]
        for kind, result, agent_name in verification_jobs:
            record = VerificationResultRecord(
                vendor_id=vendor.id,
                kind=kind,
                workflow_type=vendor.workflow_type,
                status=(
                    VerificationStatus.FLAGGED
                    if result.result in {"flagged", "excluded"}
                    else VerificationStatus.SUCCESS
                ),
                result=result.result,
                confidence_score=result.confidence_score,
                details=result.details,
                agent_name=agent_name,
                queue_name="verification_queue",
            )
            self.repo.upsert_verification(record)
            standard_results.append(record)
            WORKER_THROUGHPUT.labels(worker_name="worker-1", queue_name="verification_queue").inc()

        hipaa_results: list[HipaaVerificationRecord] = []
        if vendor.workflow_type == WorkflowType.HEALTHCARE:
            hipaa_jobs = self._run_healthcare_verifications(vendor, docs_by_type, raw_text)
            for kind, result, agent_name in hipaa_jobs:
                record = HipaaVerificationRecord(
                    vendor_id=vendor.id,
                    kind=kind,
                    workflow_type=vendor.workflow_type,
                    status=(
                        VerificationStatus.FLAGGED
                        if result.result in {"flagged", "excluded", "non_compliant", "invalid", "gaps_found"}
                        else VerificationStatus.SUCCESS
                    ),
                    result=result.result,
                    confidence_score=result.confidence_score,
                    details=result.details,
                    agent_name=agent_name,
                    queue_name="hipaa_check_queue",
                )
                self.repo.upsert_verification(record, hipaa=True)
                hipaa_results.append(record)
                HIPAA_CHECK_RESULTS.labels(check_name=kind.value, result=result.result).inc()
                WORKER_THROUGHPUT.labels(worker_name="worker-1", queue_name="hipaa_check_queue").inc()
                self.dispatch_event(
                    vendor.id,
                    "hipaa_check_complete",
                    {
                        "agent": agent_name,
                        "status": record.result,
                        "confidence": record.confidence_score,
                    },
                )

        self._complete_risk_and_approval(vendor, standard_results, hipaa_results)

    def _ensure_approval_workflow(self, vendor: VendorRecord) -> ApprovalWorkflowRecord:
        existing = self.repo.get_approval(vendor.id)
        if existing:
            return existing
        approvers = [
            {"role": "legal", "label": "Legal"},
            {"role": "finance", "label": "Finance"},
            {"role": "it", "label": "IT"},
        ]
        if vendor.workflow_type == WorkflowType.HEALTHCARE:
            approvers.append({"role": "compliance_officer", "label": "Compliance Officer"})
        deadline = _utcnow() + timedelta(
            days=7 if vendor.approval_tier == RiskTier.TIER_3.value else 14
        )
        approval = ApprovalWorkflowRecord(
            vendor_id=vendor.id,
            workflow_type=vendor.workflow_type,
            status="pending",
            approval_tier=vendor.approval_tier or RiskTier.TIER_2.value,
            required_approvers=approvers,
            current_step_role=approvers[0]["role"],
            completion_percentage=0.0,
            deadline=deadline,
        )
        return self.repo.upsert_approval(approval)

    def _complete_risk_and_approval(
        self,
        vendor: VendorRecord,
        standard_results: list[VerificationResultRecord],
        hipaa_results: list[HipaaVerificationRecord],
    ) -> None:
        hard_overrides: list[str] = []
        scores: list[tuple[str, float, float]] = []
        for item in standard_results:
            scores.append((item.kind.value, item.confidence_score, 1.0))
            if item.kind == VerificationKind.SANCTIONS and item.result == "flagged":
                hard_overrides.append("Sanctions flagged")
        for item in hipaa_results:
            scores.append((item.kind.value, item.confidence_score, 2.0))
            if item.kind == VerificationKind.OIG and item.result == "excluded":
                hard_overrides.append("OIG excluded")
            if item.kind == VerificationKind.EPHI_FLOW and item.details.get("jurisdiction_verified") is False:
                hard_overrides.append("ePHI jurisdiction violation")
        baa_record = self.repo.get_baa_record(vendor.id)
        if baa_record and "breach_notification_60_days" in baa_record.clauses_missing:
            hard_overrides.append("BAA missing breach notification clause")

        bayesian = calculate_bayesian_score(
            scores,
            healthcare=vendor.workflow_type == WorkflowType.HEALTHCARE,
            hard_overrides=hard_overrides,
        )
        self.repo.upsert_bayesian_score(
            BayesianScoreRecord(
                vendor_id=vendor.id,
                workflow_type=vendor.workflow_type,
                probability_legitimate=bayesian.probability_legitimate,
                probability_fraud=bayesian.probability_fraud,
                confidence_interval=bayesian.confidence_interval,
                risk_tier=bayesian.risk_tier,
                evidence_explanation=bayesian.evidence_explanation,
                hard_override=bayesian.hard_override,
                hipaa_overrides=bayesian.hipaa_overrides,
                hipaa_risk_factors=bayesian.hipaa_risk_factors,
            )
        )

        state_inputs = [item.confidence_score for item in standard_results]
        if vendor.workflow_type == WorkflowType.HEALTHCARE:
            state_inputs.extend(item.confidence_score for item in hipaa_results)
        state_vector = build_state_vector(
            state_inputs + [0.9] * 13,
            healthcare=vendor.workflow_type == WorkflowType.HEALTHCARE,
        )
        rl_prediction = predict_risk_tier(
            state_vector,
            healthcare=vendor.workflow_type == WorkflowType.HEALTHCARE,
        )
        models_agree = rl_prediction.tier == bayesian.risk_tier
        risk_score = round(bayesian.probability_legitimate * 100, 2)
        risk_record = RiskAssessmentRecord(
            vendor_id=vendor.id,
            workflow_type=vendor.workflow_type,
            bayesian_tier=bayesian.risk_tier,
            rl_tier=rl_prediction.tier,
            models_agree=models_agree,
            confidence_indicator="green" if models_agree else "yellow",
            overall_risk_score=risk_score,
            risk_level=_risk_label(risk_score),
            approval_tier=bayesian.risk_tier,
            executive_summary=(
                f"Bayesian tier {bayesian.risk_tier}; RL tier {rl_prediction.tier}; "
                f"{'agreement' if models_agree else 'disagreement'} across models."
            ),
            critical_blockers=hard_overrides,
            conditional_items=[
                explanation
                for explanation in bayesian.evidence_explanation
                if explanation.startswith(("pan", "gst", "bank", "soc2"))
            ],
            mitigation_recommendations=[
                {
                    "description": "Collect missing evidence",
                    "implementation": "Request updated documents and remediation artifacts",
                }
            ],
            state_vector=state_vector,
        )
        self.repo.upsert_risk_assessment(risk_record)

        self.repo.add_model_version(
            ModelVersionRecord(
                model_name="risk_rl_model",
                version="v1",
                workflow_type=vendor.workflow_type,
                accuracy=rl_prediction.confidence,
                metadata={"mode": "heuristic", "models_agree": models_agree},
            )
        )

        vendor.overall_risk_score = risk_record.overall_risk_score
        vendor.risk_level = risk_record.risk_level
        vendor.approval_tier = risk_record.approval_tier
        vendor.approval_status = "pending"
        vendor.status = (
            VendorStatusEnum.REJECTED
            if bayesian.risk_tier == RiskTier.AUTO_REJECT.value
            else VendorStatusEnum.PENDING_APPROVAL
        )
        vendor.current_phase = "approval"
        vendor.current_agent = "approval_router"
        vendor.current_step = "legal"
        vendor.progress_percentage = 80.0
        self.repo.update_vendor(vendor)

        approval = self._ensure_approval_workflow(vendor)
        vendor.approval_id = approval.id
        self.repo.update_vendor(vendor)

        if vendor.workflow_type == WorkflowType.HEALTHCARE:
            update = update_online_model(
                state_vector,
                "rejected" if hard_overrides else "approved",
            )
            CONTINUAL_MODEL_ACCURACY.set(update.accuracy)
            self.repo.add_model_version(
                ModelVersionRecord(
                    model_name="continual_logreg",
                    version="v1-online",
                    workflow_type=vendor.workflow_type,
                    accuracy=update.accuracy,
                    metadata={"alerts": update.alerts},
                )
            )
            self.repo.add_model_version(
                ModelVersionRecord(
                    model_name="federated_round",
                    version=prepare_federated_update(state_vector).round_id,
                    workflow_type=vendor.workflow_type,
                    metadata={"noise_applied": True},
                )
            )

        self.dispatch_event(
            vendor.id,
            "verification_complete",
            {
                "risk_tier": risk_record.approval_tier,
                "overall_risk_score": risk_record.overall_risk_score,
                "approval_status": vendor.approval_status,
            },
        )

    def get_vendor_status(self, vendor_id: str) -> dict[str, Any]:
        vendor = self.repo.get_vendor(vendor_id)
        if not vendor:
            raise HTTPException(status_code=404, detail="Vendor not found")
        return {
            "vendor_id": vendor.id,
            "vendor_name": vendor.name,
            "vendor_type": vendor.vendor_type or vendor.service_type,
            "vendor_domain": vendor.domain,
            "contract_value": vendor.contract_value,
            "contact_email": vendor.contact_email,
            "status": vendor.status.value.lower(),
            "current_phase": vendor.current_phase,
            "current_agent": vendor.current_agent,
            "current_step": vendor.current_step,
            "progress_percentage": vendor.progress_percentage,
            "errors": vendor.errors,
            "agent_errors": vendor.agent_errors,
            "has_errors": bool(vendor.errors or vendor.agent_errors),
            "overall_risk_score": vendor.overall_risk_score,
            "risk_level": vendor.risk_level,
            "approval_tier": vendor.approval_tier,
            "approval_status": vendor.approval_status,
            "approval_id": vendor.approval_id,
            "workflow_type": vendor.workflow_type.value,
            "ephi_involved": vendor.ephi_involved,
        }

    def get_vendor_documents(self, vendor_id: str) -> dict[str, Any]:
        vendor = self.repo.get_vendor(vendor_id)
        if not vendor:
            raise HTTPException(status_code=404, detail="Vendor not found")
        documents = self.repo.list_documents(vendor_id)
        return {
            "vendor_id": vendor_id,
            "vendor_name": vendor.name,
            "total_documents": len(documents),
            "documents": [
                {
                    "id": item.id,
                    "file_name": item.file_name,
                    "file_type": item.file_type,
                    "classification": item.classification,
                    "classification_confidence": item.classification_confidence,
                    "extracted_metadata": item.extracted_metadata,
                    "extracted_dates": item.extracted_dates,
                    "processing_status": item.processing_status,
                    "created_at": item.created_at,
                }
                for item in documents
            ],
        }

    def _review_payload(self, vendor_id: str, category: str) -> dict[str, Any]:
        vendor = self.repo.get_vendor(vendor_id)
        if not vendor:
            raise HTTPException(status_code=404, detail="Vendor not found")
        verifications = self.repo.list_verifications(vendor_id)
        hipaa = self.repo.list_verifications(vendor_id, hipaa=True)
        if category == "security":
            relevant = [
                item
                for item in verifications
                if item.kind in {VerificationKind.SOC2, VerificationKind.SANCTIONS}
            ]
            payload = {
                "status": "completed" if relevant else "pending",
                "overall_score": round(
                    sum(item.confidence_score for item in relevant) / max(1, len(relevant)) * 100
                ),
                "grade": "A" if all(item.confidence_score >= 0.85 for item in relevant) else "B",
                "critical_issues": [
                    "Sanctions or SOC 2 issue requires remediation"
                    for item in relevant
                    if item.result in {"flagged", "failed"}
                ],
                "report": {item.kind.value: item.details for item in relevant},
            }
        elif category == "compliance":
            relevant = (
                hipaa
                if vendor.workflow_type == WorkflowType.HEALTHCARE
                else [item for item in verifications if item.kind == VerificationKind.MCA]
            )
            payload = {
                "status": "completed" if relevant else "pending",
                "overall_score": round(
                    sum(item.confidence_score for item in relevant) / max(1, len(relevant)) * 100
                ),
                "grade": "A" if all(item.confidence_score >= 0.8 for item in relevant) else "B",
                "gaps": [
                    f"{item.kind.value} returned {item.result}"
                    for item in relevant
                    if item.result
                    not in {"verified", "clear", "valid", "all_covered", "compliant", "BAA_COMPLETE"}
                ],
                "report": {item.kind.value: item.details for item in relevant},
            }
        else:
            relevant = [
                item
                for item in verifications
                if item.kind in {VerificationKind.GST, VerificationKind.PAN, VerificationKind.BANK}
            ]
            payload = {
                "status": "completed" if relevant else "pending",
                "overall_score": round(
                    sum(item.confidence_score for item in relevant) / max(1, len(relevant)) * 100
                ),
                "grade": "A" if all(item.confidence_score >= 0.8 for item in relevant) else "B",
                "findings": [
                    f"{item.kind.value} returned {item.result}"
                    for item in relevant
                    if item.result != "verified"
                ],
                "report": {item.kind.value: item.details for item in relevant},
            }
        return {
            "vendor_id": vendor.id,
            "vendor_name": vendor.name,
            f"{category}_review": payload,
        }

    def get_vendor_security(self, vendor_id: str) -> dict[str, Any]:
        return self._review_payload(vendor_id, "security")

    def get_vendor_compliance(self, vendor_id: str) -> dict[str, Any]:
        return self._review_payload(vendor_id, "compliance")

    def get_vendor_financial(self, vendor_id: str) -> dict[str, Any]:
        return self._review_payload(vendor_id, "financial")

    def get_vendor_evidence_gaps(self, vendor_id: str) -> dict[str, Any]:
        vendor = self.repo.get_vendor(vendor_id)
        if not vendor:
            raise HTTPException(status_code=404, detail="Vendor not found")
        required = _required_documents(vendor.workflow_type)
        uploaded = {
            item.classification
            for item in self.repo.list_documents(vendor_id)
            if item.classification
        }
        missing = [item for item in required if item not in uploaded]
        requests = [
            {
                "id": f"gap-{index}",
                "document_type": item,
                "criticality": "high" if item in {"BAA", "SOC 2 Type II"} else "medium",
                "reason": f"{item} is required before approval can complete.",
                "status": "pending",
                "email_sent": False,
                "deadline": (_utcnow() + timedelta(days=3)).isoformat(),
            }
            for index, item in enumerate(missing, start=1)
        ]
        completion = round((len(uploaded) / len(required)) * 100, 2)
        return {
            "vendor_id": vendor.id,
            "vendor_name": vendor.name,
            "total_requests": len(requests),
            "pending": len(requests),
            "received": len(uploaded),
            "completion_percentage": completion,
            "evidence_requests": requests,
        }

    def get_vendor_evidence_status(self, vendor_id: str) -> dict[str, Any]:
        gaps = self.get_vendor_evidence_gaps(vendor_id)
        vendor = self.repo.get_vendor(vendor_id)
        return {
            "vendor_id": vendor_id,
            "vendor_name": vendor.name if vendor else None,
            "evidence_requests": gaps["total_requests"],
            "tracking_entries": len(self.repo.list_events(vendor_id)),
            "requests": gaps["evidence_requests"],
            "recent_tracking": [
                {
                    "action": event.event_type,
                    "actor": "system",
                    "details": event.data.get("status")
                    or event.data.get("agent")
                    or "workflow event",
                    "created_at": event.created_at,
                }
                for event in self.repo.list_events(vendor_id)[-5:]
            ],
        }

    def request_vendor_evidence(self, vendor_id: str) -> dict[str, Any]:
        vendor = self.repo.get_vendor(vendor_id)
        if not vendor:
            raise HTTPException(status_code=404, detail="Vendor not found")
        self.repo.add_notification(
            NotificationLogRecord(
                vendor_id=vendor.id,
                recipient=vendor.contact_email,
                template="send_reminder_email",
                subject=f"Additional evidence requested for {vendor.name}",
                status="queued",
            )
        )
        from backend.tasks.notifications import send_email_task

        send_email_task.delay(
            vendor.contact_email,
            f"Additional evidence requested for {vendor.name}",
            "Additional onboarding evidence is required. Please review the vendor portal checklist and upload the missing items.",
            "send_reminder_email",
        )
        self.dispatch_event(
            vendor.id,
            "approval_required",
            {"message": "Additional evidence requested from vendor"},
        )
        return {"status": "accepted", "message": "Evidence coordination triggered."}

    def get_vendor_risk_assessment(self, vendor_id: str) -> dict[str, Any]:
        risk = self.repo.get_risk_assessment(vendor_id)
        if not risk:
            return {
                "vendor_id": vendor_id,
                "status": "pending",
                "message": "Risk assessment pending",
            }
        return {
            "vendor_id": vendor_id,
            "status": "completed",
            "risk_assessment": {
                "overall_risk_score": risk.overall_risk_score,
                "risk_level": risk.risk_level,
                "approval_tier": risk.approval_tier,
                "breakdown": {
                    "bayesian": {"score": risk.overall_risk_score, "weight": 0.5},
                    "rl": {"score": 100 if risk.models_agree else 65, "weight": 0.5},
                },
                "executive_summary": risk.executive_summary,
                "critical_blockers": risk.critical_blockers,
                "conditional_items": risk.conditional_items,
                "mitigation_recommendations": [
                    item["description"] for item in risk.mitigation_recommendations
                ],
                "completed_at": risk.updated_at,
                "bayesian_tier": risk.bayesian_tier,
                "rl_tier": risk.rl_tier,
                "models_agree": risk.models_agree,
                "confidence_indicator": risk.confidence_indicator,
            },
        }

    def _approval_status_payload(
        self,
        approval: ApprovalWorkflowRecord | None,
    ) -> dict[str, Any]:
        if not approval:
            return {
                "status": "not_started",
                "completion_percentage": 0,
                "total_required": 0,
                "total_decided": 0,
                "pending_approvers": [],
                "overdue": False,
                "final_decision": None,
            }
        decisions = self.repo.list_approval_decisions(approval.vendor_id)
        decided_roles = {item.role.value for item in decisions}
        pending = [
            item
            for item in approval.required_approvers
            if item["role"] not in decided_roles
        ]
        return {
            "approval_id": approval.id,
            "status": approval.status,
            "completion_percentage": approval.completion_percentage,
            "total_required": len(approval.required_approvers),
            "total_decided": len(decisions),
            "pending_approvers": pending,
            "overdue": bool(approval.deadline and approval.deadline < _utcnow()),
            "final_decision": approval.final_decision,
            "decisions": [
                {
                    "approver": item.approver_name,
                    "role": item.role.value,
                    "decision": item.decision.value,
                    "decided_at": item.updated_at,
                }
                for item in decisions
            ],
        }

    def get_vendor_approval_status(self, vendor_id: str) -> dict[str, Any]:
        approval = self.repo.get_approval(vendor_id)
        payload = self._approval_status_payload(approval)
        payload["vendor_id"] = vendor_id
        return payload

    def get_vendor_approval_workflow(self, vendor_id: str) -> dict[str, Any]:
        approval = self.repo.get_approval(vendor_id)
        vendor = self.repo.get_vendor(vendor_id)
        payload = self._approval_status_payload(approval)
        return {
            "vendor_id": vendor_id,
            "approval_id": payload.get("approval_id"),
            "approval_tier": vendor.approval_tier if vendor else None,
            "status": payload["status"],
            "required_approvers": approval.required_approvers if approval else [],
            "workflow": {
                "id": approval.id if approval else None,
                "name": (
                    "Healthcare Approval Flow"
                    if vendor and vendor.workflow_type == WorkflowType.HEALTHCARE
                    else "SaaS Approval Flow"
                ),
                "approval_order": "sequential",
                "timeout_hours": (
                    336
                    if vendor and vendor.approval_tier != RiskTier.TIER_3.value
                    else 168
                ),
            },
            "deadline": approval.deadline if approval else None,
        }

    def get_vendor_approval_decisions(self, vendor_id: str) -> dict[str, Any]:
        decisions = self.repo.list_approval_decisions(vendor_id)
        return {
            "vendor_id": vendor_id,
            "total": len(decisions),
            "decisions": [
                {
                    "id": item.id,
                    "approver_name": item.approver_name,
                    "approver_role": item.role.value,
                    "decision": item.decision.value,
                    "comments": item.comments,
                    "conditions": item.conditions,
                    "decided_at": item.updated_at,
                }
                for item in decisions
            ],
        }

    def submit_approval(
        self,
        vendor_id: str,
        role: Role,
        approver_email: str,
        payload: ApprovalDecisionSchema,
    ) -> dict[str, Any]:
        vendor = self.repo.get_vendor(vendor_id)
        approval = self.repo.get_approval(vendor_id)
        if not vendor or not approval:
            raise HTTPException(status_code=404, detail="Approval workflow not found")
        if (
            approval.current_step_role
            and approval.current_step_role != role.value
            and payload.decision == ApprovalDecisionType.APPROVE
        ):
            raise HTTPException(
                status_code=409,
                detail=f"Current step is {approval.current_step_role}",
            )

        decision_record = ApprovalDecisionRecord(
            approval_id=approval.id,
            vendor_id=vendor_id,
            role=role,
            approver_name=approver_email.split("@", 1)[0].replace(".", " ").title(),
            approver_email=approver_email,
            decision=payload.decision,
            comments=payload.comments,
            conditions=payload.conditions,
            permission_level=payload.permission_level,
        )
        self.repo.add_approval_decision(decision_record)
        if role == Role.IT and payload.permission_level:
            approval.permission_level = payload.permission_level

        if payload.decision == ApprovalDecisionType.REJECT:
            approval.status = "rejected"
            approval.final_decision = "rejected"
            approval.completion_percentage = 100.0
            vendor.status = VendorStatusEnum.REJECTED
            vendor.approval_status = "rejected"
        elif payload.decision == ApprovalDecisionType.REQUEST_CHANGES:
            approval.status = "changes_requested"
            approval.final_decision = "request_changes"
            vendor.status = VendorStatusEnum.REQUEST_CHANGES
            vendor.approval_status = "changes_requested"
        else:
            decisions = self.repo.list_approval_decisions(vendor_id)
            approved_roles = [
                item.role.value
                for item in decisions
                if item.decision == ApprovalDecisionType.APPROVE
            ]
            required_roles = [item["role"] for item in approval.required_approvers]
            approval.completion_percentage = round(
                (len(approved_roles) / len(required_roles)) * 100,
                2,
            )
            next_roles = [item for item in required_roles if item not in approved_roles]
            if next_roles:
                approval.current_step_role = next_roles[0]
                approval.status = "pending"
                vendor.approval_status = "pending"
            else:
                approval.current_step_role = None
                approval.status = "approved"
                approval.final_decision = "approved"
                approval.completion_percentage = 100.0
                vendor.status = VendorStatusEnum.FULLY_APPROVED
                vendor.approval_status = "approved"
                vendor.progress_percentage = 100.0
                vendor.current_step = "completed"
                vendor.current_phase = "approved"
                if vendor.workflow_type == WorkflowType.HEALTHCARE:
                    self.repo.upsert_scheduled_task(
                        ScheduledTaskRecord(
                            vendor_id=vendor.id,
                            task_type="baa_renewal_reminder",
                            due_at=_utcnow() + timedelta(days=330),
                        )
                    )
                    self.repo.upsert_scheduled_task(
                        ScheduledTaskRecord(
                            vendor_id=vendor.id,
                            task_type="annual_hipaa_reassessment",
                            due_at=_utcnow() + timedelta(days=365),
                        )
                    )
                    self.repo.add_ephi_access_log(
                        EPHIAccessLogRecord(
                            vendor_id=vendor.id,
                            actor_email=approver_email,
                            actor_role=role,
                            action="compliance_approval_completed",
                            details={"vendor_status": vendor.status.value},
                        )
                    )
                risk = self.repo.get_risk_assessment(vendor.id)
                reward = reward_for_outcome(
                    approval.approval_tier,
                    "approved",
                    healthcare=vendor.workflow_type == WorkflowType.HEALTHCARE,
                )
                self.repo.add_rl_episode(
                    RLTrainingEpisodeRecord(
                        vendor_id=vendor.id,
                        workflow_type=vendor.workflow_type,
                        state_vector=risk.state_vector if risk else [],
                        action=0,
                        reward=reward,
                        actual_outcome="approved",
                    )
                )
                self.repo.add_feedback(
                    RiskModelFeedbackRecord(
                        vendor_id=vendor.id,
                        workflow_type=vendor.workflow_type,
                        predicted_tier=approval.approval_tier,
                        actual_outcome="approved",
                        reward=reward,
                    )
                )

        self.repo.upsert_approval(approval)
        self.repo.update_vendor(vendor)
        self.dispatch_event(
            vendor.id,
            "approval_complete"
            if approval.status == "approved"
            else "approval_required",
            {
                "role": role.value,
                "decision": payload.decision.value,
                "next_step": approval.current_step_role,
                "approval_complete": approval.status == "approved",
            },
        )
        return {
            "status": approval.status,
            "message": "Decision recorded successfully.",
            "decision_id": decision_record.id,
            "approval_complete": approval.status == "approved",
            "final_outcome": approval.final_decision,
            "next_step": approval.current_step_role,
        }

    def get_vendor_approval_packet(self, vendor_id: str) -> dict[str, Any] | None:
        vendor = self.repo.get_vendor(vendor_id)
        if not vendor:
            return None
        risk = self.repo.get_risk_assessment(vendor_id)
        bayesian = self.repo.get_bayesian_score(vendor_id)
        workflow = self.repo.get_approval(vendor_id)
        decisions = self.repo.list_approval_decisions(vendor_id)
        baa = self.repo.get_baa_record(vendor_id)
        standard_verifications = self.repo.list_verifications(vendor_id)
        hipaa_verifications = self.repo.list_verifications(vendor_id, hipaa=True)
        return {
            "verification_results": {
                "standard": [
                    self._serialize_verification(item) for item in standard_verifications
                ],
                "hipaa": [self._serialize_verification(item) for item in hipaa_verifications],
            },
            "vendor": {
                "id": vendor.id,
                "name": vendor.name,
                "workflow_type": vendor.workflow_type.value,
                "ephi_involved": vendor.ephi_involved,
                "contact_email": vendor.contact_email,
                "contract_value": vendor.contract_value,
                "status": vendor.status.value,
            },
            "documents": [
                {
                    "id": item.id,
                    "file_name": item.file_name,
                    "classification": item.classification,
                    "processing_status": item.processing_status,
                }
                for item in self.repo.list_documents(vendor_id)
            ],
            "security_review": self.get_vendor_security(vendor_id).get("security_review"),
            "compliance_review": self.get_vendor_compliance(vendor_id).get("compliance_review"),
            "financial_review": self.get_vendor_financial(vendor_id).get("financial_review"),
            "aggregate_score": vendor.overall_risk_score,
            "risk_assessment": (
                {
                    "overall_risk_score": risk.overall_risk_score,
                    "risk_level": risk.risk_level,
                    "approval_tier": risk.approval_tier,
                    "executive_summary": risk.executive_summary,
                    "probability_legitimate": (
                        bayesian.probability_legitimate if bayesian else None
                    ),
                    "probability_fraud": bayesian.probability_fraud if bayesian else None,
                    "confidence_interval": (
                        bayesian.confidence_interval if bayesian else None
                    ),
                    "evidence_explanation": (
                        bayesian.evidence_explanation if bayesian else []
                    ),
                    "hard_override": bayesian.hard_override if bayesian else None,
                    "hipaa_overrides": bayesian.hipaa_overrides if bayesian else [],
                    "hipaa_risk_factors": (
                        bayesian.hipaa_risk_factors if bayesian else []
                    ),
                    "critical_blockers": risk.critical_blockers,
                    "conditional_items": risk.conditional_items,
                    "mitigation_recommendations": risk.mitigation_recommendations,
                    "bayesian_tier": risk.bayesian_tier,
                    "rl_tier": risk.rl_tier,
                    "models_agree": risk.models_agree,
                    "confidence_indicator": risk.confidence_indicator,
                    "baa_clauses": baa.clauses if baa else None,
                    "baa_clauses_missing": baa.clauses_missing if baa else [],
                    "baa_expiry_date": baa.expiry_date if baa else None,
                }
                if risk
                else None
            ),
            "approval_workflow": {
                "name": (
                    "Healthcare Approval Flow"
                    if vendor.workflow_type == WorkflowType.HEALTHCARE
                    else "SaaS Approval Flow"
                ),
                "approval_order": "sequential",
                "approvers": workflow.required_approvers if workflow else [],
                "current_step_role": workflow.current_step_role if workflow else None,
                "deadline": workflow.deadline if workflow else None,
            },
            "evidence_gaps": self.get_vendor_evidence_gaps(vendor_id)["evidence_requests"],
            "recommendation": risk.executive_summary if risk else "Risk scoring pending",
            "audit_trail_count": len(self.repo.list_events(vendor_id)),
            "status_history": [
                {
                    "event_type": event.event_type,
                    "data": event.data,
                    "created_at": event.created_at,
                }
                for event in self.repo.list_events(vendor_id)[-10:]
            ],
            "approval_history": [
                {
                    "role": item.role.value,
                    "decision": item.decision.value,
                    "comments": item.comments,
                    "decided_at": item.updated_at,
                }
                for item in decisions
            ],
            "generated_at": _utcnow(),
        }

    def get_vendor_report(self, vendor_id: str) -> dict[str, Any]:
        vendor = self.repo.get_vendor(vendor_id)
        if not vendor:
            raise HTTPException(status_code=404, detail="Vendor not found")
        documents = self.repo.list_documents(vendor_id)
        return {
            "vendor": {
                "id": vendor.id,
                "name": vendor.name,
                "type": vendor.vendor_type or vendor.service_type,
                "contract_value": vendor.contract_value,
                "domain": vendor.domain,
                "status": vendor.status.value.lower(),
            },
            "documents": {
                "total": len(documents),
                "items": [
                    {
                        "id": item.id,
                        "file_name": item.file_name,
                        "classification": item.classification,
                        "classification_confidence": item.classification_confidence,
                        "processing_status": item.processing_status,
                        "extracted_dates": item.extracted_dates,
                    }
                    for item in documents
                ],
            },
            "security_review": self.get_vendor_security(vendor_id).get("security_review"),
            "compliance_review": self.get_vendor_compliance(vendor_id).get("compliance_review"),
            "financial_review": self.get_vendor_financial(vendor_id).get("financial_review"),
            "risk_assessment": self.get_vendor_risk_assessment(vendor_id).get("risk_assessment"),
            "approval": self.get_vendor_approval_workflow(vendor_id),
            "evidence_gaps": self.get_vendor_evidence_gaps(vendor_id),
            "audit_trail": [
                {
                    "agent": event.data.get("agent"),
                    "action": event.event_type,
                    "tool": event.data.get("tool"),
                    "status": event.data.get("status"),
                    "duration_ms": event.data.get("duration_ms"),
                    "timestamp": event.created_at,
                }
                for event in self.repo.list_events(vendor_id)
            ],
        }

    def get_vendor_audit_trail(self, vendor_id: str) -> dict[str, Any]:
        vendor = self.repo.get_vendor(vendor_id)
        events = self.repo.list_events(vendor_id)
        decisions = self.repo.list_approval_decisions(vendor_id)
        return {
            "vendor_id": vendor_id,
            "vendor_name": vendor.name if vendor else None,
            "total_events": len(events) + len(decisions),
            "audit_trail": [
                {
                    "agent_name": event.data.get("agent"),
                    "action": event.event_type,
                    "status": event.data.get("status", "recorded"),
                    "created_at": event.created_at,
                }
                for event in events
            ],
            "trail": [
                {
                    "agent_name": decision.role.value,
                    "action": "approval_decision",
                    "status": decision.decision.value,
                    "created_at": decision.updated_at,
                }
                for decision in decisions
            ],
            "timeline": [
                {
                    "event_type": event.event_type,
                    "status": event.data.get("status", "recorded"),
                    "created_at": event.created_at,
                }
                for event in events[-10:]
            ],
        }

    def get_dashboard_stats(self) -> dict[str, Any]:
        return self.repo.dashboard_stats()

    def get_dashboard_recent(self) -> dict[str, Any]:
        recent = self.repo.dashboard_recent()
        return {
            "recent_vendors": [
                self._vendor_summary(item) for item in recent["recent_vendors"]
            ],
            "recent_approvals": [
                {
                    "vendor_id": item.vendor_id,
                    "vendor_name": (
                        self.repo.get_vendor(item.vendor_id).name
                        if self.repo.get_vendor(item.vendor_id)
                        else item.vendor_id
                    ),
                    "status": item.decision.value,
                    "decided_at": item.updated_at,
                }
                for item in recent["recent_approvals"]
            ],
            "recent_completions": [
                self._vendor_summary(item)
                for item in recent["recent_completions"]
            ],
        }

    def get_ephi_logs(self, vendor_id: str) -> dict[str, Any]:
        logs = self.repo.list_ephi_access_logs(vendor_id)
        return {
            "vendor_id": vendor_id,
            "entries": [
                {
                    "id": item.id,
                    "actor_email": item.actor_email,
                    "actor_role": item.actor_role.value,
                    "action": item.action,
                    "details": item.details,
                    "created_at": item.created_at,
                }
                for item in logs
            ],
        }

    def rag_compliance_query(self, query: str, vendor_id: str | None = None) -> dict[str, Any]:
        return query_compliance_knowledge(self.repo, query, vendor_id)

    def healthcare_chat(self, payload: HealthcareChatRequest) -> dict[str, Any]:
        workflow_hint = "healthcare" if payload.vendor_id else "general"
        return {
            "status": "success",
            "reply": (
                "Upload the missing HIPAA checklist items, including the signed BAA and ePHI flow map. "
                "Once submitted, the OIG, BAA, attestation, and subprocessor checks will run automatically."
                if workflow_hint == "healthcare"
                else "Use the portal checklist to upload the remaining onboarding documents."
            ),
        }

    def onboard_from_prompt(self, prompt: str) -> dict[str, Any]:
        lowered = prompt.lower()
        vendor_name = re.search(r"onboard\s+([a-z0-9.\- ]+)", lowered)
        email_domain = re.search(r"domain\s+([a-z0-9.\-]+\.[a-z]{2,})", lowered)
        value_match = re.search(r"\$?(\d{4,})", lowered)
        payload = VendorRequestSchema(
            vendor_name=(
                vendor_name.group(1).strip().title()
                if vendor_name
                else "New Vendor"
            ),
            service_type="observability" if "observability" in lowered else "saas",
            reason="Prompt-based intake",
            contract_value=float(value_match.group(1)) if value_match else 100000,
            contact_email=(
                f"security@{email_domain.group(1)}"
                if email_domain
                else "vendor@example.com"
            ),
        )
        result = self.create_vendor_request(
            payload,
            actor_email="employee@hackstrom.local",
        )
        request_record = self.repo.get_vendor_request(result["request_id"])
        vendor_id = request_record.vendor_id if request_record else result["request_id"]
        return {
            "status": "accepted",
            "vendor_id": vendor_id,
            "message": f"Vendor {payload.vendor_name} onboarding started.",
            "status_url": f"/api/v1/vendors/{vendor_id}/status",
            "report_url": f"/api/v1/vendors/{vendor_id}/report",
        }


_service: VendorOnboardingService | None = None


def get_service() -> VendorOnboardingService:
    global _service
    if _service is None:
        _service = VendorOnboardingService(get_repository())
    return _service
