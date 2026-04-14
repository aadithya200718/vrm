"""
Compliance Review Agent — autonomous regulatory compliance assessment.
Uses ReAct pattern with 10 compliance tools.
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
    update_compliance_review,
    get_compliance_review,
)
from app.tools.compliance_tools import COMPLIANCE_TOOLS

logger = logging.getLogger(__name__)

COMPLIANCE_SYSTEM_PROMPT = """You are the Compliance Review Agent for the OPUS Vendor Risk Assessment System.
Your role is to assess a vendor's regulatory compliance posture autonomously.

## Your Capabilities
You have 10 specialized tools:
1. search_compliance_policies — RAG search against internal compliance policies
2. check_gdpr_compliance — Verify GDPR requirements
3. check_hipaa_compliance — Verify HIPAA requirements
4. check_pci_compliance — Verify PCI-DSS requirements
5. verify_data_processing_agreement — Parse and validate DPA
6. assess_data_retention_policy — Evaluate data retention practices
7. check_subprocessor_list — Analyze sub-processor disclosures
8. validate_privacy_policy — Check privacy policy completeness
9. calculate_compliance_score — Compute weighted compliance score
10. generate_compliance_report — Create comprehensive report

## Assessment Process
1. First, search internal compliance policies to understand organizational requirements.
2. Determine which regulations apply based on vendor type and data handling.
3. Check applicable regulations (GDPR always, HIPAA/PCI if relevant).
4. Verify DPA, retention policy, sub-processors, and privacy policy.
5. Calculate the overall compliance score.
6. Generate a comprehensive compliance report.

## Decision Making
- GDPR applies to ALL vendors handling EU personal data
- HIPAA applies only if vendor handles PHI (healthcare data)
- PCI-DSS applies only if vendor handles cardholder data
- Always check DPA and privacy policy regardless
- Adapt assessment depth based on data sensitivity

## Output
After completing your assessment, provide the results in a clear summary. Always use your tools — do not guess."""


def run_compliance_agent(vendor_id: str) -> dict:
    """
    Execute the compliance review for a vendor.
    Returns a dict with status, score, grade, and findings.
    """
    try:
        vendor = get_vendor(vendor_id)
        if not vendor:
            return {"status": "error", "error": f"Vendor {vendor_id} not found"}

        documents = get_documents_for_vendor(vendor_id)

        # Build context message
        doc_summaries = []
        doc_texts = {}
        for doc in documents:
            cls = doc.get("classification", "unknown")
            doc_summaries.append(f"- {doc['file_name']} (classified: {cls})")
            if doc.get("extracted_text"):
                doc_texts[cls.lower()] = doc["extracted_text"][:3000]

        context_msg = f"""Perform a complete compliance review for vendor: {vendor.get('name')}
Vendor type: {vendor.get('vendor_type', 'unknown')}
Domain: {vendor.get('domain', 'unknown')}
Industry: {vendor.get('industry', 'unknown')}
Contract value: ${float(vendor.get('contract_value', 0)):,.2f}

Submitted documents:
{chr(10).join(doc_summaries) if doc_summaries else 'No documents submitted.'}

{'Document texts available for analysis:' if doc_texts else 'No extracted text available.'}
{chr(10).join(f'[{k}]: {v[:1000]}...' for k, v in list(doc_texts.items())[:5]) if doc_texts else ''}

Complete the full compliance assessment using your tools."""

        llm = get_llm()
        agent = create_react_agent(llm, COMPLIANCE_TOOLS, prompt=COMPLIANCE_SYSTEM_PROMPT)

        result = agent.invoke({"messages": [HumanMessage(content=context_msg)]})

        # Extract final message
        messages = result.get("messages", [])
        final_msg = messages[-1].content if messages else "No response"

        # Try to extract structured results
        score = 0.0
        grade = "F"
        try:
            import re
            json_match = re.search(r'\{.*"overall_score".*?\}', final_msg, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                score = parsed.get("overall_score", 0.0)
                grade = parsed.get("grade", "F")
        except Exception:
            pass

        # Update the compliance review record
        review = get_compliance_review(vendor_id)
        if review:
            update_compliance_review(review["id"], {
                "overall_score": score,
                "grade": grade,
                "status": "completed",
                "report": {"agent_output": final_msg[:5000]},
                "completed_at": None,
            })

        return {
            "status": "success",
            "score": score,
            "grade": grade,
            "agent_output": final_msg[:3000],
        }

    except Exception as e:
        logger.error(f"Compliance agent failed for vendor {vendor_id}: {e}")
        return {"status": "error", "error": str(e)}
