from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import json
from typing import Any, TypeVar

from backend.core.logging import logger
from backend.core.supabase_client import get_supabase_client
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
from backend.models.enums import VerificationKind, WorkflowType


T = TypeVar("T")
_VENDOR_STATE_KEY = "_repository_state"
_RISK_ASSESSMENT_KEY = "_risk_assessment"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_vector(value: Any) -> list[float]:
    if isinstance(value, list):
        return [float(item) for item in value]
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        try:
            raw = json.loads(text)
        except json.JSONDecodeError:
            raw = [item for item in text.strip("[]").split(",") if item]
        return [float(item) for item in raw]
    return []


def _format_vector(values: list[float]) -> str:
    return "[" + ",".join(f"{value:.6f}" for value in values) + "]"


class SupabaseRepository:
    def __init__(self) -> None:
        self.client = get_supabase_client(service_role=True) or get_supabase_client()
        self._risk_assessment_table_supported: bool | None = None

    def _require_client(self) -> Any:
        if self.client is None:
            raise RuntimeError(
                "Supabase is not configured. Set SUPABASE_URL and a valid Supabase key."
            )
        return self.client

    def _execute(self, query: Any, *, table: str, action: str) -> Any:
        try:
            return query.execute()
        except Exception as exc:  # pragma: no cover - depends on Supabase runtime
            logger.exception(
                "Supabase repository operation failed",
                extra={
                    "service": "supabase",
                    "agent": f"{action}:{table}",
                },
            )
            raise RuntimeError(f"Supabase {action} failed for table '{table}'") from exc

    def _select_rows(
        self,
        table: str,
        *,
        filters: dict[str, Any] | None = None,
        order_by: str | None = None,
        desc: bool = False,
        limit: int | None = None,
        columns: str = "*",
    ) -> list[dict[str, Any]]:
        query = self._require_client().table(table).select(columns)
        for field, value in (filters or {}).items():
            query = query.eq(field, value)
        if order_by:
            query = query.order(order_by, desc=desc)
        if limit is not None:
            query = query.limit(limit)
        response = self._execute(query, table=table, action="select")
        return list(getattr(response, "data", None) or [])

    def _select_first(
        self,
        table: str,
        *,
        filters: dict[str, Any],
        order_by: str | None = None,
        desc: bool = False,
        columns: str = "*",
    ) -> dict[str, Any] | None:
        rows = self._select_rows(
            table,
            filters=filters,
            order_by=order_by,
            desc=desc,
            limit=1,
            columns=columns,
        )
        return rows[0] if rows else None

    def _insert_or_update_by_id(self, table: str, payload: dict[str, Any]) -> dict[str, Any]:
        existing = self._select_first(table, filters={"id": payload["id"]})
        if existing:
            query = self._require_client().table(table).update(payload).eq("id", payload["id"])
            response = self._execute(query, table=table, action="update")
        else:
            query = self._require_client().table(table).insert(payload)
            response = self._execute(query, table=table, action="insert")
        rows = list(getattr(response, "data", None) or [])
        return rows[0] if rows else payload

    def _update_row(self, table: str, row_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        query = self._require_client().table(table).update(payload).eq("id", row_id)
        response = self._execute(query, table=table, action="update")
        rows = list(getattr(response, "data", None) or [])
        return rows[0] if rows else payload

    def _model_payload(self, record: Any) -> dict[str, Any]:
        payload = record.model_dump(mode="json")
        payload["updated_at"] = _now_iso()
        return payload

    def _vendor_request_from_row(
        self,
        row: dict[str, Any],
        vendor_lookup: dict[str, str] | None = None,
    ) -> VendorRequestRecord:
        payload = dict(row)
        lookup = vendor_lookup if vendor_lookup is not None else self._vendor_request_lookup()
        payload["vendor_id"] = lookup.get(payload["id"])
        return VendorRequestRecord.model_validate(payload)

    def _vendor_request_lookup(self) -> dict[str, str]:
        mapping: dict[str, str] = {}
        for row in self._select_rows("vendors", columns="id,request_id"):
            request_id = row.get("request_id")
            if request_id:
                mapping[str(request_id)] = str(row["id"])
        return mapping

    def _vendor_payload(self, record: VendorRecord) -> dict[str, Any]:
        payload = self._model_payload(record)
        metadata = dict(payload.get("metadata") or {})
        metadata[_VENDOR_STATE_KEY] = {
            "checklist_required": record.checklist_required,
            "checklist_received": record.checklist_received,
            "errors": record.errors,
            "agent_errors": record.agent_errors,
        }
        payload["metadata"] = metadata
        payload.pop("checklist_required", None)
        payload.pop("checklist_received", None)
        payload.pop("errors", None)
        payload.pop("agent_errors", None)
        return payload

    def _vendor_from_row(self, row: dict[str, Any]) -> VendorRecord:
        payload = dict(row)
        metadata = dict(payload.get("metadata") or {})
        state = dict(metadata.get(_VENDOR_STATE_KEY) or {})
        payload["metadata"] = metadata
        payload["checklist_required"] = state.get("checklist_required", 8)
        payload["checklist_received"] = state.get("checklist_received", 0)
        payload["errors"] = list(state.get("errors") or [])
        payload["agent_errors"] = list(state.get("agent_errors") or [])
        return VendorRecord.model_validate(payload)

    def _embedding_payload(self, record: VendorEmbeddingRecord) -> dict[str, Any]:
        payload = self._model_payload(record)
        payload["embedding"] = _format_vector(record.vector)
        payload.pop("vector", None)
        return payload

    def _embedding_from_row(self, row: dict[str, Any]) -> VendorEmbeddingRecord:
        payload = dict(row)
        payload["vector"] = _parse_vector(payload.pop("embedding", payload.get("vector")))
        return VendorEmbeddingRecord.model_validate(payload)

    def _risk_assessment_from_vendor_metadata(self, vendor_id: str) -> RiskAssessmentRecord | None:
        vendor = self.get_vendor(vendor_id)
        if not vendor:
            return None
        raw = (vendor.metadata or {}).get(_RISK_ASSESSMENT_KEY)
        if not raw:
            return None
        return RiskAssessmentRecord.model_validate(raw)

    def _risk_assessment_supported(self) -> bool:
        if self._risk_assessment_table_supported is not None:
            return self._risk_assessment_table_supported
        try:
            self._select_rows("risk_assessments", limit=1)
        except RuntimeError:
            self._risk_assessment_table_supported = False
        else:
            self._risk_assessment_table_supported = True
        return self._risk_assessment_table_supported

    def create_vendor_request(self, record: VendorRequestRecord) -> VendorRequestRecord:
        payload = self._model_payload(record)
        payload.pop("vendor_id", None)
        row = self._insert_or_update_by_id("vendor_requests", payload)
        return self._vendor_request_from_row(row)

    def update_vendor_request(self, record: VendorRequestRecord) -> VendorRequestRecord:
        payload = self._model_payload(record)
        payload.pop("vendor_id", None)
        row = self._update_row("vendor_requests", record.id, payload)
        return self._vendor_request_from_row(row)

    def get_vendor_request(self, request_id: str) -> VendorRequestRecord | None:
        row = self._select_first("vendor_requests", filters={"id": request_id})
        if not row:
            return None
        return self._vendor_request_from_row(row)

    def list_vendor_requests(self) -> list[VendorRequestRecord]:
        vendor_lookup = self._vendor_request_lookup()
        return [
            self._vendor_request_from_row(row, vendor_lookup=vendor_lookup)
            for row in self._select_rows("vendor_requests", order_by="created_at")
        ]

    def create_vendor(self, record: VendorRecord) -> VendorRecord:
        row = self._insert_or_update_by_id("vendors", self._vendor_payload(record))
        return self._vendor_from_row(row)

    def update_vendor(self, record: VendorRecord) -> VendorRecord:
        row = self._update_row("vendors", record.id, self._vendor_payload(record))
        return self._vendor_from_row(row)

    def get_vendor(self, vendor_id: str) -> VendorRecord | None:
        row = self._select_first("vendors", filters={"id": vendor_id})
        if not row:
            return None
        return self._vendor_from_row(row)

    def list_vendors(self) -> list[VendorRecord]:
        return [
            self._vendor_from_row(row)
            for row in self._select_rows("vendors", order_by="created_at")
        ]

    def create_document(self, record: VendorDocumentRecord) -> VendorDocumentRecord:
        row = self._insert_or_update_by_id("vendor_documents", self._model_payload(record))
        return VendorDocumentRecord.model_validate(row)

    def update_document(self, record: VendorDocumentRecord) -> VendorDocumentRecord:
        row = self._update_row("vendor_documents", record.id, self._model_payload(record))
        return VendorDocumentRecord.model_validate(row)

    def get_document(self, document_id: str) -> VendorDocumentRecord | None:
        row = self._select_first("vendor_documents", filters={"id": document_id})
        if not row:
            return None
        return VendorDocumentRecord.model_validate(row)

    def list_documents(self, vendor_id: str) -> list[VendorDocumentRecord]:
        return [
            VendorDocumentRecord.model_validate(row)
            for row in self._select_rows(
                "vendor_documents",
                filters={"vendor_id": vendor_id},
                order_by="created_at",
            )
        ]

    def upsert_verification(
        self,
        record: VerificationResultRecord | HipaaVerificationRecord,
        hipaa: bool = False,
    ) -> VerificationResultRecord | HipaaVerificationRecord:
        table = "hipaa_verifications" if hipaa else "verification_results"
        existing = self._select_first(
            table,
            filters={"vendor_id": record.vendor_id, "kind": record.kind.value},
        )
        payload = self._model_payload(record)
        if existing:
            payload["id"] = existing["id"]
        row = self._insert_or_update_by_id(table, payload)
        model_cls = HipaaVerificationRecord if hipaa else VerificationResultRecord
        return model_cls.model_validate(row)

    def list_verifications(
        self,
        vendor_id: str,
        hipaa: bool = False,
    ) -> list[VerificationResultRecord] | list[HipaaVerificationRecord]:
        table = "hipaa_verifications" if hipaa else "verification_results"
        model_cls = HipaaVerificationRecord if hipaa else VerificationResultRecord
        return [
            model_cls.model_validate(row)
            for row in self._select_rows(
                table,
                filters={"vendor_id": vendor_id},
                order_by="created_at",
            )
        ]

    def get_verification_by_kind(
        self,
        vendor_id: str,
        kind: VerificationKind,
        hipaa: bool = False,
    ) -> VerificationResultRecord | HipaaVerificationRecord | None:
        table = "hipaa_verifications" if hipaa else "verification_results"
        row = self._select_first(
            table,
            filters={"vendor_id": vendor_id, "kind": kind.value},
        )
        if not row:
            return None
        model_cls = HipaaVerificationRecord if hipaa else VerificationResultRecord
        return model_cls.model_validate(row)

    def upsert_baa_record(self, record: BAARecord) -> BAARecord:
        existing = self._select_first("baa_records", filters={"vendor_id": record.vendor_id})
        payload = self._model_payload(record)
        if existing:
            payload["id"] = existing["id"]
        row = self._insert_or_update_by_id("baa_records", payload)
        return BAARecord.model_validate(row)

    def get_baa_record(self, vendor_id: str) -> BAARecord | None:
        row = self._select_first("baa_records", filters={"vendor_id": vendor_id})
        if not row:
            return None
        return BAARecord.model_validate(row)

    def upsert_approval(self, record: ApprovalWorkflowRecord) -> ApprovalWorkflowRecord:
        existing = self._select_first("approvals", filters={"vendor_id": record.vendor_id})
        payload = self._model_payload(record)
        if existing:
            payload["id"] = existing["id"]
        row = self._insert_or_update_by_id("approvals", payload)
        return ApprovalWorkflowRecord.model_validate(row)

    def get_approval(self, vendor_id: str) -> ApprovalWorkflowRecord | None:
        row = self._select_first("approvals", filters={"vendor_id": vendor_id})
        if not row:
            return None
        return ApprovalWorkflowRecord.model_validate(row)

    def add_approval_decision(self, record: ApprovalDecisionRecord) -> ApprovalDecisionRecord:
        row = self._insert_or_update_by_id("approval_decisions", self._model_payload(record))
        return ApprovalDecisionRecord.model_validate(row)

    def list_approval_decisions(self, vendor_id: str) -> list[ApprovalDecisionRecord]:
        filters = {"vendor_id": vendor_id} if vendor_id else None
        return [
            ApprovalDecisionRecord.model_validate(row)
            for row in self._select_rows(
                "approval_decisions",
                filters=filters,
                order_by="created_at",
            )
        ]

    def create_onboarding_token(self, record: OnboardingTokenRecord) -> OnboardingTokenRecord:
        row = self._insert_or_update_by_id("onboarding_tokens", self._model_payload(record))
        return OnboardingTokenRecord.model_validate(row)

    def get_onboarding_token(self, token: str) -> OnboardingTokenRecord | None:
        row = self._select_first("onboarding_tokens", filters={"token": token})
        if not row:
            return None
        return OnboardingTokenRecord.model_validate(row)

    def update_onboarding_token(self, record: OnboardingTokenRecord) -> OnboardingTokenRecord:
        row = self._update_row("onboarding_tokens", record.id, self._model_payload(record))
        return OnboardingTokenRecord.model_validate(row)

    def add_notification(self, record: NotificationLogRecord) -> NotificationLogRecord:
        row = self._insert_or_update_by_id("notifications_log", self._model_payload(record))
        return NotificationLogRecord.model_validate(row)

    def list_notifications(self, vendor_id: str | None = None) -> list[NotificationLogRecord]:
        filters = {"vendor_id": vendor_id} if vendor_id is not None else None
        return [
            NotificationLogRecord.model_validate(row)
            for row in self._select_rows(
                "notifications_log",
                filters=filters,
                order_by="created_at",
            )
        ]

    def upsert_bayesian_score(self, record: BayesianScoreRecord) -> BayesianScoreRecord:
        existing = self._select_first("bayesian_scores", filters={"vendor_id": record.vendor_id})
        payload = self._model_payload(record)
        if existing:
            payload["id"] = existing["id"]
        row = self._insert_or_update_by_id("bayesian_scores", payload)
        return BayesianScoreRecord.model_validate(row)

    def get_bayesian_score(self, vendor_id: str) -> BayesianScoreRecord | None:
        row = self._select_first("bayesian_scores", filters={"vendor_id": vendor_id})
        if not row:
            return None
        return BayesianScoreRecord.model_validate(row)

    def upsert_risk_assessment(self, record: RiskAssessmentRecord) -> RiskAssessmentRecord:
        payload = self._model_payload(record)
        if self._risk_assessment_supported():
            existing = self._select_first(
                "risk_assessments",
                filters={"vendor_id": record.vendor_id},
            )
            if existing:
                payload["id"] = existing["id"]
            row = self._insert_or_update_by_id("risk_assessments", payload)
            return RiskAssessmentRecord.model_validate(row)

        vendor = self.get_vendor(record.vendor_id)
        if not vendor:
            raise RuntimeError(f"Vendor '{record.vendor_id}' not found for risk assessment storage")
        vendor.metadata[_RISK_ASSESSMENT_KEY] = payload
        self.update_vendor(vendor)
        return RiskAssessmentRecord.model_validate(payload)

    def get_risk_assessment(self, vendor_id: str) -> RiskAssessmentRecord | None:
        if self._risk_assessment_supported():
            row = self._select_first("risk_assessments", filters={"vendor_id": vendor_id})
            if row:
                return RiskAssessmentRecord.model_validate(row)
        return self._risk_assessment_from_vendor_metadata(vendor_id)

    def add_rl_episode(self, record: RLTrainingEpisodeRecord) -> RLTrainingEpisodeRecord:
        row = self._insert_or_update_by_id("rl_training_episodes", self._model_payload(record))
        return RLTrainingEpisodeRecord.model_validate(row)

    def add_feedback(self, record: RiskModelFeedbackRecord) -> RiskModelFeedbackRecord:
        row = self._insert_or_update_by_id("risk_model_feedback", self._model_payload(record))
        return RiskModelFeedbackRecord.model_validate(row)

    def add_model_version(self, record: ModelVersionRecord) -> ModelVersionRecord:
        row = self._insert_or_update_by_id("model_versions", self._model_payload(record))
        return ModelVersionRecord.model_validate(row)

    def list_model_versions(self, model_name: str | None = None) -> list[ModelVersionRecord]:
        filters = {"model_name": model_name} if model_name is not None else None
        return [
            ModelVersionRecord.model_validate(row)
            for row in self._select_rows(
                "model_versions",
                filters=filters,
                order_by="created_at",
                desc=True,
            )
        ]

    def upsert_embedding(self, record: VendorEmbeddingRecord) -> VendorEmbeddingRecord:
        existing = self._select_first(
            "vendor_embeddings",
            filters={"document_id": record.document_id},
        )
        payload = self._embedding_payload(record)
        if existing:
            payload["id"] = existing["id"]
        row = self._insert_or_update_by_id("vendor_embeddings", payload)
        return self._embedding_from_row(row)

    def list_embeddings(self, vendor_id: str) -> list[VendorEmbeddingRecord]:
        return [
            self._embedding_from_row(row)
            for row in self._select_rows(
                "vendor_embeddings",
                filters={"vendor_id": vendor_id},
                order_by="created_at",
            )
        ]

    def upsert_scheduled_task(self, record: ScheduledTaskRecord) -> ScheduledTaskRecord:
        existing = self._select_first(
            "scheduled_tasks",
            filters={"vendor_id": record.vendor_id, "task_type": record.task_type},
        )
        payload = self._model_payload(record)
        if existing:
            payload["id"] = existing["id"]
        row = self._insert_or_update_by_id("scheduled_tasks", payload)
        return ScheduledTaskRecord.model_validate(row)

    def list_scheduled_tasks(self, vendor_id: str | None = None) -> list[ScheduledTaskRecord]:
        filters = {"vendor_id": vendor_id} if vendor_id is not None else None
        return [
            ScheduledTaskRecord.model_validate(row)
            for row in self._select_rows(
                "scheduled_tasks",
                filters=filters,
                order_by="due_at",
            )
        ]

    def add_ephi_access_log(self, record: EPHIAccessLogRecord) -> EPHIAccessLogRecord:
        row = self._insert_or_update_by_id("ephi_access_log", self._model_payload(record))
        return EPHIAccessLogRecord.model_validate(row)

    def list_ephi_access_logs(self, vendor_id: str) -> list[EPHIAccessLogRecord]:
        return [
            EPHIAccessLogRecord.model_validate(row)
            for row in self._select_rows(
                "ephi_access_log",
                filters={"vendor_id": vendor_id},
                order_by="created_at",
            )
        ]

    def add_event(self, record: WorkflowEventRecord) -> WorkflowEventRecord:
        row = self._insert_or_update_by_id("workflow_events", self._model_payload(record))
        return WorkflowEventRecord.model_validate(row)

    def list_events(self, vendor_id: str) -> list[WorkflowEventRecord]:
        return [
            WorkflowEventRecord.model_validate(row)
            for row in self._select_rows(
                "workflow_events",
                filters={"vendor_id": vendor_id},
                order_by="created_at",
            )
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
            self.list_approval_decisions(vendor_id=""),
            key=lambda item: item.updated_at,
            reverse=True,
        )
        completed = [item for item in vendors if item.status.value == "FULLY_APPROVED"]
        return {
            "recent_vendors": vendors[:5],
            "recent_approvals": approvals[:5],
            "recent_completions": completed[:5],
        }
