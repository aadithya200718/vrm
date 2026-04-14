"""
Supervisor Agent tools — 6 tools for orchestrating the multi-agent workflow.
Updated for Phase 2: full delegation to Compliance, Financial, and Evidence agents.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from langchain_core.tools import tool

from app.core.db import (
    get_vendor,
    get_documents_for_vendor,
    get_security_review,
    get_compliance_review,
    get_financial_review,
    get_evidence_requests,
    get_audit_logs,
    create_security_review,
    create_compliance_review,
    create_financial_review,
    update_vendor,
)
from app.core.redis_state import load_state

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# Tool 1: delegate_to_security_agent
# ═══════════════════════════════════════════════════════════════════

@tool
def delegate_to_security_agent(vendor_id: str) -> str:
    """
    Create a security review task for the Security Review Agent.
    Passes the vendor context and document data needed for the review.

    Args:
        vendor_id: The vendor UUID to start a security review for.
    """
    try:
        vendor = get_vendor(vendor_id)
        if not vendor:
            return json.dumps({
                "status": "error",
                "error": f"Vendor {vendor_id} not found",
            })

        documents = get_documents_for_vendor(vendor_id)

        # Create the security review record
        review = create_security_review({
            "vendor_id": vendor_id,
            "status": "in_progress",
            "started_at": datetime.now(timezone.utc).isoformat(),
        })

        return json.dumps({
            "status": "success",
            "task_id": review.get("id", ""),
            "vendor_name": vendor.get("name", ""),
            "vendor_domain": vendor.get("domain", ""),
            "document_count": len(documents),
            "document_classifications": [
                d.get("classification", "unknown") for d in documents
            ],
            "message": "Security review task created. Agent will now assess the vendor.",
        })

    except Exception as e:
        logger.error(f"Failed to delegate to security agent: {e}")
        return json.dumps({"status": "error", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════
# Tool 2: delegate_to_compliance_agent
# ═══════════════════════════════════════════════════════════════════

@tool
def delegate_to_compliance_agent(vendor_id: str) -> str:
    """
    Delegate a compliance review task to the Compliance Agent.
    Creates a compliance_reviews record and passes vendor context.

    Args:
        vendor_id: The vendor UUID to review.
    """
    try:
        vendor = get_vendor(vendor_id)
        if not vendor:
            return json.dumps({"status": "error", "error": f"Vendor {vendor_id} not found"})

        documents = get_documents_for_vendor(vendor_id)

        review = create_compliance_review({
            "vendor_id": vendor_id,
            "status": "in_progress",
            "started_at": datetime.now(timezone.utc).isoformat(),
        })

        return json.dumps({
            "status": "success",
            "task_id": review.get("id", ""),
            "vendor_name": vendor.get("name", ""),
            "vendor_type": vendor.get("vendor_type", ""),
            "document_count": len(documents),
            "document_classifications": [
                d.get("classification", "unknown") for d in documents
            ],
            "message": "Compliance review task created. Agent will assess regulatory compliance.",
        })

    except Exception as e:
        logger.error(f"Failed to delegate to compliance agent: {e}")
        return json.dumps({"status": "error", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════
# Tool 3: delegate_to_financial_agent
# ═══════════════════════════════════════════════════════════════════

@tool
def delegate_to_financial_agent(vendor_id: str) -> str:
    """
    Delegate a financial review task to the Financial Agent.
    Creates a financial_reviews record and passes vendor context.

    Args:
        vendor_id: The vendor UUID to review.
    """
    try:
        vendor = get_vendor(vendor_id)
        if not vendor:
            return json.dumps({"status": "error", "error": f"Vendor {vendor_id} not found"})

        documents = get_documents_for_vendor(vendor_id)

        review = create_financial_review({
            "vendor_id": vendor_id,
            "status": "in_progress",
            "started_at": datetime.now(timezone.utc).isoformat(),
        })

        return json.dumps({
            "status": "success",
            "task_id": review.get("id", ""),
            "vendor_name": vendor.get("name", ""),
            "contract_value": float(vendor.get("contract_value", 0)),
            "document_count": len(documents),
            "document_classifications": [
                d.get("classification", "unknown") for d in documents
            ],
            "message": "Financial review task created. Agent will assess financial risk.",
        })

    except Exception as e:
        logger.error(f"Failed to delegate to financial agent: {e}")
        return json.dumps({"status": "error", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════
# Tool 4: delegate_to_evidence_agent
# ═══════════════════════════════════════════════════════════════════

@tool
def delegate_to_evidence_agent(vendor_id: str) -> str:
    """
    Delegate an evidence coordination task to the Evidence Coordinator Agent.
    Passes all review findings so the agent can identify gaps.

    Args:
        vendor_id: The vendor UUID to review.
    """
    try:
        vendor = get_vendor(vendor_id)
        if not vendor:
            return json.dumps({"status": "error", "error": f"Vendor {vendor_id} not found"})

        documents = get_documents_for_vendor(vendor_id)
        security = get_security_review(vendor_id)
        compliance = get_compliance_review(vendor_id)
        financial = get_financial_review(vendor_id)

        context = {
            "status": "success",
            "vendor_name": vendor.get("name", ""),
            "vendor_type": vendor.get("vendor_type", ""),
            "contract_value": float(vendor.get("contract_value", 0)),
            "contact_email": vendor.get("contact_email", ""),
            "contact_name": vendor.get("contact_name", ""),
            "document_count": len(documents),
            "reviews_completed": {
                "security": security.get("status") if security else "not_started",
                "compliance": compliance.get("status") if compliance else "not_started",
                "financial": financial.get("status") if financial else "not_started",
            },
            "message": "Evidence coordination task created. Agent will identify gaps and request missing documents.",
        }

        return json.dumps(context)

    except Exception as e:
        logger.error(f"Failed to delegate to evidence agent: {e}")
        return json.dumps({"status": "error", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════
# Tool 5: compile_approval_packet
# ═══════════════════════════════════════════════════════════════════

@tool
def compile_approval_packet(vendor_id: str) -> str:
    """
    Compile all review findings into a comprehensive approval packet.
    Aggregates security, compliance, financial reviews, document data, evidence gaps, and audit trail.

    Args:
        vendor_id: The vendor UUID to compile results for.
    """
    try:
        vendor = get_vendor(vendor_id)
        if not vendor:
            return json.dumps({"status": "error", "error": f"Vendor {vendor_id} not found"})

        documents = get_documents_for_vendor(vendor_id)
        security_review = get_security_review(vendor_id)
        compliance_review = get_compliance_review(vendor_id)
        financial_review = get_financial_review(vendor_id)
        evidence_reqs = get_evidence_requests(vendor_id)
        audit_trail = get_audit_logs(vendor_id)

        # Build review summaries
        def build_review_summary(review, name):
            if not review:
                return {"status": "not_completed"}
            return {
                "score": float(review.get("overall_score", 0)),
                "grade": review.get("grade", "N/A"),
                "status": review.get("status"),
                "report": review.get("report", {}),
            }

        sec_summary = build_review_summary(security_review, "security")
        comp_summary = build_review_summary(compliance_review, "compliance")
        fin_summary = build_review_summary(financial_review, "financial")

        # Compute aggregate score
        scores = []
        if security_review and security_review.get("overall_score"):
            scores.append(float(security_review["overall_score"]))
        if compliance_review and compliance_review.get("overall_score"):
            scores.append(float(compliance_review["overall_score"]))
        if financial_review and financial_review.get("overall_score"):
            scores.append(float(financial_review["overall_score"]))

        avg_score = round(sum(scores) / max(len(scores), 1), 2)

        # Recommendation
        if avg_score >= 70 and not any(
            r.get("criticality") == "required" and r.get("status") == "pending"
            for r in evidence_reqs
        ):
            recommendation = "APPROVE"
        elif avg_score >= 50:
            recommendation = "CONDITIONAL_APPROVE"
        elif scores:
            recommendation = "REJECT"
        else:
            recommendation = "PENDING_REVIEW"

        packet = {
            "status": "success",
            "approval_packet": {
                "vendor": {
                    "id": vendor.get("id"),
                    "name": vendor.get("name"),
                    "type": vendor.get("vendor_type"),
                    "contract_value": float(vendor.get("contract_value", 0)),
                    "domain": vendor.get("domain"),
                },
                "documents": {
                    "total": len(documents),
                    "classifications": [
                        {
                            "file_name": d.get("file_name"),
                            "classification": d.get("classification"),
                            "status": d.get("processing_status"),
                        }
                        for d in documents
                    ],
                },
                "security_review": sec_summary,
                "compliance_review": comp_summary,
                "financial_review": fin_summary,
                "aggregate_score": avg_score,
                "evidence_gaps": {
                    "total_requests": len(evidence_reqs),
                    "pending": sum(1 for r in evidence_reqs if r.get("status") == "pending"),
                    "received": sum(1 for r in evidence_reqs if r.get("status") == "received"),
                },
                "recommendation": recommendation,
                "audit_trail_count": len(audit_trail),
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
        }

        return json.dumps(packet, default=str)

    except Exception as e:
        logger.error(f"Failed to compile approval packet: {e}")
        return json.dumps({"status": "error", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════
# Tool 6: get_worker_status
# ═══════════════════════════════════════════════════════════════════

@tool
def get_worker_status(vendor_id: str) -> str:
    """
    Get the current status and progress of the vendor review workflow.

    Args:
        vendor_id: The vendor UUID to check status for.
    """
    try:
        # Check Redis for active state
        state = load_state(vendor_id)

        if state:
            return json.dumps({
                "status": "success",
                "vendor_id": vendor_id,
                "current_phase": state.get("current_phase", "unknown"),
                "current_agent": state.get("current_agent", ""),
                "progress_percentage": state.get("progress_percentage", 0),
                "errors": state.get("errors", []),
                "message_count": len(state.get("messages", [])),
            })

        # Fallback to database
        vendor = get_vendor(vendor_id)
        if not vendor:
            return json.dumps({
                "status": "error",
                "error": f"Vendor {vendor_id} not found",
            })

        return json.dumps({
            "status": "success",
            "vendor_id": vendor_id,
            "current_phase": vendor.get("status", "unknown"),
            "progress_percentage": 0,
            "message": "No active workflow found in Redis; returning DB status.",
        })

    except Exception as e:
        logger.error(f"Failed to get worker status: {e}")
        return json.dumps({"status": "error", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════
# Collect all supervisor tools
# ═══════════════════════════════════════════════════════════════════

SUPERVISOR_TOOLS = [
    delegate_to_security_agent,
    delegate_to_compliance_agent,
    delegate_to_financial_agent,
    delegate_to_evidence_agent,
    compile_approval_packet,
    get_worker_status,
]
