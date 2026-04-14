"""
Financial Review Agent tools — 9 tools for financial risk assessment.
"""
import json
import logging
import re
import random
from datetime import datetime, timezone
from typing import Optional

from langchain_core.tools import tool

from app.core.vector import search_policies
from app.core.llm import get_llm
from app.config import get_settings

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# Tool 1: search_financial_policies
# ═══════════════════════════════════════════════════════════════════

@tool
def search_financial_policies(query: str) -> str:
    """
    Perform semantic search against internal financial policies using RAG.
    Returns relevant financial requirements based on the query.

    Args:
        query: Natural language query about financial requirements.
    """
    try:
        results = search_policies(
            collection="financial_policies",
            query=query,
            top_k=5,
            score_threshold=0.3,
        )
        return json.dumps({
            "status": "success",
            "result_count": len(results),
            "policies": [
                {
                    "title": r["title"],
                    "content_preview": r["content"][:500],
                    "relevance_score": round(r["score"], 4),
                    "policy_id": r.get("policy_id", ""),
                }
                for r in results
            ],
        })
    except Exception as e:
        logger.error(f"Financial policy search failed: {e}")
        return json.dumps({"status": "error", "error": str(e), "policies": []})


# ═══════════════════════════════════════════════════════════════════
# Tool 2: verify_insurance_coverage
# ═══════════════════════════════════════════════════════════════════

