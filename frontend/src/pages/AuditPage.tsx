import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useDeferredValue, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useShell } from "../app/ShellContext";
import { StateView } from "../components/StateView";
import { StatusBadge } from "../components/StatusBadge";
import {
  getVendorApprovalDecisions,
  getVendorApprovalPacket,
  getVendorApprovalStatus,
  getVendorApprovalWorkflow,
  getVendorAuditTrail,
  listVendors,
  submitApprovalDecision,
} from "../lib/api";
import { toneForRisk, toneForStatus } from "../lib/status";
import type { ApprovalPacket } from "../lib/types";
import { formatDateTime, formatPercent, normalizeText } from "../lib/utils";

type DecisionType = "approve" | "reject" | "request_changes";
type Check = NonNullable<NonNullable<ApprovalPacket["verification_results"]>["standard"]>[number];

const DECISION_COPY: Record<DecisionType, { label: string; desc: string }> = {
  approve: { label: "Approve", desc: "Advance to the next step or final approval." },
  reject: { label: "Reject", desc: "Stop the workflow and mark the vendor rejected." },
  request_changes: { label: "Request Changes", desc: "Pause the workflow and send remediation back." },
};

function asStrings(value: unknown) {
  return Array.isArray(value) ? value.map((item) => String(item)) : [];
}

function asRecords(value: unknown) {
  return Array.isArray(value) ? (value as Array<Record<string, unknown>>) : [];
}

function asRecord(value: unknown) {
  return value && typeof value === "object" ? (value as Record<string, unknown>) : {};
}

function uniq(values: string[]) {
  return [...new Set(values.filter(Boolean))];
}

function label(value?: string | null) {
  return (value || "").replace(/_/g, " ").replace(/\b\w/g, (m) => m.toUpperCase()) || "Pending";
}

function decisionTone(value?: string | null) {
  const normalized = (value || "").toLowerCase();
  if (normalized.includes("reject") || normalized.includes("fail") || normalized.includes("non")) return "danger";
  if (normalized.includes("request") || normalized.includes("pending") || normalized.includes("current")) return "warning";
  if (normalized.includes("approve") || normalized.includes("clear") || normalized.includes("valid")) return "info";
  return "muted";
}

function checkTone(item?: Check) {
  return decisionTone(item?.result || item?.status);
}

function percent(value?: number | null, scale = 1) {
  if (value == null || Number.isNaN(value)) return "Pending";
  return `${Math.round(value * scale)}%`;
}

function countdown(value?: string | null) {
  if (!value) return "Deadline pending";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  const diff = date.getTime() - Date.now();
  const totalHours = Math.floor(Math.abs(diff) / 36e5);
  const days = Math.floor(totalHours / 24);
  const hours = totalHours % 24;
  return diff < 0 ? `Past due by ${days}d ${hours}h` : `${days}d ${hours}h remaining`;
}

function detailLines(details?: Record<string, unknown>) {
  return Object.entries(details || {})
    .flatMap(([key, raw]) => {
      if (raw == null || raw === "") return [];
      if (Array.isArray(raw)) return raw.length ? `${label(key)}: ${raw.slice(0, 2).map(String).join(", ")}` : [];
      if (typeof raw === "boolean") return `${label(key)}: ${raw ? "Yes" : "No"}`;
      if (typeof raw === "object") return [];
      return `${label(key)}: ${String(raw)}`;
    })
    .slice(0, 3);
}

