"""
Security Review Agent — autonomous security assessment with ReAct pattern.
"""
import json
import logging

from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent

from app.core.llm import get_llm
from app.core.db import (
    get_documents_for_vendor,
    get_vendor,
    update_security_review,
    get_security_review,
)
from app.tools.security_tools import SECURITY_TOOLS

logger = logging.getLogger(__name__)

SECURITY_SYSTEM_PROMPT = """You are the Security Review Agent for a Vendor Risk Assessment system.

Your role is to autonomously and comprehensively assess the security posture of a vendor.
You use the ReAct pattern: Reason about what to do → Act by calling tools → Observe results → Repeat.

ASSESSMENT WORKFLOW:
1. **Search Internal Policies**: Use search_security_policies to find relevant security requirements
2. **Validate Certifications**: If SOC2 or ISO27001 documents are available, validate them
3. **Check Certificate Expiry**: Verify any certificates are not expired
4. **Scan Domain Security**: If a domain is provided, scan SSL/TLS and security headers
5. **Check Breach History**: Search for any data breaches involving the vendor
6. **Analyze Questionnaire**: If a security questionnaire is available, analyze it
7. **Calculate Score**: Use all findings to calculate an overall security score
8. **Flag Critical Issues**: Identify any blocking issues
9. **Generate Report**: Compile a comprehensive security assessment report

RULES:
- Be thorough — check every available piece of evidence
- If certain documents are missing, note it but continue with what's available
- Always calculate a security score even if some data is missing
- Flag any critical issues that would block approval
- Generate a complete report with findings and recommendations
- Use your judgment to adapt — if something seems suspicious, investigate further
- Use certificate scores of 0 if no certificates were submitted

SCORING GUIDE:
- Certificates (40%): SOC2 Type 2 + ISO27001 = 100, SOC2 only = 70, ISO only = 60, None = 0
- Domain Security (30%): Based on SSL + Headers scan score
- Breach History (20%): No breaches = 100, 1 breach = 60, 2+ = 30, 3+ = 0
- Questionnaire (10%): Based on questionnaire analysis score, or 50 if none submitted

When done, provide a clear summary with the overall score, grade, and recommendation.
"""


def create_security_agent():
    """Create the Security Review Agent using the ReAct pattern."""
    llm = get_llm()
    agent = create_react_agent(
        llm,
        SECURITY_TOOLS,
        prompt=SECURITY_SYSTEM_PROMPT,
    )
    return agent


def run_security_agent(vendor_id: str) -> dict:
    """
    Run the Security Review Agent for a vendor.

    Args:
        vendor_id: The vendor UUID to assess

    Returns:
        dict with security assessment results
    """
    try:
        agent = create_security_agent()

        # Gather context
        vendor = get_vendor(vendor_id)
        documents = get_documents_for_vendor(vendor_id)

        if not vendor:
            return {
                "status": "error",
                "error": f"Vendor {vendor_id} not found",
            }

        # Build document context
        doc_context = []
        for doc in documents:
            doc_context.append(
                f"- {doc.get('file_name')} "
                f"(Classification: {doc.get('classification', 'unknown')}, "
                f"Status: {doc.get('processing_status', 'unknown')})"
            )

        # Find relevant document texts
        soc2_texts = [
            doc.get("extracted_text", "")[:3000]
            for doc in documents
            if doc.get("classification") == "SOC2"
        ]
        iso_texts = [
            doc.get("extracted_text", "")[:3000]
            for doc in documents
            if doc.get("classification") == "ISO27001"
        ]
        questionnaire_texts = [
            doc.get("extracted_text", "")[:3000]
            for doc in documents
            if doc.get("classification") == "Security_Questionnaire"
        ]

        # Build the assessment task
        task = f"""Perform a comprehensive security assessment for vendor: {vendor.get('name', 'Unknown')}

VENDOR INFORMATION:
- Vendor ID: {vendor_id}
- Name: {vendor.get('name', 'Unknown')}
- Type: {vendor.get('vendor_type', 'Unknown')}
- Domain: {vendor.get('domain', 'Not provided')}
- Contract Value: ${vendor.get('contract_value', 0)}

AVAILABLE DOCUMENTS ({len(documents)} total):
{chr(10).join(doc_context) if doc_context else 'No documents available'}

{"SOC2 REPORT EXCERPT:" + chr(10) + soc2_texts[0] if soc2_texts else "NO SOC2 REPORT SUBMITTED"}

{"ISO 27001 CERTIFICATE EXCERPT:" + chr(10) + iso_texts[0] if iso_texts else "NO ISO 27001 CERTIFICATE SUBMITTED"}

{"SECURITY QUESTIONNAIRE EXCERPT:" + chr(10) + questionnaire_texts[0] if questionnaire_texts else "NO SECURITY QUESTIONNAIRE SUBMITTED"}

Please perform a full security assessment following your workflow:
1. Search internal security policies for requirements
2. Validate any SOC2 or ISO27001 documents
3. Check certificate expiry dates
4. Scan domain security (if domain provided)
5. Check breach history
6. Analyze security questionnaire (if provided)
7. Calculate the overall security score
8. Flag any critical issues
9. Generate the final security report

Vendor name for the report: {vendor.get('name', 'Unknown')}
"""

        result = agent.invoke({
            "messages": [HumanMessage(content=task)],
        })

        # Extract final response
        final_messages = result.get("messages", [])
        final_response = ""
        if final_messages:
            last_msg = final_messages[-1]
            final_response = (
                last_msg.content
                if hasattr(last_msg, "content")
                else str(last_msg)
            )

        logger.info(
            f"Security agent completed for vendor {vendor_id}"
        )

        return {
            "status": "success",
            "vendor_id": vendor_id,
            "agent_response": final_response,
        }

    except Exception as e:
        logger.error(
            f"Security agent failed for vendor {vendor_id}: {e}"
        )
        return {
            "status": "error",
            "vendor_id": vendor_id,
            "error": str(e),
        }
