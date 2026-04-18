from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class EPHIFlowAnalysis:
    result: str
    confidence_score: float
    risks: list[str]
    encryption_verified: bool
    jurisdiction_verified: bool


def analyze_ephi_flow(text: str) -> EPHIFlowAnalysis:
    lowered = text.lower()
    encryption_verified = "encryption" in lowered
    jurisdiction_verified = "india" in lowered or "us" in lowered or "jurisdiction" in lowered
    risks: list[str] = []
    if not encryption_verified:
        risks.append("Unencrypted segment detected")
    if "cross-border" in lowered or "outside jurisdiction" in lowered:
        jurisdiction_verified = False
        risks.append("ePHI may leave allowed jurisdiction")
    result = "compliant" if not risks else "non_compliant"
    confidence = 0.92 if result == "compliant" else 0.45
    return EPHIFlowAnalysis(
        result=result,
        confidence_score=confidence,
        risks=risks,
        encryption_verified=encryption_verified,
        jurisdiction_verified=jurisdiction_verified,
    )

