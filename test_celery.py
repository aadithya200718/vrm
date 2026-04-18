from __future__ import annotations

import json
import time
from uuid import uuid4

from backend.core.config import get_settings
from backend.core.repository import get_repository
from backend.models.domain import VendorDocumentRecord, VendorRecord, VendorRequestRecord
from backend.models.enums import VendorStatusEnum, WorkflowType
from backend.tasks.celery_app import celery_app
from backend.tasks.notifications import send_email_task
from backend.tasks.verification import run_vendor_verification, verify_gst_task


def print_section(title: str) -> None:
    print(f"\n=== {title} ===")


def wait_for_task(async_result, timeout: int = 30) -> dict:
    started = time.time()
    print(f"Task {async_result.id} queued with status {async_result.status}")
    while time.time() - started < timeout:
        if async_result.ready():
            try:
                payload = async_result.get(timeout=1, propagate=False)
            except Exception as exc:  # pragma: no cover - runtime dependent
                payload = {"status": "failed", "error": str(exc)}
            return {
                "task_id": async_result.id,
                "state": async_result.status,
                "result": payload,
            }
        time.sleep(1)
        print(f"Waiting... current state: {async_result.status}")
    return {
        "task_id": async_result.id,
        "state": async_result.status,
        "result": None,
        "warning": "Timed out waiting for task completion. Verify workers are running.",
    }


def build_test_vendor() -> VendorRecord:
    repo = get_repository()
    suffix = uuid4().hex[:8]
    request = VendorRequestRecord(
        employee_email=f"celery.test.{suffix}@hackstrom.local",
        vendor_name=f"Celery Smoke Vendor {suffix}",
        service_type="Cloud Services",
        reason="Celery integration smoke test",
        contract_value=10000,
        contact_email=f"vendor.{suffix}@example.com",
    )
    repo.create_vendor_request(request)
    vendor = VendorRecord(
        request_id=request.id,
        name=request.vendor_name,
        service_type=request.service_type,
        workflow_type=WorkflowType.SAAS,
        status=VendorStatusEnum.DOCUMENTS_SUBMITTED,
        contract_value=request.contract_value,
        contact_email=request.contact_email,
        vendor_type=request.service_type,
        current_phase="verification",
        current_agent="verification_supervisor",
        current_step="documents_ready",
        checklist_required=5,
        checklist_received=5,
    )
    repo.create_vendor(vendor)
    request.vendor_id = vendor.id
    repo.update_vendor_request(request)

    documents = [
        VendorDocumentRecord(
            vendor_id=vendor.id,
            file_name="gst.txt",
            file_type="txt",
            document_type="GST Certificate",
            classification="GST Certificate",
            classification_confidence=0.99,
            processing_status="processed",
            extracted_text="GSTIN 27ABCDE1234F1Z5 registered and active.",
        ),
        VendorDocumentRecord(
            vendor_id=vendor.id,
            file_name="pan.txt",
            file_type="txt",
            document_type="PAN Card",
            classification="PAN Card",
            classification_confidence=0.99,
            processing_status="processed",
            extracted_text="Permanent Account Number ABCDE1234F issued to vendor.",
        ),
        VendorDocumentRecord(
            vendor_id=vendor.id,
            file_name="bank.txt",
            file_type="txt",
            document_type="Cancelled Cheque",
            classification="Cancelled Cheque",
            classification_confidence=0.99,
            processing_status="processed",
            extracted_text="Account 123456789012 IFSC HDFC0001234.",
        ),
        VendorDocumentRecord(
            vendor_id=vendor.id,
            file_name="incorporation.txt",
            file_type="txt",
            document_type="Incorporation Certificate",
            classification="Incorporation Certificate",
            classification_confidence=0.99,
            processing_status="processed",
            extracted_text="Company incorporated in 2018 and active.",
        ),
        VendorDocumentRecord(
            vendor_id=vendor.id,
            file_name="soc2.txt",
            file_type="txt",
            document_type="SOC 2 Type II",
            classification="SOC 2 Type II",
            classification_confidence=0.99,
            processing_status="processed",
            extracted_text="SOC 2 Type II attestation issued by Heuristic Audit LLP.",
        ),
    ]
    for document in documents:
        repo.create_document(document)

    return vendor


def main() -> None:
    settings = get_settings()

    print_section("Configuration")
    print(json.dumps(
        {
            "data_backend": settings.data_backend,
            "celery_task_always_eager": settings.celery_task_always_eager,
            "broker": settings.celery_broker_url,
            "result_backend": settings.celery_result_backend,
        },
        indent=2,
    ))

    print_section("Celery Connection")
    if settings.celery_task_always_eager:
        print("Eager mode is enabled. Tasks will execute synchronously in-process.")
        ping = {"mode": "eager"}
    else:
        inspector = celery_app.control.inspect(timeout=2)
        ping = inspector.ping() or {}
        if ping:
            print(json.dumps(ping, indent=2, default=str))
        else:
            print("No Celery workers responded to ping.")

    vendor = build_test_vendor()
    print_section("Prepared Test Vendor")
    print(json.dumps({"vendor_id": vendor.id, "vendor_name": vendor.name}, indent=2))

    print_section("Email Task")
    email_result = send_email_task.delay(
        "ops@example.com",
        "Celery smoke test",
        "This is a smoke test for the vendor onboarding Celery layer.",
        "smoke_test",
    )
    print(json.dumps(wait_for_task(email_result), indent=2, default=str))

    print_section("Verification Task")
    gst_result = verify_gst_task.delay(vendor.id, "27ABCDE1234F1Z5")
    print(json.dumps(wait_for_task(gst_result), indent=2, default=str))

    print_section("Pipeline Task")
    pipeline_result = run_vendor_verification.delay(vendor.id)
    print(json.dumps(wait_for_task(pipeline_result, timeout=45), indent=2, default=str))

    if not settings.celery_task_always_eager and not ping:
        print_section("Warning")
        print("Workers did not respond to ping. Pending task states usually mean the worker containers are not running yet.")


if __name__ == "__main__":
    main()
