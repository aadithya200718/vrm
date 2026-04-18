from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

from backend.core.logging import logger
from backend.core.metrics import CONTINUAL_MODEL_ACCURACY
from backend.core.repository import get_repository
from backend.core.services import get_service
from backend.learning.bayesian import calculate_bayesian_score
from backend.learning.continual import update_online_model
from backend.learning.federated import prepare_federated_update
from backend.learning.rl import predict_risk_tier, reward_for_outcome
from backend.models.domain import (
    BayesianScoreRecord,
    ModelVersionRecord,
    RLTrainingEpisodeRecord,
    RiskModelFeedbackRecord,
    VendorRecord,
)
from backend.models.enums import RiskTier, VerificationKind
from backend.tasks.celery_app import celery_app


def _load_vendor(vendor_id: str) -> VendorRecord:
    vendor = get_repository().get_vendor(vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return vendor


def _collect_signal_inputs(vendor: VendorRecord) -> tuple[list[tuple[str, float, float]], list[str]]:
    repo = get_repository()
    standard = repo.list_verifications(vendor.id)
    hipaa = repo.list_verifications(vendor.id, hipaa=True)
    hard_overrides: list[str] = []
    scores: list[tuple[str, float, float]] = []

    for item in standard:
        scores.append((item.kind.value, item.confidence_score, 1.0))
        if item.kind == VerificationKind.SANCTIONS and item.result == "flagged":
            hard_overrides.append("Sanctions flagged")

    for item in hipaa:
        scores.append((item.kind.value, item.confidence_score, 2.0))
        if item.kind == VerificationKind.OIG and item.result == "excluded":
            hard_overrides.append("OIG excluded")
        if item.kind == VerificationKind.EPHI_FLOW and item.details.get("jurisdiction_verified") is False:
            hard_overrides.append("ePHI jurisdiction violation")

    baa_record = repo.get_baa_record(vendor.id)
    if baa_record and "breach_notification_60_days" in baa_record.clauses_missing:
        hard_overrides.append("BAA missing breach notification clause")

    return scores, hard_overrides


@celery_app.task(
    bind=True,
    max_retries=3,
    name="backend.tasks.ml.calculate_bayesian_risk_task",
)
def calculate_bayesian_risk_task(self, vendor_id: str) -> dict[str, Any]:
    try:
        vendor = _load_vendor(vendor_id)
        scores, hard_overrides = _collect_signal_inputs(vendor)
        if not scores:
            return {
                "status": "failed",
                "vendor_id": vendor_id,
                "error": "No verification results available for Bayesian scoring.",
            }
        result = calculate_bayesian_score(
            scores,
            healthcare=vendor.workflow_type.value == "healthcare",
            hard_overrides=hard_overrides,
        )
        get_repository().upsert_bayesian_score(
            BayesianScoreRecord(
                vendor_id=vendor.id,
                workflow_type=vendor.workflow_type,
                probability_legitimate=result.probability_legitimate,
                probability_fraud=result.probability_fraud,
                confidence_interval=result.confidence_interval,
                risk_tier=result.risk_tier,
                evidence_explanation=result.evidence_explanation,
                hard_override=result.hard_override,
                hipaa_overrides=result.hipaa_overrides,
                hipaa_risk_factors=result.hipaa_risk_factors,
            )
        )
        logger.info(
            "Bayesian risk score calculated",
            extra={"service": "celery", "vendor_id": vendor_id, "agent": "bayesian_risk_model"},
        )
        return {
            "status": "completed",
            "vendor_id": vendor_id,
            "risk_tier": result.risk_tier,
            "probability_legitimate": result.probability_legitimate,
            "probability_fraud": result.probability_fraud,
            "confidence_interval": result.confidence_interval,
            "hard_override": result.hard_override,
        }
    except HTTPException as exc:
        return {
            "status": "failed",
            "vendor_id": vendor_id,
            "http_status": exc.status_code,
            "error": exc.detail,
        }
    except Exception as exc:
        logger.exception(
            "Failed to calculate Bayesian risk",
            extra={"service": "celery", "vendor_id": vendor_id, "agent": "bayesian_risk_model"},
        )
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(
    bind=True,
    max_retries=3,
    name="backend.tasks.ml.predict_risk_tier_task",
)
def predict_risk_tier_task(self, vendor_id: str, state_vector: list[float]) -> dict[str, Any]:
    try:
        vendor = _load_vendor(vendor_id)
        prediction = predict_risk_tier(
            state_vector,
            healthcare=vendor.workflow_type.value == "healthcare",
        )
        logger.info(
            "RL risk tier predicted",
            extra={"service": "celery", "vendor_id": vendor_id, "agent": "rl_risk_model"},
        )
        return {
            "status": "completed",
            "vendor_id": vendor_id,
            "action": prediction.action,
            "tier": prediction.tier,
            "confidence": prediction.confidence,
            "state_vector_size": len(state_vector),
        }
    except HTTPException as exc:
        return {
            "status": "failed",
            "vendor_id": vendor_id,
            "http_status": exc.status_code,
            "error": exc.detail,
        }
    except Exception as exc:
        logger.exception(
            "Failed to predict RL risk tier",
            extra={"service": "celery", "vendor_id": vendor_id, "agent": "rl_risk_model"},
        )
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(
    bind=True,
    max_retries=3,
    name="backend.tasks.ml.update_continual_model_task",
)
def update_continual_model_task(
    self,
    vendor_id: str,
    state_vector: list[float],
    outcome: str,
) -> dict[str, Any]:
    try:
        vendor = _load_vendor(vendor_id)
        healthcare = vendor.workflow_type.value == "healthcare"
        prediction = predict_risk_tier(state_vector, healthcare=healthcare)
        update = update_online_model(state_vector, outcome)
        federated = prepare_federated_update(state_vector)
        reward = reward_for_outcome(prediction.tier, outcome, healthcare=healthcare)
        repo = get_repository()

        repo.add_rl_episode(
            RLTrainingEpisodeRecord(
                vendor_id=vendor.id,
                workflow_type=vendor.workflow_type,
                state_vector=state_vector,
                action=prediction.action,
                reward=reward,
                actual_outcome=outcome,
            )
        )
        repo.add_feedback(
            RiskModelFeedbackRecord(
                vendor_id=vendor.id,
                workflow_type=vendor.workflow_type,
                predicted_tier=prediction.tier,
                actual_outcome=outcome,
                reward=reward,
            )
        )
        repo.add_model_version(
            ModelVersionRecord(
                model_name="continual_logreg",
                version="v1-online",
                workflow_type=vendor.workflow_type,
                accuracy=update.accuracy,
                metadata={"alerts": update.alerts, "vendor_id": vendor_id},
            )
        )
        repo.add_model_version(
            ModelVersionRecord(
                model_name="federated_round",
                version=federated.round_id,
                workflow_type=vendor.workflow_type,
                metadata={
                    "noise_applied": federated.noise_applied,
                    "weight_deltas": federated.weight_deltas,
                    "vendor_id": vendor_id,
                },
            )
        )
        CONTINUAL_MODEL_ACCURACY.set(update.accuracy)
        logger.info(
            "Continual model updated",
            extra={"service": "celery", "vendor_id": vendor_id, "agent": "continual_learning"},
        )
        return {
            "status": "completed",
            "vendor_id": vendor_id,
            "predicted_tier": prediction.tier,
            "accuracy": update.accuracy,
            "alerts": update.alerts,
            "reward": reward,
            "federated_round_id": federated.round_id,
        }
    except HTTPException as exc:
        return {
            "status": "failed",
            "vendor_id": vendor_id,
            "http_status": exc.status_code,
            "error": exc.detail,
        }
    except Exception as exc:
        logger.exception(
            "Failed to update continual model",
            extra={"service": "celery", "vendor_id": vendor_id, "agent": "continual_learning"},
        )
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(
    bind=True,
    max_retries=3,
    name="backend.tasks.ml.refresh_risk_assessment",
)
def refresh_risk_assessment(self, vendor_id: str) -> dict[str, Any]:
    try:
        vendor = _load_vendor(vendor_id)
        repo = get_repository()
        standard = repo.list_verifications(vendor_id)
        hipaa = repo.list_verifications(vendor_id, hipaa=True)
        if not standard and not hipaa:
            return {
                "status": "failed",
                "vendor_id": vendor_id,
                "error": "No verification results available for risk assessment refresh.",
            }
        get_service()._complete_risk_and_approval(vendor, standard, hipaa)
        logger.info(
            "Risk assessment refreshed",
            extra={"service": "celery", "vendor_id": vendor_id, "agent": "risk_refresh"},
        )
        return {
            "status": "completed",
            "vendor_id": vendor_id,
            "risk_assessment": get_service().get_vendor_risk_assessment(vendor_id),
        }
    except HTTPException as exc:
        return {
            "status": "failed",
            "vendor_id": vendor_id,
            "http_status": exc.status_code,
            "error": exc.detail,
        }
    except Exception as exc:
        logger.exception(
            "Failed to refresh risk assessment",
            extra={"service": "celery", "vendor_id": vendor_id, "agent": "risk_refresh"},
        )
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(
    bind=True,
    max_retries=3,
    name="backend.tasks.ml.retrain_rl_model_task",
)
def retrain_rl_model_task(self) -> dict[str, Any]:
    try:
        version = f"phase4-stub-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        get_repository().add_model_version(
            ModelVersionRecord(
                model_name="risk_rl_model",
                version=version,
                workflow_type=None,
                accuracy=None,
                metadata={"status": "stubbed_for_phase_4"},
            )
        )
        logger.info(
            "RL retraining stub executed",
            extra={"service": "celery", "agent": "rl_retrainer"},
        )
        return {
            "status": "scheduled",
            "message": "RL retraining is stubbed until Phase 4.",
            "model_version": version,
        }
    except Exception as exc:
        logger.exception(
            "Failed to run RL retraining stub",
            extra={"service": "celery", "agent": "rl_retrainer"},
        )
        raise self.retry(exc=exc, countdown=60)
