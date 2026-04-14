"""
Evidence Coordinator Agent tools — 8 tools for evidence gap analysis and collection.
Uses Mailtrap for email delivery.
"""
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx
from langchain_core.tools import tool

from app.core.db import (
    get_vendor,
    get_documents_for_vendor,
    get_evidence_requests,
    create_evidence_request,
    update_evidence_request,
    create_evidence_tracking_entry,
    get_evidence_tracking,
)
from app.core.llm import get_llm
from app.config import get_settings

logger = logging.getLogger(__name__)


# Required documents by vendor type and contract value
DOCUMENT_REQUIREMENTS = {
    # Base requirements for all vendors
    "base": [
        {"type": "security_questionnaire", "criticality": "required", "reason": "Standard security assessment form"},
        {"type": "privacy_policy", "criticality": "required", "reason": "Data handling and privacy practices"},
        {"type": "insurance_certificate", "criticality": "required", "reason": "Insurance coverage verification"},
    ],
    # Additional for SaaS / technology vendors
    "technology": [
        {"type": "soc2_report", "criticality": "required", "reason": "SOC 2 Type II audit report for security assurance"},
        {"type": "penetration_test", "criticality": "required", "reason": "Third-party security testing results"},
        {"type": "data_processing_agreement", "criticality": "required", "reason": "GDPR Article 28 DPA"},
        {"type": "business_continuity_plan", "criticality": "recommended", "reason": "Disaster recovery and BCP documentation"},
        {"type": "subprocessor_list", "criticality": "required", "reason": "List of sub-processors handling data"},
    ],
    # Additional for high-value contracts (> $100K)
    "high_value": [
        {"type": "financial_statement", "criticality": "required", "reason": "Financial stability verification"},
        {"type": "iso27001_certificate", "criticality": "recommended", "reason": "ISO 27001 certification for InfoSec"},
        {"type": "cyber_insurance", "criticality": "required", "reason": "Dedicated cyber insurance coverage"},
    ],
    # Healthcare-related vendors
    "healthcare": [
        {"type": "baa", "criticality": "required", "reason": "HIPAA Business Associate Agreement"},
        {"type": "hipaa_assessment", "criticality": "required", "reason": "HIPAA compliance assessment"},
    ],
    # Financial services vendors
    "financial": [
        {"type": "pci_aoc", "criticality": "required", "reason": "PCI-DSS Attestation of Compliance"},
    ],
}


# ═══════════════════════════════════════════════════════════════════
# Tool 1: get_required_documents
# ═══════════════════════════════════════════════════════════════════