export function AuditPage() {
  const { vendorId } = useParams();
  const queryClient = useQueryClient();
  const { searchValue, approvalToken } = useShell();
  const deferredSearch = useDeferredValue(normalizeText(searchValue));
  const [selectedDecision, setSelectedDecision] = useState<DecisionType>("approve");
  const [comments, setComments] = useState("");
  const [pickedConditions, setPickedConditions] = useState<string[]>([]);
  const [extraConditions, setExtraConditions] = useState("");
  const [permissionLevel, setPermissionLevel] = useState<"read-only" | "read-write" | "admin">("read-only");

  useEffect(() => {
    setSelectedDecision("approve");
    setComments("");
    setPickedConditions([]);
    setExtraConditions("");
    setPermissionLevel("read-only");
  }, [vendorId]);

  const vendorsQuery = useQuery({ queryKey: ["vendors", "audit-queue"], queryFn: () => listVendors() });
  const packetQuery = useQuery({
    queryKey: ["vendor", vendorId, "approval-packet"],
    queryFn: () => getVendorApprovalPacket(vendorId || ""),
    enabled: Boolean(vendorId),
  });
  const workflowQuery = useQuery({
    queryKey: ["vendor", vendorId, "approval-workflow"],
    queryFn: () => getVendorApprovalWorkflow(vendorId || ""),
    enabled: Boolean(vendorId),
  });
  const decisionsQuery = useQuery({
    queryKey: ["vendor", vendorId, "approvals"],
    queryFn: () => getVendorApprovalDecisions(vendorId || ""),
    enabled: Boolean(vendorId),
  });
  const statusQuery = useQuery({
    queryKey: ["vendor", vendorId, "approval-status"],
    queryFn: () => getVendorApprovalStatus(vendorId || ""),
    enabled: Boolean(vendorId),
  });
  const auditQuery = useQuery({
    queryKey: ["vendor", vendorId, "audit-trail"],
    queryFn: () => getVendorAuditTrail(vendorId || ""),
    enabled: Boolean(vendorId),
  });

  const submitMutation = useMutation({
    mutationFn: () =>
      submitApprovalDecision(
        vendorId || "",
        approvalToken,
        (packetQuery.data?.approval_workflow?.current_step_role || workflowQuery.data?.required_approvers?.[0]?.role || "legal") as "legal" | "finance" | "it" | "compliance_officer",
        {
          decision: selectedDecision,
          comments,
          conditions: uniq([
            ...pickedConditions,
            ...extraConditions.split(/\n|,/).map((item) => item.trim()),
          ]),
          permission_level: permissionLevel,
        },
      ),
    onSuccess: async () => {
      setComments("");
      setPickedConditions([]);
      setExtraConditions("");
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["vendor", vendorId, "approvals"] }),
        queryClient.invalidateQueries({ queryKey: ["vendor", vendorId, "approval-status"] }),
        queryClient.invalidateQueries({ queryKey: ["vendor", vendorId, "approval-workflow"] }),
        queryClient.invalidateQueries({ queryKey: ["vendor", vendorId, "approval-packet"] }),
        queryClient.invalidateQueries({ queryKey: ["vendor", vendorId, "audit-trail"] }),
        queryClient.invalidateQueries({ queryKey: ["vendors", "audit-queue"] }),
      ]);
    },
  });

  const queue = useMemo(() => {
    const vendors = vendorsQuery.data?.vendors || [];
    return vendors
      .filter((vendor) => Boolean(vendor.approval_status) || normalizeText(vendor.status || "").includes("approval"))
      .filter((vendor) => {
        const haystack = normalizeText(`${vendor.name} ${vendor.status || ""} ${vendor.approval_status || ""} ${vendor.risk_level || ""}`);
        return deferredSearch ? haystack.includes(deferredSearch) : true;
      });
  }, [deferredSearch, vendorsQuery.data?.vendors]);

  if (vendorsQuery.isLoading) {
    return <div className="page"><StateView detail="Loading approval queue." title="Audit Workspace Loading" /></div>;
  }

  if (vendorsQuery.isError) {
    return (
      <div className="page">
        <StateView detail="The approval workspace is unavailable because the queue failed to load." title="Audit Workspace Unavailable" tone="danger" />
      </div>
    );
  }

  const packet = packetQuery.data;
  const risk = packet?.risk_assessment || null;
  const workflowType = String(packet?.vendor?.workflow_type || "");
  const currentRole = String(packet?.approval_workflow?.current_step_role || workflowQuery.data?.required_approvers?.[0]?.role || "legal");
  const standardChecks = packet?.verification_results?.standard || [];
  const hipaaChecks = packet?.verification_results?.hipaa || [];
  const decisions = decisionsQuery.data?.decisions || [];
  const blockers = [...asStrings(risk?.critical_blockers), ...asStrings(risk?.conditional_items)];
  const baaClauses = (risk?.baa_clauses || {}) as Record<string, { present?: boolean }>;
  const baaMissing = asStrings(risk?.baa_clauses_missing);
  const ephiFlow = hipaaChecks.find((item) => item.kind === "ephi_flow");
  const ephiDetails = asRecord(ephiFlow?.details);
  const ephiRisks = asStrings(ephiDetails.risks);
  const oigCheck = hipaaChecks.find((item) => item.kind === "oig");
  const suggestionPool = uniq([
    ...blockers,
    ...(risk?.mitigation_recommendations || []).map((item) => item.description || item.implementation || ""),
    ...baaMissing.map((item) => `Add BAA clause: ${label(item)}`),
    ...ephiRisks,
  ]).slice(0, 6);
  const steps = (workflowQuery.data?.required_approvers || packet?.approval_workflow?.approvers || []).map((step) => {
    const role = String(step.role || "");
    const decision = decisions.find((item) => item.approver_role === role);
    return { role, name: String(step.label || label(role)), status: decision?.decision || (currentRole === role ? "current" : "pending"), decidedAt: decision?.decided_at };
  });
  const auditEntries = [...asRecords(auditQuery.data?.audit_trail), ...asRecords(auditQuery.data?.trail), ...asRecords(auditQuery.data?.timeline)];

  return (
    <div className="page">
      <section className="page__header">
        <div>
          <h1 className="page__title page__title--compact">Approval Dashboard</h1>
          <p className="page__subtitle">Model scores, verification confidence, workflow steps, and final decision controls for the approval stage.</p>
        </div>
        <div className="metrics-grid">
          <div className="metric-card"><span className="metric-card__label">Queue Size</span><span className="metric-card__value">{queue.length}</span></div>
          <div className="metric-card"><span className="metric-card__label">Pending Approvers</span><span className="metric-card__value">{statusQuery.data?.pending_approvers?.length || 0}</span></div>
          <div className="metric-card metric-card--accent"><span className="metric-card__label">Completion</span><span className="metric-card__value">{formatPercent(statusQuery.data?.completion_percentage)}</span></div>
          <div className="metric-card"><span className="metric-card__label">Token Mode</span><span className="metric-card__value">{approvalToken ? "WRITE" : "READ"}</span></div>
        </div>
      </section>

      <section className="page-grid">
        <div className="queue-panel">
          <div className="queue-panel__header"><div><p className="page__kicker">Approval Queue</p><h2 className="section-title">Assessments</h2></div></div>
          <div className="stack">
            {queue.map((vendor) => (
              <Link className={vendor.id === vendorId ? "approval-item approval-item--active" : "approval-item"} key={vendor.id} to={`/audit/${vendor.id}`}>
                <span className="approval-item__title">{vendor.name}</span>
                <span>{vendor.status || "processing"} | {vendor.approval_status || "no approval"}</span>
                <span className="approval-item__meta">{vendor.risk_level || "risk pending"} | {formatDateTime(vendor.updated_at)}</span>
              </Link>
            ))}
          </div>
        </div>

        {!vendorId ? (
          <StateView detail="Select a vendor from the queue to open the approval packet." title="Select an Assessment" />
        ) : packetQuery.isLoading || workflowQuery.isLoading ? (
          <StateView detail="Loading approval packet and workflow state." title="Approval Packet Loading" />
        ) : !packet ? (
          <StateView detail="The approval packet is not available for this vendor yet." title="Approval Packet Pending" />
        ) : (
          <div className="detail-grid__column">
            <div className="split-grid">
              <div className="card">
                <div className="card__header">
                  <div><p className="page__kicker">Model Consensus</p><h2 className="section-title">{String(packet.vendor?.name || "Approval Packet")}</h2></div>
                  <StatusBadge tone={decisionTone(risk?.confidence_indicator)}>{risk?.models_agree ? "Models Agree" : "Needs Review"}</StatusBadge>
                </div>
                <div className="approval-gauge">
                  <div className="approval-gauge__ring" style={{ background: `conic-gradient(var(--blue) ${Math.round((risk?.probability_legitimate || 0) * 100)}%, var(--surface-muted) 0)` }}>
                    <div className="approval-gauge__inner"><span className="approval-gauge__value">{percent(risk?.probability_legitimate, 100)}</span><span className="approval-gauge__label">Legitimate Probability</span></div>
                  </div>
                  <div className="stack stack--tight">
                    <div className="data-row"><div className="data-row__title">Bayesian</div><div>{risk?.bayesian_tier || "Pending"}</div></div>
                    <div className="data-row"><div className="data-row__title">RL</div><div>{risk?.rl_tier || "Pending"}</div></div>
                    <div className="data-row"><div className="data-row__title">Confidence Band</div><div>{risk?.confidence_interval ? `${percent(risk.confidence_interval.low, 100)} - ${percent(risk.confidence_interval.high, 100)}` : "Pending"}</div></div>
                    <div className="data-row"><div className="data-row__title">Overall Risk</div><div>{String(risk?.overall_risk_score ?? "-")}</div></div>
                  </div>
                </div>
                <p className="panel-muted">{String(risk?.executive_summary || packet.recommendation || "Approval packet generated from persisted review output.")}</p>
                {risk?.hard_override ? <div className="item-row item-row--warning"><div className="item-row__title">Hard Override</div><div>{risk.hard_override}</div></div> : null}
              </div>

              <div className="card">
                <div className="card__header">
                  <div><p className="page__kicker">Workflow Control</p><h2 className="section-title">Sequence and Deadline</h2></div>
                  <StatusBadge tone={toneForStatus(statusQuery.data?.status)}>{statusQuery.data?.status || workflowQuery.data?.status || "pending"}</StatusBadge>
                </div>
                <div className="signal-grid">
                  <div className="signal-card"><span className="signal-card__label">Current Step</span><strong>{label(currentRole)}</strong></div>
                  <div className="signal-card"><span className="signal-card__label">Deadline</span><strong>{countdown(packet.approval_workflow?.deadline || workflowQuery.data?.deadline)}</strong></div>
                  <div className="signal-card"><span className="signal-card__label">Tier</span><strong>{risk?.approval_tier || workflowQuery.data?.approval_tier || "Pending"}</strong></div>
                  <div className="signal-card"><span className="signal-card__label">Workflow</span><strong>{packet.approval_workflow?.name || workflowQuery.data?.workflow?.name || "Sequential Review"}</strong></div>
                </div>
                <div className="workflow-strip">
                  {steps.map((step) => (
                    <div className="workflow-step" key={step.role}>
                      <StatusBadge tone={decisionTone(step.status)}>{label(step.status)}</StatusBadge>
                      <strong>{step.name}</strong>
                      <span className="workflow-step__meta">{step.decidedAt ? formatDateTime(step.decidedAt) : "Awaiting action"}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="split-grid">
              <div className="card">
                <div className="card__header"><div><p className="page__kicker">Verification Matrix</p><h2 className="section-title">Confidence Scores</h2></div></div>
                <div className="verification-grid">
                  {standardChecks.map((item) => (
                    <div className="verification-card" key={item.id}>
                      <div className="card__header"><div><p className="page__kicker">Verification</p><h3 className="section-title">{item.label || label(item.kind)}</h3></div><StatusBadge tone={checkTone(item)}>{item.result || item.status || "Pending"}</StatusBadge></div>
                      <div className="confidence-bar"><div className="confidence-bar__fill" style={{ width: `${Math.round((item.confidence_score || 0) * 100)}%` }} /></div>
                      <p className="panel-muted">Confidence {percent(item.confidence_score, 100)} | {item.agent_name || "Agent"}</p>
                      {detailLines(item.details).map((line) => <div className="item-row" key={line}><div>{line}</div></div>)}
                    </div>
                  ))}
                </div>
              </div>

              <div className="card">
                <div className="card__header"><div><p className="page__kicker">Decision Context</p><h2 className="section-title">Holds and Guidance</h2></div><StatusBadge tone={toneForRisk(String(risk?.risk_level || ""))}>{String(risk?.risk_level || "Pending")}</StatusBadge></div>
                <div className="stack">
                  {blockers.map((item, index) => <div className="item-row item-row--warning" key={`${item}-${index}`}><div className="item-row__title">Blocker {index + 1}</div><div>{item}</div></div>)}
                  {!blockers.length ? <div className="item-row"><div className="item-row__title">No blockers</div><div>No unresolved blockers are present in the current packet.</div></div> : null}
                  {(risk?.evidence_explanation || []).map((item) => <div className="item-row" key={item}><div>{item}</div></div>)}
                </div>
              </div>
            </div>

            {workflowType === "healthcare" ? (
              <div className="split-grid">
                <div className="card">
                  <div className="card__header"><div><p className="page__kicker">HIPAA Findings</p><h2 className="section-title">Healthcare Controls</h2></div><StatusBadge tone={baaMissing.length ? "warning" : "info"}>{baaMissing.length ? "Review BAA" : "BAA Complete"}</StatusBadge></div>
                  <div className="signal-grid">
                    <div className="signal-card"><span className="signal-card__label">OIG Result</span><strong>{oigCheck?.result || "Pending"}</strong></div>
                    <div className="signal-card"><span className="signal-card__label">BAA Expiry</span><strong>{formatDateTime(risk?.baa_expiry_date)}</strong></div>
                    <div className="signal-card"><span className="signal-card__label">HIPAA Factors</span><strong>{asStrings(risk?.hipaa_risk_factors).length || 0}</strong></div>
                    <div className="signal-card"><span className="signal-card__label">Overrides</span><strong>{asStrings(risk?.hipaa_overrides).length || 0}</strong></div>
                  </div>
                  <div className="checklist">
                    {Object.entries(baaClauses).map(([clause, item]) => <div className="checklist__item" key={clause}><StatusBadge tone={item.present ? "info" : "warning"}>{item.present ? "Present" : "Missing"}</StatusBadge><span>{label(clause)}</span></div>)}
                  </div>
                </div>
                <div className="card">
                  <div className="card__header"><div><p className="page__kicker">ePHI Flow Risk Map</p><h2 className="section-title">Transport and Residency</h2></div><StatusBadge tone={checkTone(ephiFlow)}>{ephiFlow?.result || "Pending"}</StatusBadge></div>
                  <div className="risk-map">
                    <div className="risk-map__row"><span>Encryption Verified</span><strong>{ephiDetails.encryption_verified ? "Yes" : "No"}</strong></div>
                    <div className="risk-map__row"><span>Jurisdiction Verified</span><strong>{ephiDetails.jurisdiction_verified ? "Yes" : "No"}</strong></div>
                    <div className="risk-map__row"><span>Risk Signals</span><strong>{ephiRisks.length || 0}</strong></div>
                  </div>
                  <div className="stack">
                    {ephiRisks.map((item) => <div className="item-row item-row--warning" key={item}><div>{item}</div></div>)}
                    {!ephiRisks.length ? <div className="item-row"><div className="item-row__title">No flow risks</div><div>The healthcare flow analysis did not report active transport issues.</div></div> : null}
                  </div>
                </div>
              </div>
            ) : null}

            <div className="card">
              <div className="card__header"><div><p className="page__kicker">Decision Input</p><h2 className="section-title">Approver Action</h2></div><StatusBadge tone={approvalToken ? "info" : "warning"}>{approvalToken ? "Writable" : "Read Only"}</StatusBadge></div>
              <div className="choice-grid">
                {(Object.keys(DECISION_COPY) as DecisionType[]).map((option) => (
                  <label className={selectedDecision === option ? "choice-card choice-card--selected" : "choice-card"} key={option}>
                    <input checked={selectedDecision === option} name="decision" onChange={() => setSelectedDecision(option)} type="radio" value={option} />
                    <strong>{DECISION_COPY[option].label}</strong>
                    <span className="panel-muted">{DECISION_COPY[option].desc}</span>
                  </label>
                ))}
              </div>
              <div className="split-grid">
                <div className="stack">
                  <label className="field"><span>Decision Commentary</span><textarea onChange={(event) => setComments(event.target.value)} placeholder="Summarize the rationale, exceptions, or review notes." rows={5} value={comments} /></label>
                  <div className="checklist">
                    {suggestionPool.map((item) => (
                      <label className="checklist__item" key={item}>
                        <input checked={pickedConditions.includes(item)} onChange={(event) => setPickedConditions((current) => event.target.checked ? [...current, item] : current.filter((entry) => entry !== item))} type="checkbox" />
                        <span>{item}</span>
                      </label>
                    ))}
                  </div>
                </div>
                <div className="stack">
                  <label className="field"><span>Custom Conditions</span><textarea onChange={(event) => setExtraConditions(event.target.value)} placeholder="Optional. One item per line." rows={5} value={extraConditions} /></label>
                  {currentRole === "it" ? <label className="field"><span>Permission Level</span><select onChange={(event) => setPermissionLevel(event.target.value as "read-only" | "read-write" | "admin")} value={permissionLevel}><option value="read-only">Read-only</option><option value="read-write">Read-write</option><option value="admin">Admin</option></select></label> : null}
                  <div className="button-row">
                    <button className={selectedDecision === "reject" ? "button button--danger" : selectedDecision === "request_changes" ? "button" : "button button--blue"} disabled={!approvalToken || submitMutation.isPending} onClick={() => submitMutation.mutate()} type="button">{submitMutation.isPending ? "Saving..." : `${DECISION_COPY[selectedDecision].label} Vendor`}</button>
                    <Link className="button" to={`/vendors/${vendorId}`}>Vendor Workspace</Link>
                  </div>
                  <p className="panel-muted">{approvalToken ? "Bearer token present. Decisions will be submitted to the backend." : "Read-only mode. Add an approver token in Settings to enable submissions."}</p>
                  {submitMutation.data ? <div className="item-row"><div className="item-row__title">Decision Recorded</div><div>{submitMutation.data.message}</div></div> : null}
                  {submitMutation.error ? <div className="item-row item-row--warning"><div className="item-row__title">Submission Issue</div><div>{submitMutation.error.message}</div></div> : null}
                </div>
              </div>
            </div>

            <div className="split-grid">
              <div className="card">
                <div className="card__header"><div><p className="page__kicker">Decision History</p><h2 className="section-title">Approvals</h2></div></div>
                <div className="stack">
                  {decisions.map((item) => (
                    <div className="approval-item" key={item.id}>
                      <div className="card__header"><strong className="approval-item__title">{item.approver_name || "Approver"}</strong><StatusBadge tone={decisionTone(item.decision)}>{label(item.decision)}</StatusBadge></div>
                      <span>{label(item.approver_role)} | {item.comments || "No commentary provided."}</span>
                      {(item.conditions || []).length ? <span className="approval-item__meta">Conditions: {(item.conditions || []).join(", ")}</span> : null}
                      <span className="approval-item__meta">{formatDateTime(item.decided_at)}</span>
                    </div>
                  ))}
                  {!decisions.length ? <div className="item-row"><div className="item-row__title">No decisions yet</div><div>Approval actions will appear here as each role records its outcome.</div></div> : null}
                </div>
              </div>
              <div className="card">
                <div className="card__header"><div><p className="page__kicker">Audit Trail</p><h2 className="section-title">Persisted Events</h2></div></div>
                <div className="stack">
                  {auditEntries.slice(0, 8).map((item, index) => <div className="timeline-item" key={`${String(item.action || item.event_type || index)}-${index}`}><span className="timeline-item__title">{String(item.action || item.event_type || item.agent_name || "Audit Event")}</span><span>{String(item.agent_name || item.agent || "system")} | {String(item.status || "recorded")}</span><span className="timeline-item__meta">{formatDateTime(String(item.created_at || item.timestamp || ""))}</span></div>)}
                </div>
              </div>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