@tool
def verify_insurance_coverage(document_text: str, contract_value: float = 0.0) -> str:
    """
    Parse and verify insurance certificate for adequate coverage.
    Checks: coverage type, amount, policy period vs contract requirements.

    Args:
        document_text: Extracted text from the insurance certificate.
        contract_value: Contract value in USD to compare against coverage requirements.
    """
    try:
        llm = get_llm()

        # Determine minimum requirements based on contract value
        min_gl = max(1_000_000, contract_value * 2)
        min_pl = max(1_000_000, contract_value)
        min_cyber = max(2_000_000, contract_value * 3)

        prompt = f"""Analyze this insurance certificate and verify coverage adequacy.

Minimum requirements (based on ${contract_value:,.0f} contract value):
- General Liability: ${min_gl:,.0f}
- Professional Liability / E&O: ${min_pl:,.0f}
- Cyber / Technology E&O: ${min_cyber:,.0f}

Extract and verify:
1. General Liability coverage and limits
2. Professional Liability / E&O coverage  
3. Cyber Insurance / Technology E&O coverage
4. Workers Compensation
5. Policy effective and expiry dates
6. Insurance carrier name and AM Best rating

Return JSON ONLY:
{{
    "coverages": {{
        "general_liability": {{"present": true/false, "limit": number or null, "adequate": true/false}},
        "professional_liability": {{"present": true/false, "limit": number or null, "adequate": true/false}},
        "cyber_insurance": {{"present": true/false, "limit": number or null, "adequate": true/false}},
        "workers_comp": {{"present": true/false, "limit": number or null}}
    }},
    "carrier": "insurance company name",
    "policy_effective": "YYYY-MM-DD or null",
    "policy_expiry": "YYYY-MM-DD or null",
    "overall_adequate": true/false,
    "adequacy_score": 0-100,
    "gaps": ["list of coverage gaps"],
    "recommendations": ["list of recommendations"]
}}

Insurance certificate text (excerpt):
{document_text[:5000]}
"""
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)
        try:
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                return json.dumps({"status": "success", **parsed})
        except (json.JSONDecodeError, AttributeError):
            pass
        return json.dumps({"status": "success", "overall_adequate": False, "adequacy_score": 0})
    except Exception as e:
        logger.error(f"Insurance verification failed: {e}")
        return json.dumps({"status": "error", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════
# Tool 3: check_insurance_expiry
# ═══════════════════════════════════════════════════════════════════

@tool
def check_insurance_expiry(policy_expiry_date: str) -> str:
    """
    Check if an insurance policy is expired or expiring soon.

    Args:
        policy_expiry_date: Expiration date in YYYY-MM-DD format.
    """
    try:
        exp_date = datetime.strptime(policy_expiry_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        days_until = (exp_date - now).days

        if days_until < 0:
            status_val, severity = "expired", "critical"
        elif days_until <= 30:
            status_val, severity = "expiring_very_soon", "high"
        elif days_until <= 60:
            status_val, severity = "expiring_soon", "medium"
        else:
            status_val, severity = "valid", "info"

        return json.dumps({
            "status": "success",
            "policy_expiry_date": policy_expiry_date,
            "days_until_expiry": days_until,
            "expiry_status": status_val,
            "severity": severity,
        })
    except ValueError:
        return json.dumps({"status": "error", "error": f"Invalid date format: '{policy_expiry_date}'. Use YYYY-MM-DD."})
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════
# Tool 4: get_credit_rating (Mock + optional OpenCorporates)
# ═══════════════════════════════════════════════════════════════════

@tool
def get_credit_rating(company_name: str, company_location: str = "") -> str:
    """
    Get credit rating and financial risk score for a company.
    Uses mock data in development mode; OpenCorporates API when configured.

    Args:
        company_name: Name of the company to look up.
        company_location: Optional location for disambiguation.
    """
    try:
        settings = get_settings()

        if settings.credit_api_mode == "mock":
            # Generate deterministic mock data based on company name
            seed = sum(ord(c) for c in company_name)
            random.seed(seed)
            credit_score = random.randint(500, 850)
            risk_score = round(random.uniform(1.0, 10.0), 1)

            if credit_score >= 750:
                rating, risk_level = "AAA", "low"
            elif credit_score >= 650:
                rating, risk_level = "AA", "low"
            elif credit_score >= 550:
                rating, risk_level = "BBB", "medium"
            else:
                rating, risk_level = "BB", "high"

            return json.dumps({
                "status": "success",
                "source": "mock",
                "company_name": company_name,
                "credit_score": credit_score,
                "credit_rating": rating,
                "risk_score": risk_score,
                "risk_level": risk_level,
                "company_status": "active",
                "years_in_business": random.randint(2, 30),
                "note": "Mock data — configure OpenCorporates API for real data.",
            })

        # OpenCorporates fallback (if API key is set)
        if settings.opencorporates_api_key:
            try:
                import httpx
                resp = httpx.get(
                    f"https://api.opencorporates.com/v0.4/companies/search",
                    params={"q": company_name, "api_token": settings.opencorporates_api_key},
                    timeout=10,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    companies = data.get("results", {}).get("companies", [])
                    if companies:
                        comp = companies[0].get("company", {})
                        return json.dumps({
                            "status": "success",
                            "source": "opencorporates",
                            "company_name": comp.get("name", company_name),
                            "jurisdiction": comp.get("jurisdiction_code", ""),
                            "company_number": comp.get("company_number", ""),
                            "company_status": comp.get("current_status", "unknown"),
                            "incorporation_date": comp.get("incorporation_date", ""),
                            "credit_rating": "N/A",
                            "note": "OpenCorporates provides basic info; credit rating requires paid service.",
                        })
            except Exception as oc_err:
                logger.warning(f"OpenCorporates lookup failed: {oc_err}")

        return json.dumps({
            "status": "success",
            "source": "mock",
            "company_name": company_name,
            "credit_rating": "BBB",
            "risk_level": "medium",
            "note": "No credit API configured; returning default.",
        })

    except Exception as e:
        logger.error(f"Credit rating lookup failed: {e}")
        return json.dumps({"status": "error", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════
# Tool 5: analyze_financial_statements
# ═══════════════════════════════════════════════════════════════════

@tool
def analyze_financial_statements(document_text: str) -> str:
    """
    Parse financial statement documents and assess financial health.
    Extracts revenue, profit, cash flow, assets, liabilities.

    Args:
        document_text: Extracted text from financial statements.
    """
    try:
        llm = get_llm()
        prompt = f"""Analyze these financial statements and assess the vendor's financial health.

Extract and analyze:
1. Revenue (current and trend)
2. Net profit/loss
3. Cash flow from operations
4. Total assets
5. Total liabilities
6. Current ratio (current assets / current liabilities)
7. Debt-to-equity ratio
8. Gross profit margin
9. Year-over-year growth rate

Return JSON ONLY:
{{
    "financial_health": "strong" or "stable" or "concerning" or "weak",
    "stability_score": 0-100,
    "metrics": {{
        "revenue": number or null,
        "net_profit": number or null,
        "cash_flow": number or null,
        "total_assets": number or null,
        "total_liabilities": number or null,
        "current_ratio": number or null,
        "debt_to_equity": number or null,
        "profit_margin": number or null,
        "yoy_growth": number or null
    }},
    "red_flags": ["list of concerning indicators"],
    "strengths": ["list of positive indicators"],
    "recommendations": ["list"]
}}

Financial statement text (excerpt):
{document_text[:6000]}
"""
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)
        try:
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                return json.dumps({"status": "success", **parsed})
        except (json.JSONDecodeError, AttributeError):
            pass
        return json.dumps({"status": "success", "financial_health": "unknown", "stability_score": 50})
    except Exception as e:
        logger.error(f"Financial statement analysis failed: {e}")
        return json.dumps({"status": "error", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════
# Tool 6: check_bankruptcy_records
# ═══════════════════════════════════════════════════════════════════

@tool
def check_bankruptcy_records(company_name: str) -> str:
    """
    Search public bankruptcy databases for the company.
    Uses mock data — real PACER integration requires paid access.

    Args:
        company_name: Name of the company to search.
    """
    try:
        # Mock bankruptcy check — in production integrate with PACER or similar
        seed = sum(ord(c) for c in company_name.lower())
        has_bankruptcy = (seed % 20) == 0  # ~5% chance for demo

        return json.dumps({
            "status": "success",
            "source": "mock",
            "company_name": company_name,
            "bankruptcy_found": has_bankruptcy,
            "active_proceedings": False,
            "historical_filings": (
                [{"type": "Chapter 11", "date": "2019-03-15", "status": "discharged"}]
                if has_bankruptcy else []
            ),
            "risk_level": "critical" if has_bankruptcy else "low",
            "note": "Mock data — integrate with PACER for production.",
        })
    except Exception as e:
        logger.error(f"Bankruptcy check failed: {e}")
        return json.dumps({"status": "error", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════
# Tool 7: verify_business_continuity_plan
# ═══════════════════════════════════════════════════════════════════

@tool
def verify_business_continuity_plan(document_text: str) -> str:
    """
    Assess a Business Continuity Plan / Disaster Recovery document.
    Checks: RTO/RPO definitions, backup procedures, disaster scenarios, testing schedule.

    Args:
        document_text: Extracted text from BCP/DR document.
    """
    try:
        llm = get_llm()
        prompt = f"""Analyze this Business Continuity Plan / Disaster Recovery document.

Check:
1. RTO (Recovery Time Objective) defined
2. RPO (Recovery Point Objective) defined
3. Backup procedures documented
4. Disaster scenarios covered (natural, cyber, pandemic)
5. Communication plan during incidents
6. Roles and responsibilities assigned
7. Testing schedule (at least annual)
8. Last test date and results
9. Alternate site/failover provisions
10. Data recovery procedures

Return JSON ONLY:
{{
    "completeness_score": 0-100,
    "rto_defined": true/false,
    "rto_value": "e.g. 4 hours or null",
    "rpo_defined": true/false,
    "rpo_value": "e.g. 1 hour or null",
    "backup_procedures": true/false,
    "disaster_scenarios_covered": true/false,
    "testing_schedule": true/false,
    "last_test_date": "date or null",
    "issues": ["list of gaps"],
    "recommendations": ["list"]
}}

BCP/DR text (excerpt):
{document_text[:5000]}
"""
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)
        try:
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                return json.dumps({"status": "success", **parsed})
        except (json.JSONDecodeError, AttributeError):
            pass
        return json.dumps({"status": "success", "completeness_score": 50})
    except Exception as e:
        logger.error(f"BCP verification failed: {e}")
        return json.dumps({"status": "error", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════
# Tool 8: calculate_financial_risk_score
# ═══════════════════════════════════════════════════════════════════

@tool
def calculate_financial_risk_score(
    insurance_score: float,
    credit_rating_score: float,
    financial_stability_score: float,
    bcp_score: float,
) -> str:
    """
    Calculate an overall weighted financial risk score.
    Weights: Insurance 35%, Credit 30%, Stability 25%, BCP 10%.

    Args:
        insurance_score: Score from insurance verification (0-100).
        credit_rating_score: Score from credit rating (0-100).
        financial_stability_score: Score from financial analysis (0-100).
        bcp_score: Score from BCP verification (0-100).
    """
    try:
        weights = {"insurance": 0.35, "credit": 0.30, "stability": 0.25, "bcp": 0.10}
        overall = (
            insurance_score * weights["insurance"]
            + credit_rating_score * weights["credit"]
            + financial_stability_score * weights["stability"]
            + bcp_score * weights["bcp"]
        )
        overall = max(0, min(100, overall))
        grade = "A" if overall >= 90 else "B" if overall >= 80 else "C" if overall >= 70 else "D" if overall >= 60 else "F"

        return json.dumps({
            "status": "success",
            "overall_score": round(overall, 2),
            "grade": grade,
            "component_scores": {
                "insurance": {"score": insurance_score, "weight": weights["insurance"], "weighted": round(insurance_score * weights["insurance"], 2)},
                "credit_rating": {"score": credit_rating_score, "weight": weights["credit"], "weighted": round(credit_rating_score * weights["credit"], 2)},
                "financial_stability": {"score": financial_stability_score, "weight": weights["stability"], "weighted": round(financial_stability_score * weights["stability"], 2)},
                "bcp": {"score": bcp_score, "weight": weights["bcp"], "weighted": round(bcp_score * weights["bcp"], 2)},
            },
            "risk_level": "low" if overall >= 80 else "medium" if overall >= 60 else "high" if overall >= 40 else "critical",
        })
    except Exception as e:
        logger.error(f"Financial risk score calculation failed: {e}")
        return json.dumps({"status": "error", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════
# Tool 9: generate_financial_report
# ═══════════════════════════════════════════════════════════════════

@tool
def generate_financial_report(
    vendor_name: str,
    overall_score: float,
    grade: str,
    findings_json: str,
    recommendations_json: str,
) -> str:
    """
    Compile all financial findings into a comprehensive report.

    Args:
        vendor_name: Name of the vendor.
        overall_score: Overall financial risk score (0-100).
        grade: Letter grade (A-F).
        findings_json: JSON string of financial findings.
        recommendations_json: JSON string of recommendations.
    """
    try:
        try:
            findings = json.loads(findings_json) if isinstance(findings_json, str) else findings_json
        except json.JSONDecodeError:
            findings = [{"raw": findings_json}]
        try:
            recommendations = json.loads(recommendations_json) if isinstance(recommendations_json, str) else recommendations_json
        except json.JSONDecodeError:
            recommendations = [recommendations_json]

        llm = get_llm()
        prompt = f"""Generate a 3-5 sentence executive summary for a vendor financial assessment.
Vendor: {vendor_name}
Financial Score: {overall_score}/100 (Grade: {grade})
Key Findings: {json.dumps(findings)[:2000]}
Return only the summary text, no JSON."""

        response = llm.invoke(prompt)
        exec_summary = response.content if hasattr(response, "content") else str(response)

        report = {
            "status": "success",
            "report": {
                "title": f"Financial Assessment Report - {vendor_name}",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "executive_summary": exec_summary.strip(),
                "overall_score": overall_score,
                "grade": grade,
                "risk_level": "low" if overall_score >= 80 else "medium" if overall_score >= 60 else "high" if overall_score >= 40 else "critical",
                "findings": findings,
                "recommendations": recommendations,
                "conclusion": (
                    "APPROVED - Vendor meets financial requirements."
                    if overall_score >= 70
                    else "CONDITIONAL - Vendor requires financial remediation."
                    if overall_score >= 50
                    else "REJECTED - Vendor does not meet financial requirements."
                ),
            },
        }
        return json.dumps(report)
    except Exception as e:
        logger.error(f"Financial report generation failed: {e}")
        return json.dumps({"status": "error", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════
# Collect all financial tools
# ═══════════════════════════════════════════════════════════════════

FINANCIAL_TOOLS = [
    search_financial_policies,
    verify_insurance_coverage,
    check_insurance_expiry,
    get_credit_rating,
    analyze_financial_statements,
    check_bankruptcy_records,
    verify_business_continuity_plan,
    calculate_financial_risk_score,
    generate_financial_report,
]
