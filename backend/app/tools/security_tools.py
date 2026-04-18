"""
Security Review Agent tools — 10 tools for comprehensive security assessment.
"""
import json
import logging
import re
import ssl
import socket
from datetime import datetime, timezone
from typing import Optional

import httpx
from langchain_core.tools import tool

from app.core.vector import search_policies
from app.core.db import search_breaches
from app.core.llm import get_llm

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# Tool 1: search_security_policies
# ═══════════════════════════════════════════════════════════════════

@tool
def search_security_policies(query: str) -> str:
    """
    Perform semantic search against internal security policies using RAG.
    Returns the top 5 most relevant security policies based on the query.

    Args:
        query: Natural language search query about security requirements.
    """
    try:
        results = search_policies(
            collection="security_policies",
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
        logger.error(f"Security policy search failed: {e}")
        return json.dumps({
            "status": "error",
            "error": str(e),
            "policies": [],
        })


# ═══════════════════════════════════════════════════════════════════
# Tool 2: validate_soc2_certificate
# ═══════════════════════════════════════════════════════════════════

@tool
def validate_soc2_certificate(document_text: str) -> str:
    """
    Validate a SOC2 report by extracting key details using LLM analysis.
    Checks: report type (Type 1/2), auditor, date range, opinion.

    Args:
        document_text: The extracted text content of the SOC2 report.
    """
    try:
        llm = get_llm()
        prompt = f"""Analyze this SOC 2 report and extract the following details.
Return JSON ONLY:
{{
    "report_type": "Type 1" or "Type 2",
    "auditor_name": "name of the audit firm",
    "audit_period_start": "YYYY-MM-DD or null",
    "audit_period_end": "YYYY-MM-DD or null",
    "opinion": "unqualified" or "qualified" or "adverse" or "disclaimer" or "unknown",
    "trust_service_criteria": ["Security", "Availability", "Processing Integrity", "Confidentiality", "Privacy"],
    "is_valid_format": true/false,
    "issues": ["list of concerns if any"],
    "auditor_is_reputable": true/false
}}

Known reputable SOC 2 auditors: Deloitte, PwC, EY, KPMG, BDO, Grant Thornton,
RSM, Crowe, Schellman, A-LIGN, Coalfire, Moss Adams.

SOC 2 Report text (excerpt):
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

        return json.dumps({
            "status": "success",
            "report_type": "unknown",
            "is_valid_format": False,
            "note": "Could not fully parse SOC2 report",
        })

    except Exception as e:
        logger.error(f"SOC2 validation failed: {e}")
        return json.dumps({"status": "error", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════
# Tool 3: validate_iso27001_certificate
# ═══════════════════════════════════════════════════════════════════

@tool
def validate_iso27001_certificate(document_text: str) -> str:
    """
    Validate an ISO 27001 certificate by extracting key details.
    Checks: certification body, scope, validity dates, accreditation.

    Args:
        document_text: The extracted text content of the ISO 27001 certificate.
    """
    try:
        llm = get_llm()
        prompt = f"""Analyze this ISO 27001 certificate and extract details.
Return JSON ONLY:
{{
    "certification_body": "name",
    "certificate_number": "number or null",
    "scope": "description of certification scope",
    "issue_date": "YYYY-MM-DD or null",
    "expiry_date": "YYYY-MM-DD or null",
    "standard_version": "ISO 27001:2013 or ISO 27001:2022",
    "is_valid_format": true/false,
    "accreditation_body": "name or null",
    "issues": ["list of concerns"],
    "certification_body_is_legitimate": true/false
}}

Known legitimate certification bodies: BSI, TÜV, Bureau Veritas, SGS,
DNV, LRQA, Intertek, Schellman, A-LIGN.

ISO 27001 certificate text:
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

        return json.dumps({
            "status": "success",
            "is_valid_format": False,
            "note": "Could not fully parse ISO 27001 certificate",
        })

    except Exception as e:
        logger.error(f"ISO 27001 validation failed: {e}")
        return json.dumps({"status": "error", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════
# Tool 4: check_certificate_expiry
# ═══════════════════════════════════════════════════════════════════

@tool
def check_certificate_expiry(
    certificate_type: str, expiry_date: str
) -> str:
    """
    Check if a certificate is expired or expiring soon (within 90 days).

    Args:
        certificate_type: Type of certificate (SOC2, ISO27001, Insurance, etc.)
        expiry_date: Expiration date in YYYY-MM-DD format.
    """
    try:
        exp_date = datetime.strptime(expiry_date, "%Y-%m-%d").replace(
            tzinfo=timezone.utc
        )
        now = datetime.now(timezone.utc)
        days_until = (exp_date - now).days

        if days_until < 0:
            status_val = "expired"
            severity = "critical"
        elif days_until <= 30:
            status_val = "expiring_very_soon"
            severity = "high"
        elif days_until <= 90:
            status_val = "expiring_soon"
            severity = "medium"
        else:
            status_val = "valid"
            severity = "info"

        return json.dumps({
            "status": "success",
            "certificate_type": certificate_type,
            "expiry_date": expiry_date,
            "days_until_expiry": days_until,
            "expiry_status": status_val,
            "severity": severity,
            "recommendation": (
                f"Certificate is {status_val}. "
                + (
                    "Immediate renewal required!"
                    if severity in ("critical", "high")
                    else (
                        "Plan renewal in the next 30 days."
                        if severity == "medium"
                        else "No action needed."
                    )
                )
            ),
        })

    except ValueError:
        return json.dumps({
            "status": "error",
            "error": f"Invalid date format: '{expiry_date}'. Use YYYY-MM-DD.",
        })
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════
# Tool 5: scan_domain_security
# ═══════════════════════════════════════════════════════════════════

@tool
def scan_domain_security(domain: str) -> str:
    """
    Scan a domain for security posture: SSL/TLS, security headers, basic checks.

    Args:
        domain: The domain to scan (e.g., 'example.com').
    """
    try:
        results = {
            "domain": domain,
            "ssl": {},
            "headers": {},
            "score": 0,
        }

        # ── SSL/TLS Check ──────────────────────────────────────
        try:
            ctx = ssl.create_default_context()
            with ctx.wrap_socket(
                socket.socket(), server_hostname=domain
            ) as s:
                s.settimeout(10)
                s.connect((domain, 443))
                cert = s.getpeercert()
                cipher = s.cipher()

                results["ssl"] = {
                    "valid": True,
                    "issuer": dict(x[0] for x in cert.get("issuer", [])),
                    "subject": dict(x[0] for x in cert.get("subject", [])),
                    "not_before": cert.get("notBefore", ""),
                    "not_after": cert.get("notAfter", ""),
                    "protocol": cipher[1] if cipher else "unknown",
                    "cipher_suite": cipher[0] if cipher else "unknown",
                }
                results["score"] += 30
        except Exception as ssl_err:
            results["ssl"] = {"valid": False, "error": str(ssl_err)}

        # ── Security Headers Check ─────────────────────────────
        try:
            resp = httpx.get(
                f"https://{domain}",
                follow_redirects=True,
                timeout=10,
            )
            headers = dict(resp.headers)

            security_headers = {
                "strict-transport-security": False,
                "content-security-policy": False,
                "x-frame-options": False,
                "x-content-type-options": False,
                "x-xss-protection": False,
                "referrer-policy": False,
                "permissions-policy": False,
            }

            for header in security_headers:
                if header in headers:
                    security_headers[header] = True
                    results["score"] += 10

            results["headers"] = {
                "present": {k: v for k, v in security_headers.items() if v},
                "missing": {k: v for k, v in security_headers.items() if not v},
                "headers_found": sum(security_headers.values()),
                "headers_total": len(security_headers),
            }
        except Exception as hdr_err:
            results["headers"] = {"error": str(hdr_err)}

        # Calculate final score (max 100)
        results["score"] = min(results["score"], 100)
        results["grade"] = (
            "A" if results["score"] >= 80
            else "B" if results["score"] >= 60
            else "C" if results["score"] >= 40
            else "D" if results["score"] >= 20
            else "F"
        )
        results["status"] = "success"

        return json.dumps(results)

    except Exception as e:
        logger.error(f"Domain security scan failed for {domain}: {e}")
        return json.dumps({"status": "error", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════
# Tool 6: check_breach_history
# ═══════════════════════════════════════════════════════════════════

@tool
def check_breach_history(company_name: str, domain: Optional[str] = None) -> str:
    """
    Check breach history for a company using internal database and public sources.

    Args:
        company_name: Name of the company to search for.
        domain: Optional domain name to search for.
    """
    try:
        # Search internal breach database
        breaches = search_breaches(company_name, domain)

        # Try HaveIBeenPwned API as fallback
        hibp_results = []
        if domain:
            try:
                resp = httpx.get(
                    f"https://haveibeenpwned.com/api/v3/breaches?domain={domain}",
                    headers={"User-Agent": "VRM-Security-Scanner"},
                    timeout=10,
                )
                if resp.status_code == 200:
                    hibp_results = resp.json()
            except Exception:
                pass  # HIBP may require API key or rate limit

        total_breaches = len(breaches) + len(hibp_results)

        return json.dumps({
            "status": "success",
            "company_name": company_name,
            "domain": domain,
            "total_breaches_found": total_breaches,
            "internal_db_results": [
                {
                    "company": b.get("company_name"),
                    "breach_date": b.get("breach_date"),
                    "records_exposed": b.get("records_exposed"),
                    "severity": b.get("severity"),
                    "description": b.get("description", ""),
                }
                for b in breaches
            ],
            "hibp_results": [
                {
                    "name": h.get("Name"),
                    "breach_date": h.get("BreachDate"),
                    "pwn_count": h.get("PwnCount"),
                    "data_classes": h.get("DataClasses", []),
                }
                for h in hibp_results[:10]
            ],
            "risk_level": (
                "critical" if total_breaches >= 3
                else "high" if total_breaches >= 2
                else "medium" if total_breaches >= 1
                else "low"
            ),
        })

    except Exception as e:
        logger.error(f"Breach history check failed: {e}")
        return json.dumps({"status": "error", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════
# Tool 7: analyze_security_questionnaire
# ═══════════════════════════════════════════════════════════════════

@tool
def analyze_security_questionnaire(questionnaire_text: str) -> str:
    """
    Analyze security questionnaire responses using LLM to score them
    against best practices and identify red flags.

    Args:
        questionnaire_text: The text content of the security questionnaire responses.
    """
    try:
        llm = get_llm()
        prompt = f"""You are a security assessment expert. Analyze these security questionnaire
responses and evaluate them against industry best practices.

Score each area on a scale of 0-10 and identify any red flags.

Return JSON ONLY:
{{
    "overall_score": 0-100,
    "areas": {{
        "access_control": {{"score": 0-10, "notes": ""}},
        "data_encryption": {{"score": 0-10, "notes": ""}},
        "incident_response": {{"score": 0-10, "notes": ""}},
        "network_security": {{"score": 0-10, "notes": ""}},
        "employee_training": {{"score": 0-10, "notes": ""}},
        "vulnerability_management": {{"score": 0-10, "notes": ""}},
        "backup_recovery": {{"score": 0-10, "notes": ""}},
        "third_party_management": {{"score": 0-10, "notes": ""}}
    }},
    "red_flags": ["list of concerning findings"],
    "strengths": ["list of positive findings"],
    "recommendations": ["list of improvement suggestions"]
}}

Questionnaire responses:
{questionnaire_text[:6000]}
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

        return json.dumps({
            "status": "success",
            "overall_score": 50,
            "note": "Could not fully analyze questionnaire",
        })

    except Exception as e:
        logger.error(f"Security questionnaire analysis failed: {e}")
        return json.dumps({"status": "error", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════
# Tool 8: calculate_security_score
# ═══════════════════════════════════════════════════════════════════

@tool
def calculate_security_score(
    certificate_score: float,
    domain_security_score: float,
    breach_history_score: float,
    questionnaire_score: float,
) -> str:
    """
    Calculate an overall weighted security score from component scores.
    Weights: certificates 40%, domain security 30%, breach history 20%, questionnaire 10%.

    Args:
        certificate_score: Score from certificate validation (0-100).
        domain_security_score: Score from domain security scan (0-100).
        breach_history_score: Score from breach history check (0-100).
        questionnaire_score: Score from security questionnaire (0-100).
    """
    try:
        weights = {
            "certificates": 0.40,
            "domain_security": 0.30,
            "breach_history": 0.20,
            "questionnaire": 0.10,
        }

        overall = (
            certificate_score * weights["certificates"]
            + domain_security_score * weights["domain_security"]
            + breach_history_score * weights["breach_history"]
            + questionnaire_score * weights["questionnaire"]
        )

        overall = max(0, min(100, overall))

        if overall >= 90:
            grade = "A"
        elif overall >= 80:
            grade = "B"
        elif overall >= 70:
            grade = "C"
        elif overall >= 60:
            grade = "D"
        else:
            grade = "F"

        return json.dumps({
            "status": "success",
            "overall_score": round(overall, 2),
            "grade": grade,
            "component_scores": {
                "certificates": {
                    "score": certificate_score,
                    "weight": weights["certificates"],
                    "weighted": round(certificate_score * weights["certificates"], 2),
                },
                "domain_security": {
                    "score": domain_security_score,
                    "weight": weights["domain_security"],
                    "weighted": round(
                        domain_security_score * weights["domain_security"], 2
                    ),
                },
                "breach_history": {
                    "score": breach_history_score,
                    "weight": weights["breach_history"],
                    "weighted": round(
                        breach_history_score * weights["breach_history"], 2
                    ),
                },
                "questionnaire": {
                    "score": questionnaire_score,
                    "weight": weights["questionnaire"],
                    "weighted": round(
                        questionnaire_score * weights["questionnaire"], 2
                    ),
                },
            },
            "risk_level": (
                "low" if overall >= 80
                else "medium" if overall >= 60
                else "high" if overall >= 40
                else "critical"
            ),
        })

    except Exception as e:
        logger.error(f"Security score calculation failed: {e}")
        return json.dumps({"status": "error", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════
# Tool 9: generate_security_report
# ═══════════════════════════════════════════════════════════════════

@tool
def generate_security_report(
    vendor_name: str,
    overall_score: float,
    grade: str,
    findings_json: str,
    recommendations_json: str,
) -> str:
    """
    Compile all security findings into a comprehensive report.

    Args:
        vendor_name: Name of the vendor being assessed.
        overall_score: Calculated overall security score (0-100).
        grade: Letter grade (A-F).
        findings_json: JSON string of all security findings from the review.
        recommendations_json: JSON string of all recommendations.
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

        # Use LLM to generate executive summary
        llm = get_llm()
        prompt = f"""Generate a brief executive summary (3-5 sentences) for a vendor security assessment.

Vendor: {vendor_name}
Security Score: {overall_score}/100 (Grade: {grade})
Key Findings: {json.dumps(findings)[:2000]}

Write a professional, concise executive summary. Return only the summary text, no JSON.
"""
        response = llm.invoke(prompt)
        executive_summary = (
            response.content if hasattr(response, "content") else str(response)
        )

        report = {
            "status": "success",
            "report": {
                "title": f"Security Assessment Report - {vendor_name}",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "executive_summary": executive_summary.strip(),
                "overall_score": overall_score,
                "grade": grade,
                "risk_level": (
                    "low" if overall_score >= 80
                    else "medium" if overall_score >= 60
                    else "high" if overall_score >= 40
                    else "critical"
                ),
                "findings": findings,
                "recommendations": recommendations,
                "conclusion": (
                    "APPROVED - Vendor meets security requirements."
                    if overall_score >= 70
                    else "CONDITIONAL - Vendor requires remediation before approval."
                    if overall_score >= 50
                    else "REJECTED - Vendor does not meet minimum security requirements."
                ),
            },
        }
        return json.dumps(report)

    except Exception as e:
        logger.error(f"Security report generation failed: {e}")
        return json.dumps({"status": "error", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════
# Tool 10: flag_critical_issues
# ═══════════════════════════════════════════════════════════════════

@tool
def flag_critical_issues(findings_json: str) -> str:
    """
    Identify and flag critical security issues that would block vendor approval.

    Args:
        findings_json: JSON string of all security findings to analyze.
    """
    try:
        try:
            findings = json.loads(findings_json) if isinstance(findings_json, str) else findings_json
        except json.JSONDecodeError:
            findings = [{"raw": findings_json}]

        llm = get_llm()
        prompt = f"""Analyze these security findings and identify any CRITICAL issues
that should BLOCK vendor approval.

Critical issues include:
- Expired or missing security certifications
- Active data breaches
- No encryption in transit or at rest
- No incident response plan
- Failed SSL/TLS
- Critical vulnerabilities
- No SOC2 or equivalent certification

Return JSON ONLY:
{{
    "has_critical_issues": true/false,
    "critical_issues": [
        {{
            "title": "Issue title",
            "severity": "critical",
            "impact": "Description of business impact",
            "remediation": "Required fix",
            "is_blocker": true/false
        }}
    ],
    "high_issues": [...same format...],
    "total_blockers": number,
    "recommendation": "approve" or "conditional" or "reject"
}}

Findings:
{json.dumps(findings)[:5000]}
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

        return json.dumps({
            "status": "success",
            "has_critical_issues": False,
            "critical_issues": [],
            "note": "Could not fully analyze findings",
        })

    except Exception as e:
        logger.error(f"Critical issues flagging failed: {e}")
        return json.dumps({"status": "error", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════
# Collect all security tools
# ═══════════════════════════════════════════════════════════════════

SECURITY_TOOLS = [
    search_security_policies,
    validate_soc2_certificate,
    validate_iso27001_certificate,
    check_certificate_expiry,
    scan_domain_security,
    check_breach_history,
    analyze_security_questionnaire,
    calculate_security_score,
    generate_security_report,
    flag_critical_issues,
]
