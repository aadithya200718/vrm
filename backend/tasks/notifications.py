from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from backend.core.logging import logger
from backend.core.repository import get_repository
from backend.tasks.celery_app import celery_app


def _log_email(
    *,
    recipient: str,
    subject: str,
    body: str,
    template: str,
    vendor_id: str | None = None,
) -> dict[str, Any]:
    logger.info(
        f"Email task executed for {recipient}: {subject}",
        extra={"service": "celery", "vendor_id": vendor_id, "agent": "email_sender"},
    )
    return {
        "status": "sent",
        "vendor_id": vendor_id,
        "recipient": recipient,
        "subject": subject,
        "template": template,
        "body": body,
    }


@celery_app.task(
    bind=True,
    max_retries=3,
    name="backend.tasks.notifications.send_email_task",
)
def send_email_task(
    self,
    recipient: str,
    subject: str,
    body: str,
    template: str = "generic",
) -> dict[str, Any]:
    try:
        return _log_email(
            recipient=recipient,
            subject=subject,
            body=body,
            template=template,
        )
    except Exception as exc:
        logger.exception(
            "Generic email task failed",
            extra={"service": "celery", "agent": "email_sender"},
        )
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(
    bind=True,
    max_retries=3,
    name="backend.tasks.notifications.send_invitation_email_task",
)
def send_invitation_email_task(
    self,
    vendor_id: str,
    recipient: str,
    portal_url: str,
    checklist_count: int,
) -> dict[str, Any]:
    try:
        vendor = get_repository().get_vendor(vendor_id)
        vendor_name = vendor.name if vendor else "Vendor"
        subject = f"Complete vendor onboarding for {vendor_name}"
        body = (
            f"Your onboarding portal is ready: {portal_url}\n"
            f"Checklist items required: {checklist_count}"
        )
        return _log_email(
            recipient=recipient,
            subject=subject,
            body=body,
            template="send_invitation_email",
            vendor_id=vendor_id,
        )
    except Exception as exc:
        logger.exception(
            "Vendor invitation email task failed",
            extra={"service": "celery", "vendor_id": vendor_id, "agent": "email_sender"},
        )
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(
    bind=True,
    max_retries=3,
    name="backend.tasks.notifications.send_hipaa_invitation_email_task",
)
def send_hipaa_invitation_email_task(
    self,
    vendor_id: str,
    recipient: str,
    portal_url: str,
    checklist_count: int,
) -> dict[str, Any]:
    try:
        vendor = get_repository().get_vendor(vendor_id)
        vendor_name = vendor.name if vendor else "Vendor"
        subject = f"Complete HIPAA vendor onboarding for {vendor_name}"
        body = (
            f"Your HIPAA onboarding portal is ready: {portal_url}\n"
            f"Checklist items required: {checklist_count}"
        )
        return _log_email(
            recipient=recipient,
            subject=subject,
            body=body,
            template="send_hipaa_invitation_email",
            vendor_id=vendor_id,
        )
    except Exception as exc:
        logger.exception(
            "HIPAA invitation email task failed",
            extra={"service": "celery", "vendor_id": vendor_id, "agent": "email_sender"},
        )
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(
    bind=True,
    max_retries=3,
    name="backend.tasks.notifications.send_approval_notification_task",
)
def send_approval_notification_task(
    self,
    vendor_id: str,
    approver_email: str,
    role: str,
) -> dict[str, Any]:
    try:
        vendor = get_repository().get_vendor(vendor_id)
        if not vendor:
            raise HTTPException(status_code=404, detail="Vendor not found")
        subject = f"Approval requested for {vendor.name}"
        body = (
            f"You have a pending {role} approval step for vendor {vendor.name}. "
            f"Current risk tier: {vendor.approval_tier or 'pending'}."
        )
        return _log_email(
            recipient=approver_email,
            subject=subject,
            body=body,
            template="send_approval_notification",
            vendor_id=vendor_id,
        )
    except HTTPException as exc:
        return {
            "status": "failed",
            "vendor_id": vendor_id,
            "http_status": exc.status_code,
            "error": exc.detail,
        }
    except Exception as exc:
        logger.exception(
            "Approval notification task failed",
            extra={"service": "celery", "vendor_id": vendor_id, "agent": "email_sender"},
        )
        raise self.retry(exc=exc, countdown=60)
