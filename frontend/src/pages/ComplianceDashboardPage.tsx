import { useMutation, useQuery } from "@tanstack/react-query";
import { useDeferredValue, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useShell } from "../app/ShellContext";
import { StateView } from "../components/StateView";
import { StatusBadge } from "../components/StatusBadge";
import {
  getEphiAccessLog,
  getVendorApprovalPacket,
  listVendors,
  queryComplianceRag,
} from "../lib/api";
import { formatDateTime, normalizeText } from "../lib/utils";

function downloadCsv(rows: Array<Record<string, unknown>>, fileName: string) {
  const headers = ["timestamp", "actor_email", "actor_role", "action"];
  const lines = [
    headers.join(","),
    ...rows.map((row) =>
      headers.map((header) => JSON.stringify(String(row[header] || ""))).join(","),
    ),
  ];
  const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = fileName;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function ComplianceDashboardPage() {
  const { approvalToken, searchValue } = useShell();
  const deferredSearch = useDeferredValue(normalizeText(searchValue));
  const [selectedVendorId, setSelectedVendorId] = useState("");
  const [query, setQuery] = useState("");

  const vendorsQuery = useQuery({
    queryKey: ["vendors", "compliance"],
    queryFn: () => listVendors(),
  });

  const healthcareVendors = useMemo(() => {
    return (vendorsQuery.data?.vendors || [])
      .filter((vendor) => vendor.workflow_type === "healthcare")
      .filter((vendor) => {
        const haystack = normalizeText(`${vendor.name} ${vendor.status || ""} ${vendor.risk_level || ""}`);
        return deferredSearch ? haystack.includes(deferredSearch) : true;
      });
  }, [deferredSearch, vendorsQuery.data?.vendors]);

  const activeVendorId = selectedVendorId || healthcareVendors[0]?.id || "";

  const packetQuery = useQuery({
    queryKey: ["vendor", activeVendorId, "compliance-packet"],
    queryFn: () => getVendorApprovalPacket(activeVendorId),
    enabled: Boolean(activeVendorId),
  });

  const ephiLogQuery = useQuery({
    queryKey: ["vendor", activeVendorId, "ephi-log"],
    queryFn: () => getEphiAccessLog(activeVendorId, approvalToken),
    enabled: Boolean(activeVendorId && approvalToken),
  });

  const ragMutation = useMutation({
    mutationFn: () => queryComplianceRag({ query, vendor_id: activeVendorId }, approvalToken),
  });

  if (vendorsQuery.isLoading) {
    return (
      <div className="page">
        <StateView detail="Loading healthcare vendor pipeline." title="Compliance Dashboard Loading" />
      </div>
    );
  }

  const baaClauses = packetQuery.data?.risk_assessment?.baa_clauses || {};
  const baaMissing = packetQuery.data?.risk_assessment?.baa_clauses_missing || [];
  const healthcareChecks = packetQuery.data?.verification_results?.hipaa || [];
  const ephiFlow = healthcareChecks.find((item) => item.kind === "ephi_flow");
  const ephiDetails = (ephiFlow?.details || {}) as Record<string, unknown>;
  const highRiskCount = healthcareVendors.filter((vendor) =>
    normalizeText(vendor.risk_level || "").includes("high"),
  ).length;
  const pendingApprovalCount = healthcareVendors.filter((vendor) =>
    normalizeText(vendor.approval_status || "").includes("pending"),
  ).length;
  const ephiEntries = ephiLogQuery.data?.entries || [];

  return (
    <div className="page">
      <section className="page__header">
        <div>
          <h1 className="page__title page__title--compact">Compliance Officer Dashboard</h1>
          <p className="page__subtitle">
            Unified HIPAA findings, BAA clause status, ePHI audit trail, and compliance search for healthcare vendors.
          </p>
        </div>
        <div className="metrics-grid">
          <div className="metric-card">
            <span className="metric-card__label">Healthcare Vendors</span>
            <span className="metric-card__value">{healthcareVendors.length}</span>
          </div>
          <div className="metric-card">
            <span className="metric-card__label">High Risk</span>
            <span className="metric-card__value">{highRiskCount}</span>
          </div>
          <div className="metric-card metric-card--accent">
            <span className="metric-card__label">Pending Approval</span>
            <span className="metric-card__value">{pendingApprovalCount}</span>
          </div>
          <div className="metric-card">
            <span className="metric-card__label">Token Mode</span>
            <span className="metric-card__value">{approvalToken ? "FULL" : "LIMITED"}</span>
          </div>
        </div>
      </section>

      <section className="page-grid">
        <div className="queue-panel">
          <div className="queue-panel__header">
            <div>
              <p className="page__kicker">Healthcare Queue</p>
              <h2 className="section-title">Vendors</h2>
            </div>
          </div>
            <div className="stack">
              {healthcareVendors.map((vendor) => (
                <button
                  className={vendor.id === activeVendorId ? "approval-item approval-item--active" : "approval-item"}
                  key={vendor.id}
                  onClick={() => setSelectedVendorId(vendor.id)}
                  type="button"
                >
                <span className="approval-item__title">{vendor.name}</span>
                <span>{vendor.status || "processing"} | {vendor.risk_level || "pending"}</span>
                <span className="approval-item__meta">{vendor.approval_status || vendor.workflow_type}</span>
              </button>
            ))}
          </div>
        </div>

        {!activeVendorId ? (
          <StateView detail="Select a healthcare vendor to inspect HIPAA findings." title="No Vendor Selected" />
        ) : (
            <div className="detail-grid__column">
              <div className="card">
                <div className="card__header">
                  <div>
                    <p className="page__kicker">BAA Clauses</p>
                  <h2 className="section-title">{packetQuery.data?.vendor?.name || activeVendorId}</h2>
                </div>
                <StatusBadge tone={baaMissing.length ? "warning" : "info"}>
                  {baaMissing.length ? "Needs Review" : "Complete"}
                </StatusBadge>
              </div>
              <div className="stack">
                {Object.entries(baaClauses).map(([clause, value]) => (
                  <div className={`item-row ${value.present ? "" : "item-row--warning"}`} key={clause}>
                    <div className="item-row__title">{clause.replace(/_/g, " ")}</div>
                    <div>{value.present ? "Present" : "Missing"}</div>
                  </div>
                ))}
                {!Object.keys(baaClauses).length ? (
                  <div className="item-row">
                    <div className="item-row__title">No BAA analysis yet</div>
                    <div>The BAA parser has not produced a clause breakdown for this vendor yet.</div>
                  </div>
                ) : null}
                </div>
              </div>

              <div className="split-grid">
                <div className="card">
                  <div className="card__header">
                    <div>
                      <p className="page__kicker">Oversight</p>
                      <h2 className="section-title">Compliance Schedule</h2>
                    </div>
                  </div>
                  <div className="signal-grid">
                    <div className="signal-card">
                      <span className="signal-card__label">BAA Expiry</span>
                      <strong>{formatDateTime(packetQuery.data?.risk_assessment?.baa_expiry_date)}</strong>
                    </div>
                    <div className="signal-card">
                      <span className="signal-card__label">Missing Clauses</span>
                      <strong>{baaMissing.length}</strong>
                    </div>
                    <div className="signal-card">
                      <span className="signal-card__label">ePHI Result</span>
                      <strong>{ephiFlow?.result || "Pending"}</strong>
                    </div>
                    <div className="signal-card">
                      <span className="signal-card__label">Current Risk</span>
                      <strong>{packetQuery.data?.risk_assessment?.risk_level || "Pending"}</strong>
                    </div>
                  </div>
                  <div className="button-row">
                    <Link className="button" to={`/audit/${activeVendorId}`}>
                      Open Approval Workspace
                    </Link>
                  </div>
                </div>

                <div className="card">
                  <div className="card__header">
                    <div>
                      <p className="page__kicker">ePHI Flow</p>
                      <h2 className="section-title">Risk Map</h2>
                    </div>
                    <StatusBadge tone={ephiFlow?.result === "compliant" ? "info" : "warning"}>
                      {ephiFlow?.result || "Pending"}
                    </StatusBadge>
                  </div>
                  <div className="risk-map">
                    <div className="risk-map__row">
                      <span>Encryption Verified</span>
                      <strong>{ephiDetails.encryption_verified ? "Yes" : "No"}</strong>
                    </div>
                    <div className="risk-map__row">
                      <span>Jurisdiction Verified</span>
                      <strong>{ephiDetails.jurisdiction_verified ? "Yes" : "No"}</strong>
                    </div>
                    <div className="risk-map__row">
                      <span>Risk Signals</span>
                      <strong>{Array.isArray(ephiDetails.risks) ? ephiDetails.risks.length : 0}</strong>
                    </div>
                  </div>
                </div>
              </div>

              <div className="split-grid">
                <div className="card">
                  <div className="card__header">
                    <div>
                      <p className="page__kicker">ePHI Access</p>
                      <h2 className="section-title">Append-Only Log</h2>
                    </div>
                    <button
                      className="button"
                      disabled={!approvalToken || !ephiEntries.length}
                      onClick={() => downloadCsv(ephiEntries as Array<Record<string, unknown>>, `${activeVendorId}-ephi-log.csv`)}
                      type="button"
                    >
                      Export CSV
                    </button>
                  </div>
                  <div className="stack">
                    {!approvalToken ? (
                      <div className="item-row">
                        <div className="item-row__title">Protected Surface</div>
                        <div>Add a compliance or admin token to unlock the ePHI access log and export.</div>
                      </div>
                    ) : null}
                    {(ephiLogQuery.data?.entries || []).map((entry) => (
                      <div className="timeline-item" key={entry.id}>
                        <span className="timeline-item__title">{entry.action}</span>
                        <span>{entry.actor_email} | {entry.actor_role}</span>
                        <span className="timeline-item__meta">{formatDateTime(entry.created_at)}</span>
                    </div>
                  ))}
                  {!ephiLogQuery.data?.entries?.length ? (
                    <div className="item-row">
                      <div className="item-row__title">No access events yet</div>
                      <div>Healthcare approval events will appear here once compliance decisions are recorded.</div>
                    </div>
                  ) : null}
                </div>
              </div>

                <div className="card">
                  <div className="card__header">
                    <div>
                      <p className="page__kicker">RAG Query</p>
                      <h2 className="section-title">Compliance Search</h2>
                    </div>
                  </div>
                  <div className="stack">
                    <label className="field">
                      <span>Ask a compliance question</span>
                      <textarea onChange={(event) => setQuery(event.target.value)} rows={4} value={query} />
                    </label>
                    <button
                      className="button button--blue"
                      disabled={!approvalToken || !query.trim() || ragMutation.isPending}
                      onClick={() => ragMutation.mutate()}
                      type="button"
                    >
                      {ragMutation.isPending ? "Searching..." : "Run Query"}
                    </button>
                    {!approvalToken ? (
                      <p className="panel-muted">
                        A compliance or admin token is required to run protected compliance search queries.
                      </p>
                    ) : null}
                    {ragMutation.data ? (
                      <div className="stack">
                        <p>{ragMutation.data.answer}</p>
                      {(ragMutation.data.sources || []).map((source, index) => (
                        <div className="item-row" key={index}>
                          <div className="item-row__title">{String(source.type || "source")}</div>
                          <div>{JSON.stringify(source)}</div>
                        </div>
                      ))}
                    </div>
                  ) : null}
                </div>
              </div>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
