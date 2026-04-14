"""
API routes for the Vendor Risk Management system.
"""
import os
import json
import uuid
import logging
import asyncio
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from app.core.db import (
    create_vendor,
    get_vendor,
    update_vendor,
    get_documents_for_vendor,
    get_security_review,
    get_compliance_review,
    get_financial_review,
    get_evidence_requests,
    update_evidence_request,
    get_evidence_tracking,
    get_audit_logs,
    create_policy,
    check_db_health,
)
from app.core.redis_state import load_state, check_redis_health
from app.core.vector import (
    upsert_policy,
    init_collections,
    check_vector_health,
)
from app.core.llm import check_llm_health
from app.agents.graph import run_full_workflow
from app.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1")


# ═══════════════════════════════════════════════════════════════════
# Request / Response Models
# ═══════════════════════════════════════════════════════════════════

class VendorOnboardRequest(BaseModel):
    vendor_name: str
    vendor_type: str = "technology"
    contract_value: float = 0.0
    vendor_domain: str = ""
    contact_email: str = ""
    contact_name: str = ""


class PolicyUploadRequest(BaseModel):
    title: str
    content: str
    category: str = "security"
    source: str = ""
    version: str = "1.0"


# ═══════════════════════════════════════════════════════════════════
# Background task runner
# ═══════════════════════════════════════════════════════════════════

def _run_workflow_sync(
    vendor_id: str,
    vendor_name: str,
    vendor_type: str,
    contract_value: float,
    vendor_domain: str,
    file_paths: list[str],
):
    """Run the full agent workflow (called as a background task)."""
    try:
        result = run_full_workflow(
            vendor_id=vendor_id,
            vendor_name=vendor_name,
            vendor_type=vendor_type,
            contract_value=contract_value,
            vendor_domain=vendor_domain,
            file_paths=file_paths,
        )
        logger.info(
            f"Workflow completed for vendor {vendor_id}: {result.get('status')}"
        )
    except Exception as e:
        logger.error(f"Workflow background task failed: {e}")
        update_vendor(vendor_id, {"status": "error"})


# ═══════════════════════════════════════════════════════════════════
# Vendor Onboarding Endpoints
# ═══════════════════════════════════════════════════════════════════

