import { useQuery } from "@tanstack/react-query";
import { useDeferredValue, useEffect, useMemo } from "react";
import { Link, useParams } from "react-router-dom";
import { useShell } from "../app/ShellContext";
import { StateView } from "../components/StateView";
import { StatusBadge } from "../components/StatusBadge";
import {
  getVendorAuditTrail,
  getVendorCompliance,
  getVendorFinancial,
  getVendorSecurity,
  getVendorStatus,
  listVendors,
} from "../lib/api";
import { toneForStatus } from "../lib/status";
import { formatDateTime, normalizeText } from "../lib/utils";

function reviewStatus(
  currentAgent: string | undefined,
  expectedAgent: string,
  review: Record<string, unknown>,
) {
  const status = String(review.status || "");
  if (currentAgent === expectedAgent) {
    return { label: "Active", tone: "info" as const };
  }
  if (normalizeText(status).includes("completed")) {
    return { label: "Idle", tone: "muted" as const };
  }
  if (normalizeText(status).includes("error")) {
    return { label: "Error", tone: "danger" as const };
  }
  return { label: status || "Waiting", tone: "warning" as const };
}

function asRecord(value: unknown) {
  return value && typeof value === "object" ? (value as Record<string, unknown>) : {};
}

export function TracePage() {
  const { vendorId } = useParams();
  const { searchValue, liveEvents, eventMode, setActiveVendorId } = useShell();
  const deferredSearch = useDeferredValue(normalizeText(searchValue));
  const vendorsQuery = useQuery({
    queryKey: ["vendors", "trace-selector"],
    queryFn: () => listVendors(),
  });

  useEffect(() => {
    setActiveVendorId(vendorId || "");
    return () => setActiveVendorId("");
  }, [setActiveVendorId, vendorId]);

  const statusQuery = useQuery({
    queryKey: ["vendor", vendorId, "status"],
    queryFn: () => getVendorStatus(vendorId || ""),
    enabled: Boolean(vendorId),
    refetchInterval: eventMode === "polling" ? 8_000 : false,
  });
  const auditQuery = useQuery({
    queryKey: ["vendor", vendorId, "audit-trail"],
    queryFn: () => getVendorAuditTrail(vendorId || ""),
    enabled: Boolean(vendorId),
    refetchInterval: eventMode === "polling" ? 8_000 : false,
  });
  const securityQuery = useQuery({
    queryKey: ["vendor", vendorId, "trace-security"],
    queryFn: () => getVendorSecurity(vendorId || ""),
    enabled: Boolean(vendorId),
  });
  const complianceQuery = useQuery({
    queryKey: ["vendor", vendorId, "trace-compliance"],
    queryFn: () => getVendorCompliance(vendorId || ""),
    enabled: Boolean(vendorId),
  });
  const financialQuery = useQuery({
    queryKey: ["vendor", vendorId, "trace-financial"],
    queryFn: () => getVendorFinancial(vendorId || ""),
    enabled: Boolean(vendorId),
  });

  const queue = useMemo(() => {
    return (vendorsQuery.data?.vendors || []).filter((vendor) => {
      const haystack = normalizeText(
        `${vendor.name} ${vendor.status || ""} ${vendor.risk_level || ""}`,
      );
      return deferredSearch ? haystack.includes(deferredSearch) : true;
    });
  }, [deferredSearch, vendorsQuery.data?.vendors]);

  if (vendorsQuery.isLoading) {
    return (
      <div className="page">
        <StateView detail="Loading trace selector and vendor queue." title="Trace Loading" />
      </div>
    );
  }

  if (!vendorId) {
    return (
      <div className="page">
        <section className="page__header">
          <div>
            <h1 className="page__title page__title--compact">Live Agent Trace</h1>
            <p className="page__subtitle">
              Backend events are vendor-scoped, so select a vendor to open the live trace console.
            </p>
          </div>
        </section>
        <section className="queue-panel">
          <div className="queue-panel__header">
            <div>
              <p className="page__kicker">Trace Selector</p>
              <h2 className="section-title">Available Vendors</h2>
            </div>
          </div>
          <div className="stack">
            {queue.map((vendor) => (
              <Link className="approval-item" key={vendor.id} to={`/trace/${vendor.id}`}>
                <span className="approval-item__title">{vendor.name}</span>
                <span>{vendor.status || "processing"} | {vendor.risk_level || "risk pending"}</span>
                <span className="approval-item__meta">{formatDateTime(vendor.updated_at)}</span>
              </Link>
            ))}
          </div>
        </section>
      </div>
    );
  }

  if (statusQuery.isLoading || !statusQuery.data) {
    return (
      <div className="page">
        <StateView detail="Loading vendor trace state." title="Trace Loading" />
      </div>
    );
  }

  const status = statusQuery.data;
  const securityReview = asRecord(securityQuery.data?.security_review);
  const complianceReview = asRecord(complianceQuery.data?.compliance_review);
  const financialReview = asRecord(financialQuery.data?.financial_review);
  const securityReport = asRecord(securityReview.report);
  const complianceReport = asRecord(complianceReview.report);
  const financialReport = asRecord(financialReview.report);
  const auditEntries = [
    ...(Array.isArray(auditQuery.data?.audit_trail) ? auditQuery.data?.audit_trail : []),
    ...(Array.isArray(auditQuery.data?.trail) ? auditQuery.data?.trail : []),
  ] as Array<Record<string, unknown>>;

  const securityState = reviewStatus(status.current_agent, "security_review", securityReview);
  const complianceState = reviewStatus(status.current_agent, "compliance_review", complianceReview);
  const financialState = reviewStatus(status.current_agent, "financial_review", financialReview);

  return (
    <div className="page">
      <section className="page__header">
        <div>
          <h1 className="page__title page__title--compact">Live Agent Trace</h1>
          <p className="page__subtitle">
            Vendor: {status.vendor_name} | current agent {status.current_agent || "pending"} | current step {status.current_step || "queued"}.
          </p>
        </div>
        <div className="page__header-actions">
          <StatusBadge tone={toneForStatus(status.status)}>
            {String(status.status || "processing")}
          </StatusBadge>
          <StatusBadge tone={eventMode === "polling" ? "warning" : "info"}>
            {eventMode === "polling" ? "Polling Fallback" : "Streaming"}
          </StatusBadge>
        </div>
      </section>

      <section className="page-grid">
        <div className="detail-grid__column">
          <div className="card">
            <div className="card__header">
              <div>
                <p className="page__kicker">Active Agents</p>
                <h2 className="section-title">Execution State</h2>
              </div>
            </div>
            <div className="stack">
              <div className="approval-item">
                <span className="approval-item__title">Security Agent</span>
                <span>{String(securityReport.summary || "Security review trace active.")}</span>
                <StatusBadge tone={securityState.tone}>{securityState.label}</StatusBadge>
              </div>
              <div className="approval-item">
                <span className="approval-item__title">Compliance Agent</span>
                <span>{String(complianceReport.summary || "Compliance review trace active.")}</span>
                <StatusBadge tone={complianceState.tone}>{complianceState.label}</StatusBadge>
              </div>
              <div className="approval-item">
                <span className="approval-item__title">Financial Agent</span>
                <span>{String(financialReport.summary || "Financial review trace active.")}</span>
                <StatusBadge tone={financialState.tone}>{financialState.label}</StatusBadge>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card__header">
              <div>
                <p className="page__kicker">Workflow Health</p>
                <h2 className="section-title">Status Snapshot</h2>
              </div>
            </div>
            <div className="stack">
              <div className="data-row">
                <div className="data-row__title">Current Phase</div>
                <div>{status.current_phase || status.status || "Queued"}</div>
              </div>
              <div className="data-row">
                <div className="data-row__title">Progress</div>
                <div>{status.progress_percentage || 0}%</div>
              </div>
              <div className="data-row">
                <div className="data-row__title">Risk Level</div>
                <div>{status.risk_level || "Pending"}</div>
              </div>
              <div className="data-row">
                <div className="data-row__title">Approval State</div>
                <div>{status.approval_status || "No approval"}</div>
              </div>
            </div>
          </div>
        </div>

        <div className="trace-log">
          <div className="trace-log__header">
            <div>
              <p className="page__kicker">Terminal Feed</p>
              <h2 className="section-title">Stream and Audit</h2>
            </div>
            <div className="trace-log__mode">
              {eventMode === "polling"
                ? "SSE unavailable. Polling status and audit trail."
                : "Live SSE stream connected."}
            </div>
          </div>
          <div className="trace-log__body">
            {liveEvents.map((event, index) => (
              <div className="trace-line" key={`${event.event_type}-${index}`}>
                <span className="trace-line__time">{event.event_type}</span>
                <span className="trace-line__event">{JSON.stringify(event.data)}</span>
              </div>
            ))}
            {auditEntries.map((entry, index) => (
              <div className="trace-line" key={`${String(entry.action || entry.agent_name || index)}-${index}`}>
                <span className="trace-line__time">
                  {formatDateTime(String(entry.created_at || entry.timestamp || ""))}
                </span>
                <span className="trace-line__event">
                  {String(entry.agent_name || entry.agent || "system")} | {" "}
                  {String(entry.action || entry.event_type || "event")} | {" "}
                  {String(entry.status || "recorded")}
                </span>
              </div>
            ))}
            {!liveEvents.length && !auditEntries.length ? (
              <div className="trace-line">
                <span className="trace-line__time">idle</span>
                <span className="trace-line__event">
                  No live events have been received yet for this vendor.
                </span>
              </div>
            ) : null}
          </div>
        </div>
      </section>
    </div>
  );
}
