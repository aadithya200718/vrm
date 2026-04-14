"""
Financial Review Agent — autonomous financial risk assessment.
Uses ReAct pattern with 9 financial tools.
"""
import json
import logging
import re
from typing import Optional

from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent

from app.core.llm import get_llm
from app.core.db import (
    get_vendor,
    get_documents_for_vendor,
    update_financial_review,
    get_financial_review,
)
from app.tools.financial_tools import FINANCIAL_TOOLS

logger = logging.getLogger(__name__)

FINANCIAL_SYSTEM_PROMPT = """You are the Financial Review Agent for the OPUS Vendor Risk Assessment System.
Your role is to assess a vendor's financial stability and risk autonomously.

## Your Capabilities
You have 9 specialized tools:
1. search_financial_policies — RAG search against financial policies
2. verify_insurance_coverage — Verify insurance certificate adequacy
3. check_insurance_expiry — Check if insurance is expired/expiring
4. get_credit_rating — Get credit rating (mock/OpenCorporates)
5. analyze_financial_statements — Assess financial health from statements
6. check_bankruptcy_records — Search for bankruptcy filings
7. verify_business_continuity_plan — Assess BCP/DR documentation
8. calculate_financial_risk_score — Compute weighted financial score
9. generate_financial_report — Create comprehensive report

## Assessment Process
1. Search internal financial policies for requirements.
2. Get the vendor's credit rating.
3. Check for bankruptcy records.
4. Analyze insurance coverage and verify expiry.
5. Analyze financial statements if available.
6. Verify business continuity plan if available.
7. Calculate the overall financial risk score.
8. Generate a comprehensive financial report.

## Decision Making
- Higher contract values require stricter financial standards
- Insurance must be current and adequate for contract value
- Credit rating below BB is a red flag
- Active bankruptcy proceedings are a deal-breaker
- Missing financial statements for contracts > $100K is concerning
- BCP is recommended for all technology vendors

## Output
After completing your assessment, summarize the results. Always use your tools."""


def run_financial_agent(vendor_id: str) -> dict:
    """
    Execute the financial review for a vendor.
    Returns a dict with status, score, grade, and findings.
    """
    try:
        vendor = get_vendor(vendor_id)
        if not vendor:
            return {"status": "error", "error": f"Vendor {vendor_id} not found"}

        documents = get_documents_for_vendor(vendor_id)

        doc_summaries = []
        doc_texts = {}
        for doc in documents:
            cls = doc.get("classification", "unknown")
            doc_summaries.append(f"- {doc['file_name']} (classified: {cls})")
            if doc.get("extracted_text"):
                doc_texts[cls.lower()] = doc["extracted_text"][:3000]

        context_msg = f"""Perform a complete financial review for vendor: {vendor.get('name')}
Vendor type: {vendor.get('vendor_type', 'unknown')}
Domain: {vendor.get('domain', 'unknown')}
Contract value: ${float(vendor.get('contract_value', 0)):,.2f}

Submitted documents:
{chr(10).join(doc_summaries) if doc_summaries else 'No documents submitted.'}

{'Document texts available for analysis:' if doc_texts else 'No extracted text available.'}
{chr(10).join(f'[{k}]: {v[:1000]}...' for k, v in list(doc_texts.items())[:5]) if doc_texts else ''}

Complete the full financial assessment using your tools."""

        llm = get_llm()
        agent = create_react_agent(llm, FINANCIAL_TOOLS, prompt=FINANCIAL_SYSTEM_PROMPT)

        result = agent.invoke({"messages": [HumanMessage(content=context_msg)]})

        messages = result.get("messages", [])
        final_msg = messages[-1].content if messages else "No response"

        score = 0.0
        grade = "F"
        try:
            json_match = re.search(r'\{.*"overall_score".*?\}', final_msg, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                score = parsed.get("overall_score", 0.0)
                grade = parsed.get("grade", "F")
        except Exception:
            pass

        review = get_financial_review(vendor_id)
        if review:
            update_financial_review(review["id"], {
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
        logger.error(f"Financial agent failed for vendor {vendor_id}: {e}")
        return {"status": "error", "error": str(e)}