@router.post("/vendors/onboard")
async def onboard_vendor(
    background_tasks: BackgroundTasks,
    vendor_name: str = Form(...),
    vendor_type: str = Form("technology"),
    contract_value: float = Form(0.0),
    vendor_domain: str = Form(""),
    contact_email: str = Form(""),
    contact_name: str = Form(""),
    files: list[UploadFile] = File(default=[]),
):
    """
    Start the vendor onboarding process.
    Accepts vendor details and document uploads, then triggers the
    multi-agent workflow in the background.
    """
    try:
        # Create vendor record
        vendor_data = {
            "name": vendor_name,
            "vendor_type": vendor_type,
            "contract_value": contract_value,
            "domain": vendor_domain,
            "contact_email": contact_email,
            "contact_name": contact_name,
            "status": "processing",
        }
        vendor = create_vendor(vendor_data)
        vendor_id = vendor.get("id")

        if not vendor_id:
            raise HTTPException(status_code=500, detail="Failed to create vendor record")

        # Save uploaded files
        settings = get_settings()
        upload_dir = os.path.join(settings.upload_dir, vendor_id)
        os.makedirs(upload_dir, exist_ok=True)

        file_paths = []
        for f in files:
            file_path = os.path.join(upload_dir, f.filename)
            content = await f.read()
            with open(file_path, "wb") as fp:
                fp.write(content)
            file_paths.append(file_path)
            logger.info(f"Saved file: {file_path}")

        # Trigger the multi-agent workflow in the background
        background_tasks.add_task(
            _run_workflow_sync,
            vendor_id=vendor_id,
            vendor_name=vendor_name,
            vendor_type=vendor_type,
            contract_value=contract_value,
            vendor_domain=vendor_domain,
            file_paths=file_paths,
        )

        return {
            "status": "accepted",
            "vendor_id": vendor_id,
            "message": f"Vendor '{vendor_name}' onboarding started. {len(file_paths)} files uploaded.",
            "files_uploaded": [f.filename for f in files],
            "status_url": f"/api/v1/vendors/{vendor_id}/status",
            "report_url": f"/api/v1/vendors/{vendor_id}/report",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Vendor onboarding failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vendors/{vendor_id}/status")
async def get_vendor_status(vendor_id: str):
    """
    Get the current status and progress of a vendor review workflow.
    """
    vendor = get_vendor(vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    # Check Redis for active state
    active_state = load_state(vendor_id)

    return {
        "vendor_id": vendor_id,
        "vendor_name": vendor.get("name"),
        "status": vendor.get("status"),
        "current_phase": (
            active_state.get("current_phase") if active_state else vendor.get("status")
        ),
        "current_agent": (
            active_state.get("current_agent", "") if active_state else ""
        ),
        "progress_percentage": (
            active_state.get("progress_percentage", 0) if active_state else (
                100 if vendor.get("status") == "review_completed" else 0
            )
        ),
        "errors": (
            active_state.get("errors", []) if active_state else []
        ),
    }


@router.get("/vendors/{vendor_id}/report")
async def get_vendor_report(vendor_id: str):
    """
    Get the complete vendor assessment report including all findings.
    """
    vendor = get_vendor(vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    documents = get_documents_for_vendor(vendor_id)
    security_review = get_security_review(vendor_id)
    compliance_rev = get_compliance_review(vendor_id)
    financial_rev = get_financial_review(vendor_id)
    evidence_reqs = get_evidence_requests(vendor_id)
    audit_trail = get_audit_logs(vendor_id)

    return {
        "vendor": {
            "id": vendor.get("id"),
            "name": vendor.get("name"),
            "type": vendor.get("vendor_type"),
            "contract_value": float(vendor.get("contract_value", 0)),
            "domain": vendor.get("domain"),
            "status": vendor.get("status"),
        },
        "documents": {
            "total": len(documents),
            "items": [
                {
                    "id": d.get("id"),
                    "file_name": d.get("file_name"),
                    "classification": d.get("classification"),
                    "classification_confidence": float(
                        d.get("classification_confidence", 0)
                    ),
                    "processing_status": d.get("processing_status"),
                    "extracted_dates": d.get("extracted_dates", {}),
                }
                for d in documents
            ],
        },
        "security_review": (
            {
                "overall_score": float(security_review.get("overall_score", 0)),
                "grade": security_review.get("grade"),
                "status": security_review.get("status"),
                "report": security_review.get("report", {}),
            }
            if security_review
            else None
        ),
        "compliance_review": (
            {
                "overall_score": float(compliance_rev.get("overall_score", 0)),
                "grade": compliance_rev.get("grade"),
                "status": compliance_rev.get("status"),
                "report": compliance_rev.get("report", {}),
            }
            if compliance_rev
            else None
        ),
        "financial_review": (
            {
                "overall_score": float(financial_rev.get("overall_score", 0)),
                "grade": financial_rev.get("grade"),
                "status": financial_rev.get("status"),
                "report": financial_rev.get("report", {}),
            }
            if financial_rev
            else None
        ),
        "evidence_gaps": {
            "total": len(evidence_reqs),
            "pending": sum(1 for r in evidence_reqs if r.get("status") == "pending"),
            "received": sum(1 for r in evidence_reqs if r.get("status") == "received"),
        },
        "audit_trail": [
            {
                "agent": log.get("agent_name"),
                "action": log.get("action"),
                "tool": log.get("tool_name"),
                "status": log.get("status"),
                "duration_ms": log.get("duration_ms"),
                "timestamp": log.get("created_at"),
            }
            for log in audit_trail
        ],
    }


# ═══════════════════════════════════════════════════════════════════
# Document Management Endpoints
# ═══════════════════════════════════════════════════════════════════

@router.post("/vendors/{vendor_id}/documents")
async def upload_additional_documents(
    vendor_id: str,
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
):
    """Upload additional documents for a vendor and trigger re-processing."""
    vendor = get_vendor(vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    settings = get_settings()
    upload_dir = os.path.join(settings.upload_dir, vendor_id)
    os.makedirs(upload_dir, exist_ok=True)

    file_paths = []
    for f in files:
        file_path = os.path.join(upload_dir, f.filename)
        content = await f.read()
        with open(file_path, "wb") as fp:
            fp.write(content)
        file_paths.append(file_path)

    # Re-run intake agent in background
    from app.agents.document_intake import run_intake_agent

    background_tasks.add_task(run_intake_agent, vendor_id, file_paths)

    return {
        "status": "accepted",
        "vendor_id": vendor_id,
        "files_uploaded": [f.filename for f in files],
        "message": "Documents uploaded and processing started.",
    }


@router.get("/vendors/{vendor_id}/documents")
async def list_vendor_documents(vendor_id: str):
    """List all documents for a vendor with classifications and metadata."""
    vendor = get_vendor(vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    documents = get_documents_for_vendor(vendor_id)

    return {
        "vendor_id": vendor_id,
        "vendor_name": vendor.get("name"),
        "total_documents": len(documents),
        "documents": [
            {
                "id": d.get("id"),
                "file_name": d.get("file_name"),
                "file_type": d.get("file_type"),
                "classification": d.get("classification"),
                "classification_confidence": float(
                    d.get("classification_confidence", 0)
                ),
                "extracted_metadata": d.get("extracted_metadata", {}),
                "extracted_dates": d.get("extracted_dates", {}),
                "processing_status": d.get("processing_status"),
                "created_at": d.get("created_at"),
            }
            for d in documents
        ],
    }


# ═══════════════════════════════════════════════════════════════════
# Security Review Endpoints
# ═══════════════════════════════════════════════════════════════════

@router.get("/vendors/{vendor_id}/security")
async def get_security_findings(vendor_id: str):
    """Get the security review findings for a vendor."""
    vendor = get_vendor(vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    review = get_security_review(vendor_id)
    if not review:
        return {
            "vendor_id": vendor_id,
            "status": "not_started",
            "message": "No security review has been completed for this vendor.",
        }

    return {
        "vendor_id": vendor_id,
        "vendor_name": vendor.get("name"),
        "security_review": {
            "overall_score": float(review.get("overall_score", 0)),
            "grade": review.get("grade"),
            "component_scores": {
                "certificates": float(review.get("certificate_score", 0)),
                "domain_security": float(review.get("domain_security_score", 0)),
                "breach_history": float(review.get("breach_history_score", 0)),
                "questionnaire": float(review.get("questionnaire_score", 0)),
            },
            "findings": review.get("findings", []),
            "critical_issues": review.get("critical_issues", []),
            "recommendations": review.get("recommendations", []),
            "report": review.get("report", {}),
            "status": review.get("status"),
            "completed_at": review.get("completed_at"),
        },
    }


# ═══════════════════════════════════════════════════════════════════
# Compliance Review Endpoints (Phase 2)
# ═══════════════════════════════════════════════════════════════════

@router.get("/vendors/{vendor_id}/compliance")
async def get_compliance_findings(vendor_id: str):
    """Get the compliance review findings for a vendor."""
    vendor = get_vendor(vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    review = get_compliance_review(vendor_id)
    if not review:
        return {
            "vendor_id": vendor_id,
            "status": "not_started",
            "message": "No compliance review has been completed for this vendor.",
        }

    return {
        "vendor_id": vendor_id,
        "vendor_name": vendor.get("name"),
        "compliance_review": {
            "overall_score": float(review.get("overall_score", 0)),
            "grade": review.get("grade"),
            "component_scores": {
                "gdpr": float(review.get("gdpr_score", 0)),
                "hipaa": float(review.get("hipaa_score", 0)),
                "pci": float(review.get("pci_score", 0)),
                "dpa": float(review.get("dpa_score", 0)),
                "privacy_policy": float(review.get("privacy_policy_score", 0)),
            },
            "applicable_regulations": review.get("applicable_regulations", []),
            "findings": review.get("findings", []),
            "gaps": review.get("gaps", []),
            "recommendations": review.get("recommendations", []),
            "report": review.get("report", {}),
            "status": review.get("status"),
        },
    }


# ═══════════════════════════════════════════════════════════════════
# Financial Review Endpoints (Phase 2)
# ═══════════════════════════════════════════════════════════════════

@router.get("/vendors/{vendor_id}/financial")
async def get_financial_findings(vendor_id: str):
    """Get the financial review findings for a vendor."""
    vendor = get_vendor(vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    review = get_financial_review(vendor_id)
    if not review:
        return {
            "vendor_id": vendor_id,
            "status": "not_started",
            "message": "No financial review has been completed for this vendor.",
        }

    return {
        "vendor_id": vendor_id,
        "vendor_name": vendor.get("name"),
        "financial_review": {
            "overall_score": float(review.get("overall_score", 0)),
            "grade": review.get("grade"),
            "component_scores": {
                "insurance": float(review.get("insurance_score", 0)),
                "credit_rating": float(review.get("credit_rating_score", 0)),
                "financial_stability": float(review.get("financial_stability_score", 0)),
                "bcp": float(review.get("bcp_score", 0)),
            },
            "insurance_details": review.get("insurance_details", {}),
            "credit_details": review.get("credit_details", {}),
            "findings": review.get("findings", []),
            "recommendations": review.get("recommendations", []),
            "report": review.get("report", {}),
            "status": review.get("status"),
        },
    }


# ═══════════════════════════════════════════════════════════════════
# Evidence Coordination Endpoints (Phase 2)
# ═══════════════════════════════════════════════════════════════════

@router.get("/vendors/{vendor_id}/evidence-gaps")
async def get_evidence_gaps(vendor_id: str):
    """List missing documents and evidence gaps for a vendor."""
    vendor = get_vendor(vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    requests = get_evidence_requests(vendor_id)
    pending = [r for r in requests if r.get("status") == "pending"]
    received = [r for r in requests if r.get("status") == "received"]

    return {
        "vendor_id": vendor_id,
        "vendor_name": vendor.get("name"),
        "total_requests": len(requests),
        "pending": len(pending),
        "received": len(received),
        "completion_percentage": round((len(received) / max(len(requests), 1)) * 100, 1),
        "evidence_requests": [
            {
                "id": r.get("id"),
                "document_type": r.get("document_type"),
                "criticality": r.get("criticality"),
                "reason": r.get("reason"),
                "status": r.get("status"),
                "email_sent": r.get("email_sent"),
                "deadline": r.get("deadline"),
                "created_at": r.get("created_at"),
            }
            for r in requests
        ],
    }


@router.post("/vendors/{vendor_id}/request-evidence")
async def trigger_evidence_request(
    vendor_id: str,
    background_tasks: BackgroundTasks,
):
    """Manually trigger evidence request coordination for a vendor."""
    vendor = get_vendor(vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    from app.agents.evidence_coordinator import run_evidence_coordinator
    background_tasks.add_task(run_evidence_coordinator, vendor_id)

    return {
        "status": "accepted",
        "vendor_id": vendor_id,
        "message": "Evidence coordination triggered.",
    }


@router.get("/vendors/{vendor_id}/evidence-status")
async def get_evidence_status(vendor_id: str):
    """Track evidence collection progress for a vendor."""
    vendor = get_vendor(vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    requests = get_evidence_requests(vendor_id)
    tracking = get_evidence_tracking(vendor_id)

    return {
        "vendor_id": vendor_id,
        "vendor_name": vendor.get("name"),
        "evidence_requests": len(requests),
        "tracking_entries": len(tracking),
        "requests": [
            {
                "id": r.get("id"),
                "document_type": r.get("document_type"),
                "status": r.get("status"),
                "email_sent": r.get("email_sent"),
                "deadline": r.get("deadline"),
            }
            for r in requests
        ],
        "recent_tracking": [
            {
                "action": t.get("action"),
                "actor": t.get("actor"),
                "details": t.get("details"),
                "created_at": t.get("created_at"),
            }
            for t in tracking[-10:]
        ],
    }


@router.post("/vendors/{vendor_id}/evidence/{doc_type}/received")
async def mark_evidence_received(vendor_id: str, doc_type: str):
    """Mark a document type as received for a vendor."""
    vendor = get_vendor(vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    requests = get_evidence_requests(vendor_id)
    matched = [r for r in requests if r.get("document_type") == doc_type and r.get("status") == "pending"]

    if not matched:
        raise HTTPException(status_code=404, detail=f"No pending evidence request found for '{doc_type}'")

    from datetime import timezone as tz
    for req in matched:
        update_evidence_request(req["id"], {
            "status": "received",
            "response_received_at": datetime.now(tz.utc).isoformat(),
        })

    return {
        "status": "success",
        "vendor_id": vendor_id,
        "document_type": doc_type,
        "requests_updated": len(matched),
        "message": f"Document type '{doc_type}' marked as received.",
    }


# ═══════════════════════════════════════════════════════════════════
# Admin Endpoints
# ═══════════════════════════════════════════════════════════════════

@router.post("/policies/{policy_type}")
async def upload_policy(policy_type: str, request: PolicyUploadRequest):
    """
    Upload a policy document (security, compliance, or financial).
    Generates embeddings and stores in the Qdrant vector database for RAG search.
    """
    valid_types = ["security", "compliance", "financial"]
    if policy_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid policy type. Must be one of: {valid_types}",
        )

    try:
        policy_data = {
            "title": request.title,
            "content": request.content,
            "category": policy_type,
            "source": request.source,
            "version": request.version,
            "is_active": True,
        }
        policy = create_policy(policy_data)
        policy_id = policy.get("id", str(uuid.uuid4()))

        collection = f"{policy_type}_policies"
        upsert_policy(
            collection=collection,
            policy_id=policy_id,
            title=request.title,
            content=request.content,
            metadata={
                "source": request.source,
                "version": request.version,
                "category": policy_type,
            },
        )

        return {
            "status": "success",
            "policy_id": policy_id,
            "policy_type": policy_type,
            "message": f"Policy '{request.title}' uploaded and indexed in {collection}.",
            "collection": collection,
        }

    except Exception as e:
        logger.error(f"Policy upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/policies")
async def list_policies(policy_type: str = ""):
    """List all policies, optionally filtered by type."""
    from app.core.db import get_active_policies
    if policy_type:
        policies = get_active_policies(category=policy_type)
    else:
        policies = []
        for cat in ["security", "compliance", "financial"]:
            policies.extend(get_active_policies(category=cat))

    return {
        "total": len(policies),
        "policies": [
            {
                "id": p.get("id"),
                "title": p.get("title"),
                "category": p.get("category"),
                "source": p.get("source"),
                "version": p.get("version"),
                "is_active": p.get("is_active"),
                "created_at": p.get("created_at"),
            }
            for p in policies
        ],
    }


@router.get("/health")
async def health_check():
    """
    System health check — verifies connectivity to all services.
    """
    db_ok = check_db_health()
    redis_ok = check_redis_health()
    vector_ok = check_vector_health()
    llm_status = check_llm_health()

    all_healthy = db_ok and redis_ok and vector_ok and llm_status.get("ollama", False)

    return {
        "status": "healthy" if all_healthy else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {
            "database": {"status": "up" if db_ok else "down", "type": "supabase"},
            "redis": {"status": "up" if redis_ok else "down"},
            "vector_store": {"status": "up" if vector_ok else "down", "type": "qdrant"},
            "llm": {
                "ollama": "up" if llm_status.get("ollama") else "down",
                "groq": "up" if llm_status.get("groq") else "down",
            },
        },
    }
