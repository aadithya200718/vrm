from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from backend.core.logging import logger
from backend.core.metrics import WORKER_THROUGHPUT
from backend.core.repository import get_repository
from backend.core.services import get_service
from backend.models.domain import VendorRecord, VerificationResultRecord
from backend.models.enums import VerificationKind, VerificationStatus
from backend.tasks.celery_app import celery_app
from backend.tools.comply_advantage import check_sanctions
from backend.tools.decentro import verify_bank_account
from backend.tools.signzy import verify_gst
from backend.tools.surepass import verify_pan


def _queue_name(task: Any, default: str = "verification_queue") -> str:
    delivery_info = getattr(task.request, "delivery_info", None) or {}
    return delivery_info.get("routing_key") or default


def _load_vendor(vendor_id: str) -> VendorRecord:
    vendor = get_repository().get_vendor(vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return vendor


def _status_from_result(result: str) -> VerificationStatus:
    if result in {"flagged", "excluded"}:
        return VerificationStatus.FLAGGED
    if result in {"failed", "invalid", "error"}:
        return VerificationStatus.FAILED
    if result in {"skipped"}:
        return VerificationStatus.SKIPPED
    return VerificationStatus.SUCCESS


def _persist_standard_verification(
    vendor: VendorRecord,
    *,
    kind: VerificationKind,
    tool_result: Any,
    agent_name: str,
    queue_name: str,
) -> VerificationResultRecord:
    repo = get_repository()
    existing = repo.get_verification_by_kind(vendor.id, kind)
    kwargs: dict[str, Any] = {}
    if existing:
        kwargs["id"] = existing.id
        kwargs["created_at"] = existing.created_at
    record = VerificationResultRecord(
        vendor_id=vendor.id,
        kind=kind,
        workflow_type=vendor.workflow_type,
        status=_status_from_result(tool_result.result),
        result=tool_result.result,
        confidence_score=tool_result.confidence_score,
        details=tool_result.details,
        agent_name=agent_name,
        queue_name=queue_name,
        **kwargs,
    )
    saved = repo.upsert_verification(record)
    WORKER_THROUGHPUT.labels(worker_name="celery", queue_name=queue_name).inc()
    return saved


def _serialize_verification(record: VerificationResultRecord) -> dict[str, Any]:
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
    name="backend.tasks.verification.run_vendor_verification",
)
def run_vendor_verification(self, vendor_id: str) -> dict[str, Any]:
    try:
        logger.info(
            "Running vendor verification pipeline",
            extra={"service": "celery", "vendor_id": vendor_id, "agent": "verification_pipeline"},
        )
        get_service()._run_verification_pipeline_sync(vendor_id)
        vendor = _load_vendor(vendor_id)
        return {
            "status": "completed",
            "vendor_id": vendor_id,
            "vendor_status": vendor.status.value,
            "workflow_type": vendor.workflow_type.value,
            "risk_assessment": get_service().get_vendor_risk_assessment(vendor_id),
        }
    except HTTPException as exc:
        logger.error(
            "Vendor verification pipeline failed permanently",
            extra={"service": "celery", "vendor_id": vendor_id, "agent": "verification_pipeline"},
        )
        return {
            "status": "failed",
            "vendor_id": vendor_id,
            "http_status": exc.status_code,
            "error": exc.detail,
        }
    except Exception as exc:
        logger.exception(
            "Vendor verification pipeline failed",
            extra={"service": "celery", "vendor_id": vendor_id, "agent": "verification_pipeline"},
        )
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(
    bind=True,
    max_retries=3,
    name="backend.tasks.verification.verify_gst_task",
)
def verify_gst_task(self, vendor_id: str, gst_number: str) -> dict[str, Any]:
    try:
        vendor = _load_vendor(vendor_id)
        record = _persist_standard_verification(
            vendor,
            kind=VerificationKind.GST,
            tool_result=verify_gst(gst_number, vendor.name),
            agent_name="GST Verification",
            queue_name=_queue_name(self),
        )
        logger.info(
            "GST verification completed",
            extra={"service": "celery", "vendor_id": vendor_id, "agent": "gst_verifier"},
        )
        return _serialize_verification(record)
    except HTTPException as exc:
        return {
            "status": "failed",
            "vendor_id": vendor_id,
            "kind": VerificationKind.GST.value,
            "http_status": exc.status_code,
            "error": exc.detail,
        }
    except Exception as exc:
        logger.exception(
            "GST verification failed",
            extra={"service": "celery", "vendor_id": vendor_id, "agent": "gst_verifier"},
        )
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(
    bind=True,
    max_retries=3,
    name="backend.tasks.verification.verify_pan_task",
)
def verify_pan_task(self, vendor_id: str, pan_number: str) -> dict[str, Any]:
    try:
        vendor = _load_vendor(vendor_id)
        record = _persist_standard_verification(
            vendor,
            kind=VerificationKind.PAN,
            tool_result=verify_pan(pan_number, vendor.name),
            agent_name="PAN Verification",
            queue_name=_queue_name(self),
        )
        logger.info(
            "PAN verification completed",
            extra={"service": "celery", "vendor_id": vendor_id, "agent": "pan_verifier"},
        )
        return _serialize_verification(record)
    except HTTPException as exc:
        return {
            "status": "failed",
            "vendor_id": vendor_id,
            "kind": VerificationKind.PAN.value,
            "http_status": exc.status_code,
            "error": exc.detail,
        }
    except Exception as exc:
        logger.exception(
            "PAN verification failed",
            extra={"service": "celery", "vendor_id": vendor_id, "agent": "pan_verifier"},
        )
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(
    bind=True,
    max_retries=3,
    name="backend.tasks.verification.verify_bank_task",
)
def verify_bank_task(self, vendor_id: str, account_number: str, ifsc: str) -> dict[str, Any]:
    try:
        vendor = _load_vendor(vendor_id)
        raw_text = f"{account_number} {ifsc}".strip()
        record = _persist_standard_verification(
            vendor,
            kind=VerificationKind.BANK,
            tool_result=verify_bank_account(raw_text, vendor.name),
            agent_name="Bank Validation",
            queue_name=_queue_name(self),
        )
        logger.info(
            "Bank verification completed",
            extra={"service": "celery", "vendor_id": vendor_id, "agent": "bank_verifier"},
        )
        return _serialize_verification(record)
    except HTTPException as exc:
        return {
            "status": "failed",
            "vendor_id": vendor_id,
            "kind": VerificationKind.BANK.value,
            "http_status": exc.status_code,
            "error": exc.detail,
        }
    except Exception as exc:
        logger.exception(
            "Bank verification failed",
            extra={"service": "celery", "vendor_id": vendor_id, "agent": "bank_verifier"},
        )
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(
    bind=True,
    max_retries=3,
    name="backend.tasks.verification.check_sanctions_task",
)
def check_sanctions_task(self, vendor_id: str, names: list[str]) -> dict[str, Any]:
    try:
        vendor = _load_vendor(vendor_id)
        names_to_check = names or [vendor.name]
        record = _persist_standard_verification(
            vendor,
            kind=VerificationKind.SANCTIONS,
            tool_result=check_sanctions(names_to_check),
            agent_name="Sanctions Check",
            queue_name=_queue_name(self),
        )
        logger.info(
            "Sanctions check completed",
            extra={"service": "celery", "vendor_id": vendor_id, "agent": "sanctions_checker"},
        )
        return _serialize_verification(record)
    except HTTPException as exc:
        return {
            "status": "failed",
            "vendor_id": vendor_id,
            "kind": VerificationKind.SANCTIONS.value,
            "http_status": exc.status_code,
            "error": exc.detail,
        }
    except Exception as exc:
        logger.exception(
            "Sanctions check failed",
            extra={"service": "celery", "vendor_id": vendor_id, "agent": "sanctions_checker"},
        )
        raise self.retry(exc=exc, countdown=60)
