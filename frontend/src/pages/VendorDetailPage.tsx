import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { useDeferredValue, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useShell } from "../app/ShellContext";
import {
  getVendorApprovalStatus,
  getVendorCompliance,
  getVendorDocuments,
  getVendorEvidenceGaps,
  getVendorEvidenceStatus,
  getVendorFinancial,
  getVendorReport,
  getVendorRiskAssessment,
  getVendorSecurity,
  getVendorStatus,
  requestVendorEvidence,
  uploadVendorDocuments,
} from "../lib/api";
import { resolveStageFromVendorStatus, toneForRisk, toneForStatus } from "../lib/status";
import { formatCurrency, formatDateTime, formatPercent, normalizeText } from "../lib/utils";
import { StateView } from "../components/StateView";
import { StatusBadge } from "../components/StatusBadge";

function asRecord(value: unknown) {
  return value && typeof value === "object" ? (value as Record<string, unknown>) : {};
}

function asStringList(value: unknown) {
  return Array.isArray(value) ? value.map((entry) => String(entry)) : [];
}

export function VendorDetailPage() {
  const { vendorId = "" } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { searchValue, liveEvents, eventMode, setActiveVendorId } = useShell();
  const deferredSearch = useDeferredValue(normalizeText(searchValue));
  const [pendingFiles, setPendingFiles] = useState<File[]>([]);

  useEffect(() => {
    setActiveVendorId(vendorId);
    return () => setActiveVendorId("");
  }, [setActiveVendorId, vendorId]);

  const statusQuery = useQuery({
    queryKey: ["vendor", vendorId, "status"],
    queryFn: () => getVendorStatus(vendorId),
    enabled: Boolean(vendorId),
    refetchInterval: 12_000,
  });
  const reportQuery = useQuery({
    queryKey: ["vendor", vendorId, "report"],
    queryFn: () => getVendorReport(vendorId),
    enabled: Boolean(vendorId),
  });
  const securityQuery = useQuery({
    queryKey: ["vendor", vendorId, "security"],
    queryFn: () => getVendorSecurity(vendorId),
    enabled: Boolean(vendorId),
  });
  const complianceQuery = useQuery({
    queryKey: ["vendor", vendorId, "compliance"],
    queryFn: () => getVendorCompliance(vendorId),
    enabled: Boolean(vendorId),
  });
  const financialQuery = useQuery({
    queryKey: ["vendor", vendorId, "financial"],
    queryFn: () => getVendorFinancial(vendorId),
    enabled: Boolean(vendorId),
  });
  const evidenceQuery = useQuery({
    queryKey: ["vendor", vendorId, "evidence-gaps"],
    queryFn: () => getVendorEvidenceGaps(vendorId),
    enabled: Boolean(vendorId),
  });
  const evidenceStatusQuery = useQuery({
    queryKey: ["vendor", vendorId, "evidence-status"],
    queryFn: () => getVendorEvidenceStatus(vendorId),
    enabled: Boolean(vendorId),
  });
  const riskQuery = useQuery({
    queryKey: ["vendor", vendorId, "risk-assessment"],
    queryFn: () => getVendorRiskAssessment(vendorId),
    enabled: Boolean(vendorId),
  });
  const approvalStatusQuery = useQuery({
    queryKey: ["vendor", vendorId, "approval-status"],
    queryFn: () => getVendorApprovalStatus(vendorId),
    enabled: Boolean(vendorId),
  });
  const documentsQuery = useQuery({
    queryKey: ["vendor", vendorId, "documents"],
    queryFn: () => getVendorDocuments(vendorId),
    enabled: Boolean(vendorId),
  });

  const requestEvidenceMutation = useMutation({
    mutationFn: () => requestVendorEvidence(vendorId),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["vendor", vendorId, "evidence-gaps"] }),
        queryClient.invalidateQueries({ queryKey: ["vendor", vendorId, "evidence-status"] }),
        queryClient.invalidateQueries({ queryKey: ["vendor", vendorId, "report"] }),
      ]);
    },
  });

  const uploadDocumentsMutation = useMutation({
    mutationFn: () => uploadVendorDocuments(vendorId, pendingFiles),
    onSuccess: async () => {
      setPendingFiles([]);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["vendor", vendorId, "documents"] }),
        queryClient.invalidateQueries({ queryKey: ["vendor", vendorId, "status"] }),
        queryClient.invalidateQueries({ queryKey: ["vendor", vendorId, "report"] }),
      ]);
    },
  });

  const refetchAll = async () => {
    await Promise.all([
      statusQuery.refetch(),
      reportQuery.refetch(),
      securityQuery.refetch(),
      complianceQuery.refetch(),
      financialQuery.refetch(),
      evidenceQuery.refetch(),
      evidenceStatusQuery.refetch(),
      riskQuery.refetch(),
      approvalStatusQuery.refetch(),
      documentsQuery.refetch(),
    ]);
  };

  const report = reportQuery.data;
  const securityReview = asRecord(securityQuery.data?.security_review);
  const complianceReview = asRecord(complianceQuery.data?.compliance_review);
  const financialReview = asRecord(financialQuery.data?.financial_review);
  const riskAssessment = asRecord(riskQuery.data?.risk_assessment ?? report?.risk_assessment);
  const documents = documentsQuery.data?.documents || [];
  const evidenceRequests = evidenceQuery.data?.evidence_requests || [];
  const approvalStatus = approvalStatusQuery.data;

  const findings = useMemo(() => {
    return [
      ...asStringList(securityReview.critical_issues),
      ...asStringList(complianceReview.gaps),
      ...asStringList(financialReview.findings),
    ].filter((entry) =>
      deferredSearch ? normalizeText(entry).includes(deferredSearch) : true,
    );
  }, [complianceReview.gaps, deferredSearch, financialReview.findings, securityReview.critical_issues]);

  const filteredDocuments = useMemo(() => {
    return documents.filter((document) => {
      const haystack = normalizeText(
        `${document.file_name || ""} ${document.classification || ""} ${document.processing_status || ""}`,
      );
      return deferredSearch ? haystack.includes(deferredSearch) : true;
    });
  }, [deferredSearch, documents]);

  const filteredEvidence = useMemo(() => {
    return evidenceRequests.filter((request) => {
      const haystack = normalizeText(
        `${request.document_type} ${request.reason || ""} ${request.status || ""}`,
      );
      return deferredSearch ? haystack.includes(deferredSearch) : true;
    });
  }, [deferredSearch, evidenceRequests]);

  if (statusQuery.isLoading || reportQuery.isLoading) {
    return (
      <div className="page">
        <StateView
          detail="Loading vendor workspace, review outputs, and evidence state."
          title="Vendor Workspace Loading"
        />
      </div>
    );
  }

  if (statusQuery.isError || !statusQuery.data) {
    return (
      <div className="page">
        <StateView
          detail="The vendor status endpoint failed, so the workspace cannot be rendered."
          title="Vendor Workspace Unavailable"
          tone="danger"
        />
      </div>
    );
  }

  const status = statusQuery.data;

  const overallRiskScore = Number(
    riskAssessment.overall_risk_score ?? status.overall_risk_score ?? 0,
  );
  const riskLevel = String(riskAssessment.risk_level ?? status.risk_level ?? "Pending");
  const currentStage = resolveStageFromVendorStatus(status);

  return (
    <div className="page">
      <section className="page__header">
        <div>
          <StatusBadge tone="info">
            {String(
              riskAssessment.approval_tier ??
                status.approval_tier ??
                "Tier Pending",
            )}
          </StatusBadge>
          <h1 className="page__title">{status.vendor_name}</h1>
          <p className="page__subtitle">
            {status.vendor_domain || report?.vendor.domain || "Vendor domain pending"} |{" "}
            {formatCurrency(status.contract_value)}
          </p>
        </div>
        <div className="page__header-actions">
          <button
            className="button"
            onClick={() => navigate(`/vendors/${vendorId}/report?print=1`)}
            type="button"
          >
            Export PDF
          </button>
          <button className="button button--primary" onClick={refetchAll} type="button">
            Re-Evaluate
          </button>
        </div>
      </section>

      <section className="detail-grid">
        <div className="detail-grid__column">
          <div className="card risk-velocity" id="risk">
            <div className="card__header">
              <div>
                <p className="page__kicker">Current Risk</p>
                <h2 className="section-title">Risk Velocity</h2>
              </div>
              <StatusBadge tone={toneForRisk(riskLevel)}>{riskLevel}</StatusBadge>
            </div>
            <div className="risk-velocity__score">{Math.round(overallRiskScore)}</div>
            <p className="panel-muted">Current stage: {currentStage.toUpperCase()}</p>
            <div className="progress-bar">
              <div className="progress-bar__fill" style={{ width: `${Math.max(overallRiskScore, 8)}%` }} />
            </div>
          </div>

          <div className="card" id="review">
            <div className="card__header">
              <div>
                <p className="page__kicker">Review Signals</p>
                <h2 className="section-title">Core Findings</h2>
              </div>
              <StatusBadge tone={toneForStatus(status.status)}>{status.status || "processing"}</StatusBadge>
            </div>
            <div className="stack">
              {findings.slice(0, 5).map((finding, index) => (
                <div className="item-row item-row--warning" key={`${finding}-${index}`}>
                  <div className="item-row__title">Flag {index + 1}</div>
                  <div>{finding}</div>
                </div>
              ))}
              {!findings.length ? (
                <div className="item-row">
                  <div className="item-row__title">No material flags</div>
                  <div>Review details will appear here as the agents complete their work.</div>
                </div>
              ) : null}
            </div>
          </div>

          {status.has_errors ? (
            <StateView
              detail="One or more agent errors were surfaced by the workflow. Use Trace for the live sequence and Audit for the persisted trail."
              title="Workflow Errors Detected"
              tone="danger"
            />
          ) : null}
        </div>

        <div className="detail-grid__column" id="evidence">
          <div className="card">
            <div className="card__header">
              <div>
                <p className="page__kicker">Missing Inputs</p>
                <h2 className="section-title">Evidence Gaps</h2>
              </div>
              <StatusBadge tone="warning">
                {formatPercent(evidenceQuery.data?.completion_percentage)}
              </StatusBadge>
            </div>
            <div className="stack">
              {filteredEvidence.map((request) => (
                <div
                  className={request.status === "pending" ? "item-row item-row--warning" : "item-row"}
                  key={request.id}
                >
                  <div className="item-row__title">{request.document_type}</div>
                  <div>{request.reason || "Evidence requested by the workflow."}</div>
                  <div className="item-row__meta">
                    {request.status || "pending"} | {formatDateTime(request.deadline)}
                  </div>
                </div>
              ))}
              {!filteredEvidence.length ? (
                <div className="item-row">
                  <div className="item-row__title">No evidence gaps</div>
                  <div>All required evidence is currently accounted for.</div>
                </div>
              ) : null}
            </div>
            <div className="button-row">
              <button
                className="button button--blue"
                disabled={requestEvidenceMutation.isPending}
                onClick={() => requestEvidenceMutation.mutate()}
                type="button"
              >
                {requestEvidenceMutation.isPending ? "Requesting..." : "Request Evidence"}
              </button>
              <Link className="button" to={`/audit/${vendorId}`}>
                Open Approval Workspace
              </Link>
            </div>
          </div>

          <div className="card" id="documents">
            <div className="card__header">
              <div>
                <p className="page__kicker">Document Intake</p>
                <h2 className="section-title">Uploaded Documents</h2>
              </div>
              <StatusBadge tone="info">{`${filteredDocuments.length} Visible`}</StatusBadge>
            </div>
            <div className="stack">
              {filteredDocuments.map((document) => (
                <div className="doc-row" key={document.id}>
                  <div className="item-row__title">{document.file_name || "Unnamed file"}</div>
                  <div>{document.classification || "Unclassified"}</div>
                  <div className="item-row__meta">
                    {document.processing_status || "queued"} | {formatDateTime(document.created_at)}
                  </div>
                </div>
              ))}
              {!filteredDocuments.length ? (
                <div className="item-row">
                  <div className="item-row__title">No documents found</div>
                  <div>This vendor does not have any processed files yet.</div>
                </div>
              ) : null}
            </div>
            <div className="stack stack--tight">
              <label className="field">
                <span>Add more files</span>
                <input
                  multiple
                  onChange={(event) => setPendingFiles(Array.from(event.target.files || []))}
                  type="file"
                />
              </label>
              {pendingFiles.length ? (
                <div className="file-list">
                  {pendingFiles.map((file) => (
                    <span className="file-pill" key={`${file.name}-${file.size}`}>
                      {file.name}
                    </span>
                  ))}
                </div>
              ) : null}
              <button
                className="button"
                disabled={!pendingFiles.length || uploadDocumentsMutation.isPending}
                onClick={() => uploadDocumentsMutation.mutate()}
                type="button"
              >
                {uploadDocumentsMutation.isPending ? "Uploading..." : "Upload Documents"}
              </button>
            </div>
          </div>
        </div>

        <div className="detail-grid__column" id="approval">
          <div className="card">
            <div className="card__header">
              <div>
                <p className="page__kicker">Workflow Snapshot</p>
                <h2 className="section-title">Control State</h2>
              </div>
            </div>
            <div className="stack">
              <div className="data-row">
                <div className="data-row__title">Current Phase</div>
                <div>{status.current_phase || status.status || "Queued"}</div>
              </div>
              <div className="data-row">
                <div className="data-row__title">Current Agent</div>
                <div>{status.current_agent || "Awaiting assignment"}</div>
              </div>
              <div className="data-row">
                <div className="data-row__title">Progress</div>
                <div>{formatPercent(status.progress_percentage)}</div>
              </div>
              <div className="data-row">
                <div className="data-row__title">Approval</div>
                <div>{approvalStatus?.status || status.approval_status || "No approval"}</div>
              </div>
              <div className="data-row">
                <div className="data-row__title">Live Stream</div>
                <div>{eventMode === "polling" ? "Polling Fallback" : "Streaming"}</div>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card__header">
              <div>
                <p className="page__kicker">Agent Scores</p>
                <h2 className="section-title">Review Grades</h2>
              </div>
            </div>
            <div className="stack">
              <div className="data-row">
                <div className="data-row__title">Security</div>
                <div>
                  {String(securityReview.grade || "Pending")} | {String(securityReview.overall_score || "-")}
                </div>
              </div>
              <div className="data-row">
                <div className="data-row__title">Compliance</div>
                <div>
                  {String(complianceReview.grade || "Pending")} | {String(complianceReview.overall_score || "-")}
                </div>
              </div>
              <div className="data-row">
                <div className="data-row__title">Financial</div>
                <div>
                  {String(financialReview.grade || "Pending")} | {String(financialReview.overall_score || "-")}
                </div>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card__header">
              <div>
                <p className="page__kicker">Evidence Tracking</p>
                <h2 className="section-title">Recent Workflow Notes</h2>
              </div>
            </div>
            <div className="stack">
              {(evidenceStatusQuery.data?.recent_tracking || []).slice(0, 4).map((entry, index) => (
                <div className="timeline-item" key={`${entry.action}-${index}`}>
                  <span className="timeline-item__title">{entry.action || "Tracking"}</span>
                  <span>{entry.details || "Workflow tracking entry"}</span>
                  <span className="timeline-item__meta">{formatDateTime(entry.created_at)}</span>
                </div>
              ))}
              {(report?.audit_trail || []).slice(0, 3).map((entry, index) => (
                <div className="timeline-item" key={`${entry.action}-${index}`}>
                  <span className="timeline-item__title">{entry.action || entry.agent || "Audit Event"}</span>
                  <span>{entry.agent || "system"} | {entry.status || "recorded"}</span>
                  <span className="timeline-item__meta">{formatDateTime(entry.timestamp)}</span>
                </div>
              ))}
              {liveEvents.slice(-3).map((event, index) => (
                <div className="timeline-item" key={`${event.event_type}-${index}`}>
                  <span className="timeline-item__title">{event.event_type}</span>
                  <span>{JSON.stringify(event.data)}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
