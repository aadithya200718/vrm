from __future__ import annotations

from datetime import datetime, timedelta, timezone

from backend.core.logging import logger
from backend.core.repository import get_repository
from backend.models.enums import WorkflowType
from backend.tasks.celery_app import celery_app


@celery_app.task(
    bind=True,
    max_retries=3,
    name="backend.tasks.scheduler.check_baa_expiry",
)
def check_baa_expiry(self) -> dict:
    try:
        repo = get_repository()
        cutoff = (datetime.now(timezone.utc) + timedelta(days=30)).date().isoformat()
        expiring = []
        for vendor in repo.list_vendors():
            if vendor.workflow_type != WorkflowType.HEALTHCARE:
                continue
            baa = repo.get_baa_record(vendor.id)
            if baa and baa.expiry_date and baa.expiry_date <= cutoff:
                expiring.append({"vendor_id": vendor.id, "expiry_date": baa.expiry_date})
        logger.info(
            "Checked BAA expiry schedule",
            extra={"service": "celery", "agent": "scheduler"},
        )
        return {
            "status": "completed",
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "expiring_count": len(expiring),
            "expiring_baas": expiring,
        }
    except Exception as exc:
        logger.exception(
            "BAA expiry scheduler task failed",
            extra={"service": "celery", "agent": "scheduler"},
        )
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(
    bind=True,
    max_retries=3,
    name="backend.tasks.scheduler.schedule_hipaa_reassessments",
)
def schedule_hipaa_reassessments(self) -> dict:
    try:
        healthcare_vendors = [
            vendor.id
            for vendor in get_repository().list_vendors()
            if vendor.workflow_type == WorkflowType.HEALTHCARE
        ]
        logger.info(
            "HIPAA reassessment scheduler stub executed",
            extra={"service": "celery", "agent": "scheduler"},
        )
        return {
            "status": "scheduled",
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "candidate_vendors": len(healthcare_vendors),
            "message": "Annual HIPAA reassessment scheduling remains a Phase 4 stub.",
        }
    except Exception as exc:
        logger.exception(
            "HIPAA reassessment scheduler task failed",
            extra={"service": "celery", "agent": "scheduler"},
        )
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(
    bind=True,
    max_retries=3,
    name="backend.tasks.scheduler.cleanup_expired_tokens",
)
def cleanup_expired_tokens(self) -> dict:
    try:
        logger.info(
            "Expired onboarding token cleanup stub executed",
            extra={"service": "celery", "agent": "scheduler"},
        )
        return {
            "status": "completed",
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "message": "Expired token cleanup is stubbed pending Phase 4 retention workflows.",
        }
    except Exception as exc:
        logger.exception(
            "Expired token cleanup task failed",
            extra={"service": "celery", "agent": "scheduler"},
        )
        raise self.retry(exc=exc, countdown=60)
