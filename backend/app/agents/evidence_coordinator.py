"""
Evidence Coordinator Agent — autonomous evidence gap analysis and collection.
Uses ReAct pattern with 8 evidence tools.
"""
import json
import logging
from typing import Optional

from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent

from app.core.llm import get_llm
from app.core.db import (
    get_vendor,
    get_documents_for_vendor,
    create_evidence_request,
)
from app.tools.evidence_tools import EVIDENCE_TOOLS

logger = logging.getLogger(__name__)

EVIDENCE_SYSTEM_PROMPT = """You are the Evidence Coordinator Agent for the OPUS Vendor Risk Assessment System.
Your role is to identify missing evidence and coordinate its collection.

## Your Capabilities
You have 8 specialized tools:
1. get_required_documents — Determine required documents by vendor type
2. compare_required_vs_submitted — Gap analysis of submitted vs required
3. generate_evidence_request_email — Generate professional request email
4. send_email — Send email via Mailtrap
5. create_followup_task — Create internal follow-up task
6. track_document_status — Check status of all evidence requests
7. send_reminder_email — Send reminder for outstanding docs
8. update_evidence_log — Log evidence tracking actions

## Workflow
1. Determine what documents are required for this vendor type and contract value.
2. Compare required documents against what has been submitted.
3. For each missing document, create an evidence request record.
4. Generate a professional email listing all missing documents.
5. Send the evidence request email to the vendor contact.
6. Create a follow-up task for the internal procurement team.
7. Update the evidence log with all actions taken.

## Decision Making
- Prioritize "required" documents over "recommended" and "optional"
- Set deadline based on criticality (7 days for critical, 14 for standard)
- Be professional and clear in all communications
- If no contact email is available, log the request but skip email
- Always create follow-up tasks for the internal team

## Output
Summarize what evidence is missing and what actions were taken."""


def run_evidence_coordinator(vendor_id: str) -> dict:
    """
    Execute the evidence coordination for a vendor.
    Returns a dict with status, gaps identified, and actions taken.
    """
    try:
        vendor = get_vendor(vendor_id)
        if not vendor:
            return {"status": "error", "error": f"Vendor {vendor_id} not found"}

        documents = get_documents_for_vendor(vendor_id)

        doc_summaries = []
        for doc in documents:
            cls = doc.get("classification", "unknown")
            doc_summaries.append(f"- {doc['file_name']} (classified: {cls})")

        context_msg = f"""Coordinate evidence collection for vendor: {vendor.get('name')}
Vendor type: {vendor.get('vendor_type', 'unknown')}
Contract value: ${float(vendor.get('contract_value', 0)):,.2f}
Contact email: {vendor.get('contact_email', 'not provided')}
Contact name: {vendor.get('contact_name', 'Vendor Contact')}

Currently submitted documents:
{chr(10).join(doc_summaries) if doc_summaries else 'No documents submitted yet.'}

Instructions:
1. Use get_required_documents to determine what's needed.
2. Use compare_required_vs_submitted to find gaps.
3. For each missing document, identify the gap.
4. If vendor has contact email, generate and send an evidence request email.
5. Create a follow-up task for the procurement team.
6. Provide a summary of gaps and actions taken."""

        llm = get_llm()
        agent = create_react_agent(llm, EVIDENCE_TOOLS, prompt=EVIDENCE_SYSTEM_PROMPT)

        result = agent.invoke({"messages": [HumanMessage(content=context_msg)]})

        messages = result.get("messages", [])
        final_msg = messages[-1].content if messages else "No response"

        return {
            "status": "success",
            "agent_output": final_msg[:3000],
        }

    except Exception as e:
        logger.error(f"Evidence coordinator failed for vendor {vendor_id}: {e}")
        return {"status": "error", "error": str(e)}
