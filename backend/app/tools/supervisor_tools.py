"""
Supervisor Agent tools — 6 tools for orchestrating the multi-agent workflow.
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
    get_audit_logs,
    create_security_review,
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
# Tool 2: delegate_to_compliance_agent (Placeholder)
# ═══════════════════════════════════════════════════════════════════

@tool
def delegate_to_compliance_agent(vendor_id: str) -> str:
    """
    Delegate a compliance review task to the Compliance Agent.
    NOTE: This agent is not yet implemented (Phase 2).

    Args:
        vendor_id: The vendor UUID to review.
    """
    return json.dumps({
        "status": "not_implemented",
        "message": "Compliance Review Agent will be available in Phase 2.",
        "vendor_id": vendor_id,
    })


# ═══════════════════════════════════════════════════════════════════
# Tool 3: delegate_to_financial_agent (Placeholder)
# ═══════════════════════════════════════════════════════════════════

@tool
def delegate_to_financial_agent(vendor_id: str) -> str:
    """
    Delegate a financial review task to the Financial Agent.
    NOTE: This agent is not yet implemented (Phase 2).

    Args:
        vendor_id: The vendor UUID to review.
    """
    return json.dumps({
        "status": "not_implemented",
        "message": "Financial Review Agent will be available in Phase 2.",
        "vendor_id": vendor_id,
    })


# ═══════════════════════════════════════════════════════════════════
# Tool 4: delegate_to_evidence_agent (Placeholder)
# ═══════════════════════════════════════════════════════════════════

@tool
def delegate_to_evidence_agent(vendor_id: str) -> str:
    """
    Delegate an evidence coordination task to the Evidence Agent.
    NOTE: This agent is not yet implemented (Phase 2).

    Args:
        vendor_id: The vendor UUID to review.
    """
    return json.dumps({
        "status": "not_implemented",
        "message": "Evidence Coordinator Agent will be available in Phase 2.",
        "vendor_id": vendor_id,
    })


# ═══════════════════════════════════════════════════════════════════
# Tool 5: compile_approval_packet
# ═══════════════════════════════════════════════════════════════════

@tool
def compile_approval_packet(vendor_id: str) -> str:
    """
    Compile all review findings into a comprehensive approval packet.
    Aggregates security review results, document data, and audit trail.

    Args:
        vendor_id: The vendor UUID to compile results for.
    """
    try:
        vendor = get_vendor(vendor_id)
        if not vendor:
            return json.dumps({
                "status": "error",
                "error": f"Vendor {vendor_id} not found",
            })

        documents = get_documents_for_vendor(vendor_id)
        security_review = get_security_review(vendor_id)
        audit_trail = get_audit_logs(vendor_id)

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
                "security_review": (
                    {
                        "score": float(security_review.get("overall_score", 0)),
                        "grade": security_review.get("grade", "N/A"),
                        "critical_issues": security_review.get("critical_issues", []),
                        "status": security_review.get("status"),
                        "report": security_review.get("report", {}),
                    }
                    if security_review
                    else {"status": "not_completed"}
                ),
                "audit_trail_count": len(audit_trail),
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
        }

        # Determine overall recommendation
        if security_review:
            score = float(security_review.get("overall_score", 0))
            if score >= 70:
                packet["approval_packet"]["recommendation"] = "APPROVE"
            elif score >= 50:
                packet["approval_packet"]["recommendation"] = "CONDITIONAL_APPROVE"
            else:
                packet["approval_packet"]["recommendation"] = "REJECT"
        else:
            packet["approval_packet"]["recommendation"] = "PENDING_REVIEW"

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
