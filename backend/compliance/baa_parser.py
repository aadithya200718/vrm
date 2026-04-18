from __future__ import annotations

from dataclasses import dataclass


MANDATORY_CLAUSES = {
    "breach_notification_60_days": ["breach", "60", "days"],
    "encryption_at_rest_in_transit": ["encryption", "rest", "transit"],
    "subprocessor_obligation": ["subprocessor", "obligation"],
    "phi_return_destruction": ["return", "destruction", "termination"],
    "audit_rights": ["audit", "rights"],
    "minimum_necessary_use": ["minimum", "necessary"],
}


@dataclass(slots=True)
class BAAAnalysis:
    status: str
    confidence_score: float
    clauses: dict[str, dict[str, object]]
    missing: list[str]


def analyze_baa(text: str) -> BAAAnalysis:
    lowered = text.lower()
    clauses: dict[str, dict[str, object]] = {}
    missing: list[str] = []
    present_count = 0
    for clause, keywords in MANDATORY_CLAUSES.items():
        present = all(keyword in lowered for keyword in keywords)
        if present:
            present_count += 1
        else:
            missing.append(clause)
        clauses[clause] = {
            "present": present,
            "exact_quote": "" if not present else f"Matched keywords: {', '.join(keywords)}",
            "confidence": 0.9 if present else 0.2,
        }
    confidence = round(present_count / len(MANDATORY_CLAUSES), 4)
    return BAAAnalysis(
        status="BAA_COMPLETE" if not missing else "BAA_INCOMPLETE",
        confidence_score=confidence,
        clauses=clauses,
        missing=missing,
    )

