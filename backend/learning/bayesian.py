from __future__ import annotations

from dataclasses import dataclass

from backend.models.enums import RiskTier


@dataclass(slots=True)
class BayesianResult:
    probability_legitimate: float
    probability_fraud: float
    confidence_interval: dict[str, float]
    risk_tier: str
    evidence_explanation: list[str]
    hard_override: str | None
    hipaa_overrides: list[str]
    hipaa_risk_factors: list[str]


def calculate_bayesian_score(
    scores: list[tuple[str, float, float]],
    healthcare: bool = False,
    hard_overrides: list[str] | None = None,
) -> BayesianResult:
    prior = 0.65 if healthcare else 0.75
    posterior = prior
    explanations: list[str] = []
    hipaa_factors: list[str] = []
    for name, confidence, weight in scores:
        delta = ((confidence - 0.5) * 0.4) * weight
        posterior = min(0.99, max(0.01, posterior + delta))
        explanations.append(f"{name} adjusted score by {delta:+.2f}")
        if healthcare and weight > 1:
            hipaa_factors.append(name)

    override = hard_overrides[0] if hard_overrides else None
    if override:
        posterior = 0.01

    if override:
        tier = RiskTier.AUTO_REJECT.value
    elif posterior > 0.85:
        tier = RiskTier.TIER_3.value
    elif posterior > 0.65:
        tier = RiskTier.TIER_2.value
    else:
        tier = RiskTier.TIER_1.value

    width = 0.06 if posterior > 0.8 else 0.1
    return BayesianResult(
        probability_legitimate=round(posterior, 4),
        probability_fraud=round(1 - posterior, 4),
        confidence_interval={
            "low": round(max(0.0, posterior - width), 4),
            "high": round(min(1.0, posterior + width), 4),
        },
        risk_tier=tier,
        evidence_explanation=explanations,
        hard_override=override,
        hipaa_overrides=hard_overrides or [],
        hipaa_risk_factors=hipaa_factors,
    )

