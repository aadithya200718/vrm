from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException

from backend.compliance.baa_parser import analyze_baa
from backend.compliance.ephi import analyze_ephi_flow
from backend.core.config import get_settings
from backend.core.logging import logger
from backend.core.metrics import HIPAA_CHECK_RESULTS, WORKER_THROUGHPUT
from backend.core.repository import get_repository
from backend.core.services import get_service
from backend.models.domain import BAARecord, EPHIAccessLogRecord, HipaaVerificationRecord, VendorRecord
from backend.models.enums import Role, VendorStatusEnum, VerificationKind, VerificationStatus
from backend.tasks.celery_app import celery_app
from backend.tools.oig import check_oig


def _queue_name(task: Any, default: str = "hipaa_check_queue") -> str:
    delivery_info = getattr(task.request, "delivery_info", None) or {}
    return delivery_info.get("routing_key") or default


def _load_vendor(vendor_id: str) -> VendorRecord:
    vendor = get_repository().get_vendor(vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return vendor


def _status_from_result(result: str) -> VerificationStatus:
    normalized = result.lower()
    if normalized in {"excluded", "flagged", "non_compliant", "gaps_found", "baa_incomplete"}:
        return VerificationStatus.FLAGGED
    if normalized in {"failed", "invalid"}:
        return VerificationStatus.FAILED
    return VerificationStatus.SUCCESS


def _persist_hipaa_verification(
    vendor: VendorRecord,
    *,
    kind: VerificationKind,
    result: str,
    confidence_score: float,
    details: dict[str, Any],
    agent_name: str,
    queue_name: str,
) -> HipaaVerificationRecord:
    repo = get_repository()
    existing = repo.get_verification_by_kind(vendor.id, kind, hipaa=True)
    kwargs: dict[str, Any] = {}
    if existing:
        kwargs["id"] = existing.id
        kwargs["created_at"] = existing.created_at
    record = HipaaVerificationRecord(
        vendor_id=vendor.id,
        kind=kind,
        workflow_type=vendor.workflow_type,
        status=_status_from_result(result),
        result=result,
        confidence_score=confidence_score,
        details=details,
        agent_name=agent_name,
        queue_name=queue_name,
        **kwargs,
    )
    saved = repo.upsert_verification(record, hipaa=True)
    HIPAA_CHECK_RESULTS.labels(check_name=kind.value, result=saved.result).inc()
    WORKER_THROUGHPUT.labels(worker_name="celery", queue_name=queue_name).inc()
    return saved


def _serialize(record: HipaaVerificationRecord) -> dict[str, Any]:
    return {
        "status": "completed",
        "vendor_id": record.vendor_id,
        "verification_id": record.id,
        "kind": record.kind.value,
        "result": record.result,
        "verification_status": record.status.value,
        "confidence_score": record.confidence_score,
        "details": record.details,
        "queue_name": record.queue_name,
        "updated_at": record.updated_at,
    }


@celery_app.task(
    bind=True,
    max_retries=3,
    name="backend.tasks.healthcare.check_oig_task",
)
def check_oig_task(self, vendor_id: str, names: list[str]) -> dict[str, Any]:
    try:
        vendor = _load_vendor(vendor_id)
        names_to_check = names or [vendor.name]
        tool_result = check_oig(names_to_check)
        record = _persist_hipaa_verification(
            vendor,
            kind=VerificationKind.OIG,
            result=tool_result.result,
            confidence_score=tool_result.confidence_score,
            details=tool_result.details,
            agent_name="OIG Exclusion Check",
            queue_name=_queue_name(self),
        )
        if tool_result.result == "excluded" and get_settings().oig_auto_reject_enabled:
            vendor.status = VendorStatusEnum.REJECTED
            vendor.approval_status = "rejected"
            vendor.current_phase = "verification"
            vendor.current_step = "oig_exclusion"
            vendor.current_agent = "oig_checker"
            vendor.errors.append("Vendor auto-rejected due to OIG exclusion.")
            get_repository().update_vendor(vendor)
            get_service().dispatch_event(
                vendor.id,
                "status_change",
                {
                    "status": vendor.status.value,
                    "reason": "oig_excluded",
                    "auto_reject": True,
                },
            )
        logger.info(
            "OIG check completed",
            extra={"service": "celery", "vendor_id": vendor_id, "agent": "oig_checker"},
        )
        return _serialize(record)
    except HTTPException as exc:
        return {
            "status": "failed",
            "vendor_id": vendor_id,
            "kind": VerificationKind.OIG.value,
            "http_status": exc.status_code,
            "error": exc.detail,
        }
    except Exception as exc:
        logger.exception(
            "OIG check failed",
            extra={"service": "celery", "vendor_id": vendor_id, "agent": "oig_checker"},
        )
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(
    bind=True,
    max_retries=3,
    name="backend.tasks.healthcare.parse_baa_task",
)
def parse_baa_task(self, vendor_id: str, baa_text: str) -> dict[str, Any]:
    try:
        vendor = _load_vendor(vendor_id)
        analysis = analyze_baa(baa_text)
        get_repository().upsert_baa_record(
            BAARecord(
                vendor_id=vendor.id,
                status=analysis.status,
                confidence_score=analysis.confidence_score,
                clauses=analysis.clauses,
                clauses_missing=analysis.missing,
                expiry_date=(datetime.now(timezone.utc) + timedelta(days=365)).date().isoformat(),
            )
        )
        record = _persist_hipaa_verification(
            vendor,
            kind=VerificationKind.BAA,
            result=analysis.status,
            confidence_score=analysis.confidence_score,
            details={
                "clauses_present": [
                    clause for clause, clause_data in analysis.clauses.items() if clause_data["present"]
                ],
                "clauses_missing": analysis.missing,
            },
            agent_name="BAA Parser",
            queue_name=_queue_name(self),
        )
        logger.info(
            "BAA analysis completed",
            extra={"service": "celery", "vendor_id": vendor_id, "agent": "baa_parser"},
        )
        return _serialize(record)
    except HTTPException as exc:
        return {
            "status": "failed",
            "vendor_id": vendor_id,
            "kind": VerificationKind.BAA.value,
            "http_status": exc.status_code,
            "error": exc.detail,
        }
    except Exception as exc:
        logger.exception(
            "BAA analysis failed",
            extra={"service": "celery", "vendor_id": vendor_id, "agent": "baa_parser"},
        )
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(
    bind=True,
    max_retries=3,
    name="backend.tasks.healthcare.analyze_ephi_flow_task",
)
def analyze_ephi_flow_task(self, vendor_id: str, flow_text: str) -> dict[str, Any]:
    try:
        vendor = _load_vendor(vendor_id)
        analysis = analyze_ephi_flow(flow_text)
        record = _persist_hipaa_verification(
            vendor,
            kind=VerificationKind.EPHI_FLOW,
            result=analysis.result,
            confidence_score=analysis.confidence_score,
            details={
                "risks": analysis.risks,
                "encryption_verified": analysis.encryption_verified,
                "jurisdiction_verified": analysis.jurisdiction_verified,
            },
            agent_name="ePHI Data Flow Analyzer",
            queue_name=_queue_name(self),
        )
        logger.info(
            "ePHI flow analysis completed",
            extra={"service": "celery", "vendor_id": vendor_id, "agent": "ephi_flow_analyzer"},
        )
        return _serialize(record)
    except HTTPException as exc:
        return {
            "status": "failed",
            "vendor_id": vendor_id,
            "kind": VerificationKind.EPHI_FLOW.value,
            "http_status": exc.status_code,
            "error": exc.detail,
        }
    except Exception as exc:
        logger.exception(
            "ePHI flow analysis failed",
            extra={"service": "celery", "vendor_id": vendor_id, "agent": "ephi_flow_analyzer"},
        )
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(
    bind=True,
    max_retries=3,
    name="backend.tasks.healthcare.refresh_ephi_logs",
)
def refresh_ephi_logs(self, vendor_id: str) -> dict[str, Any]:
    try:
        vendor = _load_vendor(vendor_id)
        repo = get_repository()
        existing = repo.list_ephi_access_logs(vendor_id)
        repo.add_ephi_access_log(
            EPHIAccessLogRecord(
                vendor_id=vendor.id,
                actor_email="system@hackstrom.local",
                actor_role=Role.SYSTEM,
                action="refresh_ephi_logs",
                details={"existing_entries": len(existing)},
            )
        )
        refreshed = repo.list_ephi_access_logs(vendor_id)
        logger.info(
            "ePHI access logs refreshed",
            extra={"service": "celery", "vendor_id": vendor_id, "agent": "ephi_log_refresher"},
        )
        return {
            "status": "completed",
            "vendor_id": vendor_id,
            "entries": len(refreshed),
        }
    except HTTPException as exc:
        return {
            "status": "failed",
            "vendor_id": vendor_id,
            "http_status": exc.status_code,
            "error": exc.detail,
        }
    except Exception as exc:
        logger.exception(
            "Failed to refresh ePHI access logs",
            extra={"service": "celery", "vendor_id": vendor_id, "agent": "ephi_log_refresher"},
        )
        raise self.retry(exc=exc, countdown=60)
