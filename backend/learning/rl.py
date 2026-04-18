from __future__ import annotations

from dataclasses import dataclass

from backend.models.enums import RiskTier


@dataclass(slots=True)
class RLPrediction:
    action: int
    tier: str
    confidence: float


def build_state_vector(features: list[float], healthcare: bool = False) -> list[float]:
    return features[:13] if healthcare else features[:8]


def predict_risk_tier(state_vector: list[float], healthcare: bool = False) -> RLPrediction:
    average = sum(state_vector) / max(1, len(state_vector))
    if healthcare and any(value < 0.2 for value in state_vector[-5:]):
        return RLPrediction(action=3, tier=RiskTier.AUTO_REJECT.value, confidence=0.91)
    if average > 0.84:
        return RLPrediction(action=0, tier=RiskTier.TIER_3.value, confidence=0.83)
    if average > 0.65:
        return RLPrediction(action=1, tier=RiskTier.TIER_2.value, confidence=0.72)
    return RLPrediction(action=2, tier=RiskTier.TIER_1.value, confidence=0.79)


def reward_for_outcome(predicted_tier: str, actual_outcome: str, healthcare: bool = False) -> float:
    if predicted_tier == RiskTier.AUTO_REJECT.value and actual_outcome in {"breach", "fraud", "rejected"}:
        return 2.0
    if actual_outcome == "approved" and predicted_tier == RiskTier.TIER_3.value:
        return 1.0
    if actual_outcome in {"breach", "fraud"}:
        return -10.0 if healthcare else -5.0
    if actual_outcome == "approved":
        return -1.0
    return 0.25

