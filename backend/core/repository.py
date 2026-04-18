from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Iterable

from backend.core.config import get_settings
from backend.core.supabase_repository import SupabaseRepository
from backend.models.domain import (
    ApprovalDecisionRecord,
    ApprovalWorkflowRecord,
    BAARecord,
    BayesianScoreRecord,
    EPHIAccessLogRecord,
    HipaaVerificationRecord,
    ModelVersionRecord,
    NotificationLogRecord,
    OnboardingTokenRecord,
    RLTrainingEpisodeRecord,
    RiskAssessmentRecord,
    RiskModelFeedbackRecord,
    ScheduledTaskRecord,
    VendorDocumentRecord,
    VendorEmbeddingRecord,
    VendorRecord,
    VendorRequestRecord,
    VerificationResultRecord,
    WorkflowEventRecord,
)
from backend.models.enums import Role, VerificationKind, WorkflowType


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class JsonRepository:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write(self._empty())

    def _empty(self) -> dict[str, list[dict[str, Any]]]:
        return {
            "vendor_requests": [],
            "vendors": [],
            "vendor_documents": [],
            "verification_results": [],
            "hipaa_verifications": [],
            "baa_records": [],
            "approvals": [],
            "approval_decisions": [],
            "onboarding_tokens": [],
            "notifications_log": [],
            "bayesian_scores": [],
            "risk_assessments": [],
            "rl_training_episodes": [],
            "risk_model_feedback": [],
            "model_versions": [],
            "vendor_embeddings": [],
            "scheduled_tasks": [],
            "ephi_access_log": [],
            "workflow_events": [],
        }

    def _read(self) -> dict[str, list[dict[str, Any]]]:
        with self.path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def _write(self, payload: dict[str, list[dict[str, Any]]]) -> None:
        with self.path.open("w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2, default=str)

    def _upsert(self, bucket: list[dict[str, Any]], record: dict[str, Any]) -> None:
        for index, existing in enumerate(bucket):
            if existing["id"] == record["id"]:
                bucket[index] = record
                return
        bucket.append(record)

    def _persist_model(self, table: str, model: Any) -> Any:
        with self._lock:
            state = self._read()
            record = model.model_dump(mode="json")
            record["updated_at"] = _now_iso()
            self._upsert(state[table], record)
            self._write(state)
        return model

    def _load_models(self, table: str, model_cls: Any) -> list[Any]:
        state = self._read()
        return [model_cls.model_validate(item) for item in state[table]]

    def _find_model(self, table: str, model_cls: Any, item_id: str) -> Any | None:
        for item in self._load_models(table, model_cls):
            if item.id == item_id:
                return item
        return None

    def create_vendor_request(self, record: VendorRequestRecord) -> VendorRequestRecord:
        return self._persist_model("vendor_requests", record)

    def update_vendor_request(self, record: VendorRequestRecord) -> VendorRequestRecord:
        return self._persist_model("vendor_requests", record)

    def get_vendor_request(self, request_id: str) -> VendorRequestRecord | None:
        return self._find_model("vendor_requests", VendorRequestRecord, request_id)

    def list_vendor_requests(self) -> list[VendorRequestRecord]:
        return self._load_models("vendor_requests", VendorRequestRecord)

    def create_vendor(self, record: VendorRecord) -> VendorRecord:
        return self._persist_model("vendors", record)

    def update_vendor(self, record: VendorRecord) -> VendorRecord:
        return self._persist_model("vendors", record)

    def get_vendor(self, vendor_id: str) -> VendorRecord | None:
        return self._find_model("vendors", VendorRecord, vendor_id)

    def list_vendors(self) -> list[VendorRecord]:
        return self._load_models("vendors", VendorRecord)

    def create_document(self, record: VendorDocumentRecord) -> VendorDocumentRecord:
        return self._persist_model("vendor_documents", record)

    def update_document(self, record: VendorDocumentRecord) -> VendorDocumentRecord:
        return self._persist_model("vendor_documents", record)

    def get_document(self, document_id: str) -> VendorDocumentRecord | None:
        return self._find_model("vendor_documents", VendorDocumentRecord, document_id)

    def list_documents(self, vendor_id: str) -> list[VendorDocumentRecord]:
        return [
            item
            for item in self._load_models("vendor_documents", VendorDocumentRecord)
            if item.vendor_id == vendor_id
        ]

    def upsert_verification(
        self,
        record: VerificationResultRecord | HipaaVerificationRecord,
        hipaa: bool = False,
    ) -> VerificationResultRecord | HipaaVerificationRecord:
        table = "hipaa_verifications" if hipaa else "verification_results"
        return self._persist_model(table, record)

    def list_verifications(
        self,
        vendor_id: str,
        hipaa: bool = False,
    ) -> list[VerificationResultRecord]:
        table = "hipaa_verifications" if hipaa else "verification_results"
        model_cls = HipaaVerificationRecord if hipaa else VerificationResultRecord
        return [
            item
            for item in self._load_models(table, model_cls)
            if item.vendor_id == vendor_id
        ]

    def get_verification_by_kind(
        self,
        vendor_id: str,
        kind: VerificationKind,
        hipaa: bool = False,
    ) -> VerificationResultRecord | None:
        for item in self.list_verifications(vendor_id, hipaa=hipaa):
            if item.kind == kind:
                return item
        return None

    def upsert_baa_record(self, record: BAARecord) -> BAARecord:
        return self._persist_model("baa_records", record)

    def get_baa_record(self, vendor_id: str) -> BAARecord | None:
        for item in self._load_models("baa_records", BAARecord):
            if item.vendor_id == vendor_id:
                return item
        return None

    def upsert_approval(self, record: ApprovalWorkflowRecord) -> ApprovalWorkflowRecord:
        return self._persist_model("approvals", record)

    def get_approval(self, vendor_id: str) -> ApprovalWorkflowRecord | None:
        for item in self._load_models("approvals", ApprovalWorkflowRecord):
            if item.vendor_id == vendor_id:
                return item
        return None

    def add_approval_decision(self, record: ApprovalDecisionRecord) -> ApprovalDecisionRecord:
        return self._persist_model("approval_decisions", record)

    def list_approval_decisions(self, vendor_id: str) -> list[ApprovalDecisionRecord]:
        return [
            item
            for item in self._load_models("approval_decisions", ApprovalDecisionRecord)
            if item.vendor_id == vendor_id
        ]

    def create_onboarding_token(self, record: OnboardingTokenRecord) -> OnboardingTokenRecord:
        return self._persist_model("onboarding_tokens", record)

    def get_onboarding_token(self, token: str) -> OnboardingTokenRecord | None:
        for item in self._load_models("onboarding_tokens", OnboardingTokenRecord):
            if item.token == token:
                return item
        return None

    def update_onboarding_token(self, record: OnboardingTokenRecord) -> OnboardingTokenRecord:
        return self._persist_model("onboarding_tokens", record)

    def add_notification(self, record: NotificationLogRecord) -> NotificationLogRecord:
        return self._persist_model("notifications_log", record)

    def list_notifications(self, vendor_id: str | None = None) -> list[NotificationLogRecord]:
        items = self._load_models("notifications_log", NotificationLogRecord)
        return [item for item in items if vendor_id is None or item.vendor_id == vendor_id]

    def upsert_bayesian_score(self, record: BayesianScoreRecord) -> BayesianScoreRecord:
        return self._persist_model("bayesian_scores", record)

    def get_bayesian_score(self, vendor_id: str) -> BayesianScoreRecord | None:
        for item in self._load_models("bayesian_scores", BayesianScoreRecord):
            if item.vendor_id == vendor_id:
                return item
        return None

    def upsert_risk_assessment(self, record: RiskAssessmentRecord) -> RiskAssessmentRecord:
        return self._persist_model("risk_assessments", record)

    def get_risk_assessment(self, vendor_id: str) -> RiskAssessmentRecord | None:
        for item in self._load_models("risk_assessments", RiskAssessmentRecord):
            if item.vendor_id == vendor_id:
                return item
        return None

    def add_rl_episode(self, record: RLTrainingEpisodeRecord) -> RLTrainingEpisodeRecord:
        return self._persist_model("rl_training_episodes", record)

    def add_feedback(self, record: RiskModelFeedbackRecord) -> RiskModelFeedbackRecord:
        return self._persist_model("risk_model_feedback", record)

    def add_model_version(self, record: ModelVersionRecord) -> ModelVersionRecord:
        return self._persist_model("model_versions", record)

    def list_model_versions(self, model_name: str | None = None) -> list[ModelVersionRecord]:
        items = self._load_models("model_versions", ModelVersionRecord)
        return [item for item in items if model_name is None or item.model_name == model_name]

    def upsert_embedding(self, record: VendorEmbeddingRecord) -> VendorEmbeddingRecord:
        return self._persist_model("vendor_embeddings", record)

    def list_embeddings(self, vendor_id: str) -> list[VendorEmbeddingRecord]:
        return [
            item
            for item in self._load_models("vendor_embeddings", VendorEmbeddingRecord)
            if item.vendor_id == vendor_id
        ]

    def upsert_scheduled_task(self, record: ScheduledTaskRecord) -> ScheduledTaskRecord:
        return self._persist_model("scheduled_tasks", record)

    def list_scheduled_tasks(self, vendor_id: str | None = None) -> list[ScheduledTaskRecord]:
        items = self._load_models("scheduled_tasks", ScheduledTaskRecord)
        return [item for item in items if vendor_id is None or item.vendor_id == vendor_id]

    def add_ephi_access_log(self, record: EPHIAccessLogRecord) -> EPHIAccessLogRecord:
        return self._persist_model("ephi_access_log", record)

    def list_ephi_access_logs(self, vendor_id: str) -> list[EPHIAccessLogRecord]:
        return [
            item
            for item in self._load_models("ephi_access_log", EPHIAccessLogRecord)
            if item.vendor_id == vendor_id
        ]

    def add_event(self, record: WorkflowEventRecord) -> WorkflowEventRecord:
        return self._persist_model("workflow_events", record)

    def list_events(self, vendor_id: str) -> list[WorkflowEventRecord]:
        return [
            item
            for item in self._load_models("workflow_events", WorkflowEventRecord)
            if item.vendor_id == vendor_id
        ]

    def dashboard_stats(self) -> dict[str, Any]:
        vendors = self.list_vendors()
        requests = self.list_vendor_requests()
        by_status: dict[str, int] = defaultdict(int)
        for vendor in vendors:
            by_status[vendor.status.value] += 1
        healthcare = sum(1 for item in vendors if item.workflow_type == WorkflowType.HEALTHCARE)
        approval_pending = sum(
            1 for item in vendors if (item.approval_status or "").lower().startswith("pending")
        )
        return {
            "total_vendors": len(vendors),
            "total_requests": len(requests),
            "healthcare_vendors": healthcare,
            "pending_approvals": approval_pending,
            "fully_approved": by_status.get("FULLY_APPROVED", 0),
            "rejected": by_status.get("REJECTED", 0),
        }

    def dashboard_recent(self) -> dict[str, Any]:
        vendors = sorted(self.list_vendors(), key=lambda item: item.updated_at, reverse=True)
        approvals = sorted(
            self._load_models("approval_decisions", ApprovalDecisionRecord),
            key=lambda item: item.updated_at,
            reverse=True,
        )
        completed = [item for item in vendors if item.status.value == "FULLY_APPROVED"]
        return {
            "recent_vendors": vendors[:5],
            "recent_approvals": approvals[:5],
            "recent_completions": completed[:5],
        }


RepositoryType = JsonRepository | SupabaseRepository


_repo: RepositoryType | None = None


def get_repository() -> RepositoryType:
    global _repo
    settings = get_settings()
    if settings.data_backend == "supabase":
        if not isinstance(_repo, SupabaseRepository):
            _repo = SupabaseRepository()
        return _repo

    if not isinstance(_repo, JsonRepository):
        _repo = JsonRepository(path=settings.data_file)
    return _repo
