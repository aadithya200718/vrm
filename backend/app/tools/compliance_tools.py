"""
Compliance Review Agent tools — 10 tools for regulatory compliance assessment.
"""
import json
import logging
import re
from datetime import datetime, timezone
from typing import Optional

import httpx
from langchain_core.tools import tool

from app.core.vector import search_policies
from app.core.llm import get_llm

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# Tool 1: search_compliance_policies
# ═══════════════════════════════════════════════════════════════════

@tool
def search_compliance_policies(query: str) -> str:
    """
    Perform semantic search against internal compliance policies using RAG.
    Returns the top 5 most relevant compliance policies.

    Args:
        query: Natural language search query about compliance requirements.
    """
    try:
        results = search_policies(
            collection="compliance_policies",
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
        logger.error(f"Compliance policy search failed: {e}")
        return json.dumps({"status": "error", "error": str(e), "policies": []})


# ═══════════════════════════════════════════════════════════════════
# Tool 2: check_gdpr_compliance
# ═══════════════════════════════════════════════════════════════════

@tool
def check_gdpr_compliance(document_text: str, vendor_domain: str = "") -> str:
    """
    Verify GDPR requirements against vendor documents using LLM analysis.
    Checks: EU data center, DPO appointment, data subject rights, breach notification.

    Args:
        document_text: Extracted text from DPA, privacy policy, or questionnaire.
        vendor_domain: Vendor's domain for additional context.
    """
    try:
        llm = get_llm()
        prompt = f"""You are a GDPR compliance expert. Analyze the following vendor documentation
and assess compliance with GDPR requirements.

Check each requirement and score it:
1. Lawful basis for processing (consent, contract, legitimate interest)
2. Data Processing Agreement (Article 28) present and complete
3. Data Protection Officer (DPO) appointed
4. Data subject rights procedures (access, rectification, erasure, portability)
5. Breach notification procedures (72-hour notification)
6. Data transfer safeguards (SCCs, adequacy decisions)
7. Data minimization and purpose limitation
8. Record of processing activities (Article 30)
9. Privacy by design and default
10. Sub-processor management

Return JSON ONLY:
{{
    "overall_compliance": "compliant" or "partial" or "non_compliant",
    "score": 0-100,
    "checks": {{
        "lawful_basis": {{"status": "pass/partial/fail", "notes": ""}},
        "dpa_completeness": {{"status": "pass/partial/fail", "notes": ""}},
        "dpo_appointed": {{"status": "pass/partial/fail", "notes": ""}},
        "data_subject_rights": {{"status": "pass/partial/fail", "notes": ""}},
        "breach_notification": {{"status": "pass/partial/fail", "notes": ""}},
        "data_transfer": {{"status": "pass/partial/fail", "notes": ""}},
        "data_minimization": {{"status": "pass/partial/fail", "notes": ""}},
        "processing_records": {{"status": "pass/partial/fail", "notes": ""}},
        "privacy_by_design": {{"status": "pass/partial/fail", "notes": ""}},
        "sub_processor_mgmt": {{"status": "pass/partial/fail", "notes": ""}}
    }},
    "gaps": ["list of missing GDPR requirements"],
    "recommendations": ["list of remediation steps"]
}}

Vendor domain: {vendor_domain}
Document text (excerpt):
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
        return json.dumps({"status": "success", "overall_compliance": "unknown", "score": 50})
    except Exception as e:
        logger.error(f"GDPR compliance check failed: {e}")
        return json.dumps({"status": "error", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════
# Tool 3: check_hipaa_compliance
# ═══════════════════════════════════════════════════════════════════

@tool
def check_hipaa_compliance(document_text: str) -> str:
    """
    Verify HIPAA requirements against vendor documents using LLM analysis.
    Checks: BAA existence, PHI handling, security safeguards, breach procedures.

    Args:
        document_text: Extracted text from BAA, security docs, or questionnaire.
    """
    try:
        llm = get_llm()
        prompt = f"""You are a HIPAA compliance expert. Analyze vendor documentation for HIPAA compliance.

Check each requirement:
1. Business Associate Agreement (BAA) present
2. PHI handling procedures documented
3. Administrative safeguards (security officer, training, access management)
4. Physical safeguards (facility access, workstation security)
5. Technical safeguards (access controls, audit controls, transmission security, encryption)
6. Breach notification procedures
7. Risk assessment performed
8. Contingency planning (backup, disaster recovery)

Return JSON ONLY:
{{
    "overall_compliance": "compliant" or "partial" or "non_compliant" or "not_applicable",
    "score": 0-100,
    "baa_present": true/false,
    "checks": {{
        "baa": {{"status": "pass/partial/fail", "notes": ""}},
        "phi_handling": {{"status": "pass/partial/fail", "notes": ""}},
        "admin_safeguards": {{"status": "pass/partial/fail", "notes": ""}},
        "physical_safeguards": {{"status": "pass/partial/fail", "notes": ""}},
        "technical_safeguards": {{"status": "pass/partial/fail", "notes": ""}},
        "breach_notification": {{"status": "pass/partial/fail", "notes": ""}},
        "risk_assessment": {{"status": "pass/partial/fail", "notes": ""}},
        "contingency_plan": {{"status": "pass/partial/fail", "notes": ""}}
    }},
    "gaps": ["list of missing requirements"],
    "recommendations": ["list of remediation steps"]
}}

Document text (excerpt):
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
        return json.dumps({"status": "success", "overall_compliance": "unknown", "score": 50})
    except Exception as e:
        logger.error(f"HIPAA compliance check failed: {e}")
        return json.dumps({"status": "error", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════
# Tool 4: check_pci_compliance
# ═══════════════════════════════════════════════════════════════════

@tool
def check_pci_compliance(document_text: str) -> str:
    """
    Verify PCI-DSS requirements against vendor documents using LLM analysis.
    Checks: cardholder data handling, network security, access controls.

    Args:
        document_text: Extracted text from security docs, questionnaire, or PCI AOC.
    """
    try:
        llm = get_llm()
        prompt = f"""You are a PCI-DSS compliance expert. Analyze vendor documentation for PCI-DSS compliance.

Check the 12 PCI-DSS requirements:
1. Install/maintain firewall
2. No vendor-supplied default passwords
3. Protect stored cardholder data
4. Encrypt transmission over public networks
5. Use/update anti-virus
6. Develop/maintain secure systems
7. Restrict access on need-to-know
8. Assign unique IDs
9. Restrict physical access to data
10. Track/monitor network access
11. Regular security testing
12. Maintain info security policy

Return JSON ONLY:
{{
    "overall_compliance": "compliant" or "partial" or "non_compliant" or "not_applicable",
    "score": 0-100,
    "pci_level": "Level 1/2/3/4 or unknown",
    "handles_cardholder_data": true/false,
    "aoc_present": true/false,
    "gaps": ["list of missing requirements"],
    "recommendations": ["list of remediation steps"]
}}

Document text (excerpt):
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
        return json.dumps({"status": "success", "overall_compliance": "unknown", "score": 50})
    except Exception as e:
        logger.error(f"PCI compliance check failed: {e}")
        return json.dumps({"status": "error", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════
# Tool 5: verify_data_processing_agreement
# ═══════════════════════════════════════════════════════════════════

@tool
def verify_data_processing_agreement(document_text: str) -> str:
    """
    Parse and verify a Data Processing Agreement for completeness.
    Checks for Article 28 GDPR clauses, purpose limitation, subprocessor disclosure.

    Args:
        document_text: Extracted text from the DPA document.
    """
    try:
        llm = get_llm()
        prompt = f"""Analyze this Data Processing Agreement (DPA) for completeness.

Required clauses (GDPR Article 28):
1. Subject matter, duration, nature, purpose of processing
2. Type of personal data and categories of data subjects
3. Obligations of the controller
4. Processing only on documented instructions
5. Confidentiality obligations
6. Technical and organizational security measures
7. Sub-processor engagement rules and notification
8. Assistance with data subject requests
9. Assistance with DPIA and prior consultation
10. Deletion or return of data after service ends
11. Audit rights for the controller
12. International data transfer provisions

Return JSON ONLY:
{{
    "is_valid_dpa": true/false,
    "completeness_score": 0-100,
    "clauses_present": ["list of present clauses"],
    "clauses_missing": ["list of missing clauses"],
    "subprocessors_disclosed": true/false,
    "international_transfers_addressed": true/false,
    "audit_rights_granted": true/false,
    "data_deletion_clause": true/false,
    "issues": ["list of specific issues"],
    "recommendations": ["list of remediation steps"]
}}

DPA text (excerpt):
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
        return json.dumps({"status": "success", "is_valid_dpa": False, "completeness_score": 0})
    except Exception as e:
        logger.error(f"DPA verification failed: {e}")
        return json.dumps({"status": "error", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════
# Tool 6: assess_data_retention_policy
# ═══════════════════════════════════════════════════════════════════

@tool
def assess_data_retention_policy(document_text: str) -> str:
    """
    Assess a data retention policy for adequacy.
    Checks: retention periods, deletion procedures, data minimization.

    Args:
        document_text: Extracted text from the data retention policy.
    """
    try:
        llm = get_llm()
        prompt = f"""Assess this data retention policy for adequacy.

Check:
1. Clear retention periods defined for each data category
2. Deletion/destruction procedures documented
3. Data minimization principles applied
4. Legal hold exceptions documented
5. Regular review schedule defined
6. Disposal methods specified (secure delete, shredding)
7. Compliance with applicable regulations

Return JSON ONLY:
{{
    "adequacy_score": 0-100,
    "retention_periods_defined": true/false,
    "deletion_procedures": true/false,
    "data_minimization": true/false,
    "legal_hold_provisions": true/false,
    "review_schedule": true/false,
    "issues": ["list of issues"],
    "recommendations": ["list of improvements"]
}}

Retention policy text (excerpt):
{document_text[:4000]}
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
        return json.dumps({"status": "success", "adequacy_score": 50})
    except Exception as e:
        logger.error(f"Data retention assessment failed: {e}")
        return json.dumps({"status": "error", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════
# Tool 7: check_subprocessor_list
# ═══════════════════════════════════════════════════════════════════

@tool
def check_subprocessor_list(document_text: str) -> str:
    """
    Extract and analyze subprocessor list from vendor documents.
    Verifies disclosure completeness and flags high-risk jurisdictions.

    Args:
        document_text: Extracted text containing subprocessor information.
    """
    try:
        llm = get_llm()
        prompt = f"""Extract and analyze the subprocessor list from this vendor documentation.

For each subprocessor identify:
- Name
- Location/jurisdiction
- Purpose/service provided
- Data access level

Flag jurisdictions that are high-risk for data protection:
High-risk: China, Russia, countries without adequacy decisions

Return JSON ONLY:
{{
    "subprocessors_found": number,
    "subprocessors": [
        {{
            "name": "",
            "location": "",
            "purpose": "",
            "risk_level": "low/medium/high"
        }}
    ],
    "high_risk_jurisdictions": ["list"],
    "disclosure_complete": true/false,
    "issues": ["list of concerns"],
    "recommendations": ["list of steps"]
}}

Document text (excerpt):
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
        return json.dumps({"status": "success", "subprocessors_found": 0, "disclosure_complete": False})
    except Exception as e:
        logger.error(f"Subprocessor analysis failed: {e}")
        return json.dumps({"status": "error", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════
# Tool 8: validate_privacy_policy
# ═══════════════════════════════════════════════════════════════════

@tool
def validate_privacy_policy(document_text: str, vendor_domain: str = "") -> str:
    """
    Validate a privacy policy for completeness and regulatory compliance.
    Checks: data collection disclosure, purpose specification, user rights.

    Args:
        document_text: Extracted text from the privacy policy.
        vendor_domain: Vendor domain to optionally fetch the live privacy policy.
    """
    try:
        # Optionally fetch live privacy policy
        policy_text = document_text
        if vendor_domain and not document_text.strip():
            try:
                resp = httpx.get(f"https://{vendor_domain}/privacy", follow_redirects=True, timeout=10)
                if resp.status_code == 200:
                    policy_text = resp.text[:8000]
            except Exception:
                pass

        llm = get_llm()
        prompt = f"""Analyze this privacy policy for completeness and regulatory compliance.

Check:
1. Data collection types disclosed
2. Purpose of collection specified
3. Legal basis stated
4. User rights described (access, deletion, portability)
5. Cookie policy present
6. Third-party sharing disclosed
7. Data retention periods stated
8. Contact information for DPO/privacy team
9. International transfer disclosure
10. Children's data handling (if applicable)

Return JSON ONLY:
{{
    "completeness_score": 0-100,
    "checks": {{
        "data_collection": {{"present": true/false, "notes": ""}},
        "purpose_specification": {{"present": true/false, "notes": ""}},
        "legal_basis": {{"present": true/false, "notes": ""}},
        "user_rights": {{"present": true/false, "notes": ""}},
        "cookie_policy": {{"present": true/false, "notes": ""}},
        "third_party_sharing": {{"present": true/false, "notes": ""}},
        "retention_periods": {{"present": true/false, "notes": ""}},
        "contact_info": {{"present": true/false, "notes": ""}},
        "international_transfers": {{"present": true/false, "notes": ""}},
        "childrens_data": {{"present": true/false, "notes": ""}}
    }},
    "issues": ["list"],
    "recommendations": ["list"]
}}

Privacy policy text (excerpt):
{policy_text[:5000]}
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
        logger.error(f"Privacy policy validation failed: {e}")
        return json.dumps({"status": "error", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════
# Tool 9: calculate_compliance_score
# ═══════════════════════════════════════════════════════════════════

@tool
def calculate_compliance_score(
    gdpr_score: float,
    hipaa_score: float,
    pci_score: float,
    dpa_score: float,
    privacy_policy_score: float,
) -> str:
    """
    Calculate an overall weighted compliance score.
    Weights: GDPR 30%, HIPAA 20%, PCI 15%, DPA 20%, Privacy 15%.

    Args:
        gdpr_score: GDPR compliance score (0-100).
        hipaa_score: HIPAA compliance score (0-100), use 0 if not applicable.
        pci_score: PCI-DSS compliance score (0-100), use 0 if not applicable.
        dpa_score: DPA completeness score (0-100).
        privacy_policy_score: Privacy policy completeness score (0-100).
    """
    try:
        weights = {
            "gdpr": 0.30,
            "hipaa": 0.20,
            "pci": 0.15,
            "dpa": 0.20,
            "privacy_policy": 0.15,
        }
        overall = (
            gdpr_score * weights["gdpr"]
            + hipaa_score * weights["hipaa"]
            + pci_score * weights["pci"]
            + dpa_score * weights["dpa"]
            + privacy_policy_score * weights["privacy_policy"]
        )
        overall = max(0, min(100, overall))

        grade = (
            "A" if overall >= 90 else
            "B" if overall >= 80 else
            "C" if overall >= 70 else
            "D" if overall >= 60 else "F"
        )

        return json.dumps({
            "status": "success",
            "overall_score": round(overall, 2),
            "grade": grade,
            "component_scores": {
                "gdpr": {"score": gdpr_score, "weight": weights["gdpr"], "weighted": round(gdpr_score * weights["gdpr"], 2)},
                "hipaa": {"score": hipaa_score, "weight": weights["hipaa"], "weighted": round(hipaa_score * weights["hipaa"], 2)},
                "pci": {"score": pci_score, "weight": weights["pci"], "weighted": round(pci_score * weights["pci"], 2)},
                "dpa": {"score": dpa_score, "weight": weights["dpa"], "weighted": round(dpa_score * weights["dpa"], 2)},
                "privacy_policy": {"score": privacy_policy_score, "weight": weights["privacy_policy"], "weighted": round(privacy_policy_score * weights["privacy_policy"], 2)},
            },
            "risk_level": "low" if overall >= 80 else "medium" if overall >= 60 else "high" if overall >= 40 else "critical",
        })
    except Exception as e:
        logger.error(f"Compliance score calculation failed: {e}")
        return json.dumps({"status": "error", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════
# Tool 10: generate_compliance_report
# ═══════════════════════════════════════════════════════════════════

@tool
def generate_compliance_report(
    vendor_name: str,
    overall_score: float,
    grade: str,
    findings_json: str,
    recommendations_json: str,
) -> str:
    """
    Compile all compliance findings into a comprehensive report.

    Args:
        vendor_name: Name of the vendor being assessed.
        overall_score: Overall compliance score (0-100).
        grade: Letter grade (A-F).
        findings_json: JSON string of compliance findings.
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
        prompt = f"""Generate a 3-5 sentence executive summary for a vendor compliance assessment.
Vendor: {vendor_name}
Compliance Score: {overall_score}/100 (Grade: {grade})
Key Findings: {json.dumps(findings)[:2000]}
Return only the summary text, no JSON."""

        response = llm.invoke(prompt)
        exec_summary = response.content if hasattr(response, "content") else str(response)

        report = {
            "status": "success",
            "report": {
                "title": f"Compliance Assessment Report - {vendor_name}",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "executive_summary": exec_summary.strip(),
                "overall_score": overall_score,
                "grade": grade,
                "risk_level": "low" if overall_score >= 80 else "medium" if overall_score >= 60 else "high" if overall_score >= 40 else "critical",
                "findings": findings,
                "recommendations": recommendations,
                "conclusion": (
                    "COMPLIANT - Vendor meets regulatory requirements."
                    if overall_score >= 70
                    else "CONDITIONAL - Vendor requires remediation."
                    if overall_score >= 50
                    else "NON-COMPLIANT - Vendor does not meet requirements."
                ),
            },
        }
        return json.dumps(report)
    except Exception as e:
        logger.error(f"Compliance report generation failed: {e}")
        return json.dumps({"status": "error", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════
# Collect all compliance tools
# ═══════════════════════════════════════════════════════════════════

COMPLIANCE_TOOLS = [
    search_compliance_policies,
    check_gdpr_compliance,
    check_hipaa_compliance,
    check_pci_compliance,
    verify_data_processing_agreement,
    assess_data_retention_policy,
    check_subprocessor_list,
    validate_privacy_policy,
    calculate_compliance_score,
    generate_compliance_report,
]