@tool
def get_required_documents(vendor_type: str, contract_value: float) -> str:
    """
    Determine the list of required documents for a given vendor type and contract value.

    Args:
        vendor_type: Type of vendor (technology, healthcare, financial, consulting, etc.).
        contract_value: Contract value in USD.
    """
    try:
        required = list(DOCUMENT_REQUIREMENTS["base"])

        # Add type-specific documents
        vendor_type_lower = vendor_type.lower()
        if vendor_type_lower in ("technology", "saas", "software", "cloud"):
            required.extend(DOCUMENT_REQUIREMENTS["technology"])
        if vendor_type_lower in ("healthcare", "medical", "health"):
            required.extend(DOCUMENT_REQUIREMENTS["healthcare"])
        if vendor_type_lower in ("financial", "fintech", "banking"):
            required.extend(DOCUMENT_REQUIREMENTS["financial"])

        # Add high-value requirements
        if contract_value > 100_000:
            required.extend(DOCUMENT_REQUIREMENTS["high_value"])

        return json.dumps({
            "status": "success",
            "vendor_type": vendor_type,
            "contract_value": contract_value,
            "total_required": len(required),
            "documents": required,
        })
    except Exception as e:
        logger.error(f"Get required documents failed: {e}")
        return json.dumps({"status": "error", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════
# Tool 2: compare_required_vs_submitted
# ═══════════════════════════════════════════════════════════════════

@tool
def compare_required_vs_submitted(vendor_id: str, required_docs_json: str) -> str:
    """
    Compare required documents against submitted documents.
    Identifies missing, submitted, and incomplete documents.

    Args:
        vendor_id: The vendor UUID.
        required_docs_json: JSON string of required document list from get_required_documents.
    """
    try:
        try:
            required_docs = json.loads(required_docs_json) if isinstance(required_docs_json, str) else required_docs_json
        except json.JSONDecodeError:
            required_docs = []

        if isinstance(required_docs, dict):
            required_docs = required_docs.get("documents", [])

        submitted = get_documents_for_vendor(vendor_id)

        # Build a set of classifications from submitted docs
        submitted_types = set()
        for doc in submitted:
            classification = (doc.get("classification") or "").lower().replace(" ", "_")
            submitted_types.add(classification)

        missing = []
        present = []
        for req in required_docs:
            doc_type = req.get("type", "").lower()
            # Check if any submitted doc matches
            found = any(doc_type in st for st in submitted_types)
            if found:
                present.append(req)
            else:
                missing.append(req)

        completion = round((len(present) / max(len(required_docs), 1)) * 100, 1)

        return json.dumps({
            "status": "success",
            "vendor_id": vendor_id,
            "total_required": len(required_docs),
            "total_submitted": len(submitted),
            "documents_present": len(present),
            "documents_missing": len(missing),
            "completion_percentage": completion,
            "missing_documents": missing,
            "present_documents": [p.get("type") for p in present],
        })
    except Exception as e:
        logger.error(f"Document comparison failed: {e}")
        return json.dumps({"status": "error", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════
# Tool 3: generate_evidence_request_email
# ═══════════════════════════════════════════════════════════════════

@tool
def generate_evidence_request_email(
    vendor_name: str,
    contact_name: str,
    missing_documents_json: str,
    deadline_days: int = 14,
) -> str:
    """
    Generate a professional evidence request email using LLM.

    Args:
        vendor_name: Name of the vendor.
        contact_name: Name of the vendor contact person.
        missing_documents_json: JSON string of missing documents.
        deadline_days: Number of days for the deadline (default 14).
    """
    try:
        try:
            missing_docs = json.loads(missing_documents_json) if isinstance(missing_documents_json, str) else missing_documents_json
        except json.JSONDecodeError:
            missing_docs = [{"type": missing_documents_json, "reason": "Required for review"}]

        deadline = (datetime.now(timezone.utc) + timedelta(days=deadline_days)).strftime("%B %d, %Y")

        llm = get_llm()
        prompt = f"""Generate a professional email requesting missing documents from a vendor.

Details:
- Vendor name: {vendor_name}
- Contact name: {contact_name}
- Deadline: {deadline}
- Missing documents:
{json.dumps(missing_docs, indent=2)}

Guidelines:
- Professional and courteous tone
- Clear subject line (include it as "Subject: ...")
- Personalized greeting
- Brief context about the vendor risk assessment
- Bulleted list of missing documents with reasons
- Clear deadline
- Upload instructions (reply to this email or upload to secure portal)
- Offer to help if questions
- Professional signature from "OPUS Vendor Risk Assessment Team"

Write the complete email."""

        response = llm.invoke(prompt)
        email_body = response.content if hasattr(response, "content") else str(response)

        # Extract subject line if present
        subject = f"Document Request - Vendor Risk Assessment for {vendor_name}"
        for line in email_body.split("\n"):
            if line.lower().startswith("subject:"):
                subject = line.split(":", 1)[1].strip()
                break

        return json.dumps({
            "status": "success",
            "subject": subject,
            "body": email_body,
            "deadline": deadline,
            "documents_requested": len(missing_docs),
        })
    except Exception as e:
        logger.error(f"Evidence request email generation failed: {e}")
        return json.dumps({"status": "error", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════
# Tool 4: send_email (Mailtrap)
# ═══════════════════════════════════════════════════════════════════

@tool
def send_email(
    to_email: str,
    subject: str,
    body: str,
    vendor_id: str = "",
) -> str:
    """
    Send an email via Mailtrap API.

    Args:
        to_email: Recipient email address.
        subject: Email subject line.
        body: Email body text.
        vendor_id: Optional vendor ID for tracking.
    """
    try:
        settings = get_settings()

        if not settings.mailtrap_api_key:
            logger.warning("Mailtrap API key not configured — logging email instead of sending.")
            logger.info(f"[EMAIL MOCK] To: {to_email} | Subject: {subject}")
            return json.dumps({
                "status": "success",
                "delivery": "mocked",
                "to_email": to_email,
                "subject": subject,
                "note": "Email logged — Mailtrap API key not configured.",
            })

        # Mailtrap Send API
        response = httpx.post(
            "https://send.api.mailtrap.io/api/send",
            headers={
                "Authorization": f"Bearer {settings.mailtrap_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": {
                    "email": settings.mailtrap_sender_email,
                    "name": settings.mailtrap_sender_name,
                },
                "to": [{"email": to_email}],
                "subject": subject,
                "text": body,
            },
            timeout=15,
        )

        if response.status_code in (200, 201, 202):
            result = response.json()
            return json.dumps({
                "status": "success",
                "delivery": "sent",
                "to_email": to_email,
                "subject": subject,
                "mailtrap_message_id": result.get("message_ids", [""])[0] if isinstance(result, dict) else "",
            })
        else:
            logger.error(f"Mailtrap send failed: {response.status_code} {response.text}")
            return json.dumps({
                "status": "error",
                "delivery": "failed",
                "error": f"Mailtrap API returned {response.status_code}: {response.text[:200]}",
            })

    except Exception as e:
        logger.error(f"Email sending failed: {e}")
        return json.dumps({"status": "error", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════
# Tool 5: create_followup_task
# ═══════════════════════════════════════════════════════════════════

@tool
def create_followup_task(
    vendor_id: str,
    task_description: str,
    assigned_to: str = "procurement",
    due_days: int = 7,
) -> str:
    """
    Create a follow-up task for the internal team to track evidence collection.

    Args:
        vendor_id: The vendor UUID.
        task_description: Description of what needs to be followed up on.
        assigned_to: Team or person to assign the task to.
        due_days: Number of days until the task is due.
    """
    try:
        due_date = (datetime.now(timezone.utc) + timedelta(days=due_days)).strftime("%Y-%m-%d")

        # Log to evidence tracking table
        entry = create_evidence_tracking_entry({
            "vendor_id": vendor_id,
            "action": "followup_task_created",
            "actor": "evidence_coordinator",
            "details": {
                "description": task_description,
                "assigned_to": assigned_to,
                "due_date": due_date,
            },
        })

        return json.dumps({
            "status": "success",
            "task_id": entry.get("id", ""),
            "description": task_description,
            "assigned_to": assigned_to,
            "due_date": due_date,
            "vendor_id": vendor_id,
            "note": "Task logged in evidence_tracking. Integrate with Jira/Asana for production.",
        })
    except Exception as e:
        logger.error(f"Follow-up task creation failed: {e}")
        return json.dumps({"status": "error", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════
# Tool 6: track_document_status
# ═══════════════════════════════════════════════════════════════════

@tool
def track_document_status(vendor_id: str) -> str:
    """
    Track the status of all evidence requests for a vendor.

    Args:
        vendor_id: The vendor UUID.
    """
    try:
        requests = get_evidence_requests(vendor_id)
        tracking = get_evidence_tracking(vendor_id)

        total = len(requests)
        received = sum(1 for r in requests if r.get("status") == "received")
        pending = sum(1 for r in requests if r.get("status") == "pending")
        overdue = 0
        for r in requests:
            if r.get("status") == "pending" and r.get("deadline"):
                try:
                    dl = datetime.strptime(r["deadline"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                    if dl < datetime.now(timezone.utc):
                        overdue += 1
                except (ValueError, TypeError):
                    pass

        completion = round((received / max(total, 1)) * 100, 1)

        return json.dumps({
            "status": "success",
            "vendor_id": vendor_id,
            "total_requests": total,
            "received": received,
            "pending": pending,
            "overdue": overdue,
            "completion_percentage": completion,
            "requests": [
                {
                    "id": r.get("id"),
                    "document_type": r.get("document_type"),
                    "criticality": r.get("criticality"),
                    "status": r.get("status"),
                    "email_sent": r.get("email_sent"),
                    "deadline": r.get("deadline"),
                }
                for r in requests
            ],
            "tracking_entries": len(tracking),
        })
    except Exception as e:
        logger.error(f"Document status tracking failed: {e}")
        return json.dumps({"status": "error", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════
# Tool 7: send_reminder_email
# ═══════════════════════════════════════════════════════════════════

@tool
def send_reminder_email(
    vendor_name: str,
    contact_name: str,
    contact_email: str,
    outstanding_docs_json: str,
    vendor_id: str = "",
) -> str:
    """
    Generate and send a polite reminder email for outstanding documents.

    Args:
        vendor_name: Name of the vendor.
        contact_name: Name of the vendor contact.
        contact_email: Email of the contact.
        outstanding_docs_json: JSON string of outstanding documents.
        vendor_id: Optional vendor ID for tracking.
    """
    try:
        try:
            outstanding = json.loads(outstanding_docs_json) if isinstance(outstanding_docs_json, str) else outstanding_docs_json
        except json.JSONDecodeError:
            outstanding = [{"type": outstanding_docs_json}]

        llm = get_llm()
        prompt = f"""Generate a polite but firm reminder email for outstanding vendor documents.

Vendor: {vendor_name}
Contact: {contact_name}
Outstanding documents: {json.dumps(outstanding)[:1500]}

Guidelines:
- Polite but firm reminder
- Subject line starts with "Reminder: ..."
- Reference previous request
- List outstanding items
- Emphasize urgency
- Offer support
- Professional signature from "OPUS Vendor Risk Assessment Team"
"""
        response = llm.invoke(prompt)
        email_body = response.content if hasattr(response, "content") else str(response)

        subject = f"Reminder: Outstanding Documents for {vendor_name} Risk Assessment"
        for line in email_body.split("\n"):
            if line.lower().startswith("subject:"):
                subject = line.split(":", 1)[1].strip()
                break

        # Send via Mailtrap
        send_result_raw = send_email.invoke({
            "to_email": contact_email,
            "subject": subject,
            "body": email_body,
            "vendor_id": vendor_id,
        })

        try:
            send_result = json.loads(send_result_raw) if isinstance(send_result_raw, str) else send_result_raw
        except json.JSONDecodeError:
            send_result = {"delivery": "unknown"}

        # Track
        if vendor_id:
            create_evidence_tracking_entry({
                "vendor_id": vendor_id,
                "action": "reminder_email_sent",
                "actor": "evidence_coordinator",
                "details": {
                    "to": contact_email,
                    "subject": subject,
                    "items_outstanding": len(outstanding),
                },
            })

        return json.dumps({
            "status": "success",
            "email_sent": True,
            "delivery": send_result.get("delivery", "unknown"),
            "subject": subject,
            "outstanding_count": len(outstanding),
        })
    except Exception as e:
        logger.error(f"Reminder email failed: {e}")
        return json.dumps({"status": "error", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════
# Tool 8: update_evidence_log
# ═══════════════════════════════════════════════════════════════════

@tool
def update_evidence_log(
    vendor_id: str,
    evidence_request_id: str,
    action: str,
    details_json: str = "{}",
) -> str:
    """
    Update the evidence tracking log for a specific request.

    Args:
        vendor_id: Vendor UUID.
        evidence_request_id: The evidence request ID.
        action: Action taken (e.g., 'request_sent', 'response_received', 'reviewed').
        details_json: JSON string of additional details.
    """
    try:
        try:
            details = json.loads(details_json) if isinstance(details_json, str) else details_json
        except json.JSONDecodeError:
            details = {"raw": details_json}

        # Create tracking entry
        entry = create_evidence_tracking_entry({
            "vendor_id": vendor_id,
            "evidence_request_id": evidence_request_id,
            "action": action,
            "actor": "evidence_coordinator",
            "details": details,
        })

        # Update request status if applicable
        status_map = {
            "request_sent": "pending",
            "response_received": "received",
            "reviewed": "reviewed",
            "rejected": "rejected",
        }
        if action in status_map:
            update_evidence_request(evidence_request_id, {
                "status": status_map[action],
                **({"email_sent": True, "email_sent_at": datetime.now(timezone.utc).isoformat()} if action == "request_sent" else {}),
                **({"response_received_at": datetime.now(timezone.utc).isoformat()} if action == "response_received" else {}),
            })

        return json.dumps({
            "status": "success",
            "tracking_entry_id": entry.get("id", ""),
            "action": action,
            "evidence_request_id": evidence_request_id,
            "vendor_id": vendor_id,
        })
    except Exception as e:
        logger.error(f"Evidence log update failed: {e}")
        return json.dumps({"status": "error", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════
# Collect all evidence tools
# ═══════════════════════════════════════════════════════════════════

EVIDENCE_TOOLS = [
    get_required_documents,
    compare_required_vs_submitted,
    generate_evidence_request_email,
    send_email,
    create_followup_task,
    track_document_status,
    send_reminder_email,
    update_evidence_log,
]
