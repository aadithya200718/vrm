import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { StateView } from "../components/StateView";
import { StatusBadge } from "../components/StatusBadge";
import { getVendorReport } from "../lib/api";
import { formatCurrency, formatDateTime } from "../lib/utils";

export function VendorReportPage() {
  const { vendorId = "" } = useParams();
  const [searchParams] = useSearchParams();
  const printMode = searchParams.get("print") === "1";
  const reportQuery = useQuery({
    queryKey: ["vendor", vendorId, "report"],
    queryFn: () => getVendorReport(vendorId),
    enabled: Boolean(vendorId),
  });

  useEffect(() => {
    if (!printMode) {
      return;
    }
    const timeoutId = window.setTimeout(() => window.print(), 150);
    return () => window.clearTimeout(timeoutId);
  }, [printMode]);

  if (reportQuery.isLoading) {
    return (
      <div className="page">
        <StateView detail="Loading report packet for printing." title="Report Loading" />
      </div>
    );
  }

  if (reportQuery.isError || !reportQuery.data) {
    return (
      <div className="page">
        <StateView
          detail="The consolidated report endpoint did not return data for this vendor."
          title="Report Unavailable"
          tone="danger"
        />
      </div>
    );
  }

  const report = reportQuery.data;

  return (
    <div className="page report-layout">
      <section className="page__header print-hidden">
        <div>
          <h1 className="page__title page__title--compact">Report Packet</h1>
          <p className="page__subtitle">
            Consolidated review, evidence, risk, and approval state for {report.vendor.name}.
          </p>
        </div>
        <div className="page__header-actions">
          <button className="button button--primary" onClick={() => window.print()} type="button">
            Print Report
          </button>
          <Link className="button" to={`/vendors/${vendorId}`}>
            Back to Workspace
          </Link>
        </div>
      </section>

      <section className="report-panel">
        <div className="card__header">
          <div>
            <p className="page__kicker">Vendor Summary</p>
            <h2 className="section-title">{report.vendor.name}</h2>
          </div>
          <StatusBadge tone="info">{report.vendor.status || "processing"}</StatusBadge>
        </div>
        <div className="metrics-grid">
          <div className="data-row">
            <div className="data-row__title">Vendor Type</div>
            <div>{report.vendor.type || "N/A"}</div>
          </div>
          <div className="data-row">
            <div className="data-row__title">Domain</div>
            <div>{report.vendor.domain || "N/A"}</div>
          </div>
          <div className="data-row">
            <div className="data-row__title">Contract Value</div>
            <div>{formatCurrency(report.vendor.contract_value)}</div>
          </div>
        </div>
      </section>

      <section className="split-grid">
        <div className="report-panel">
          <div className="card__header">
            <div>
              <p className="page__kicker">Documents</p>
              <h2 className="section-title">Evidence Inventory</h2>
            </div>
            <StatusBadge tone="muted">{`${report.documents.total || 0} Files`}</StatusBadge>
          </div>
          <div className="report-list">
            {(report.documents.items || []).map((document) => (
              <div className="report-list__item" key={document.id}>
                <strong>{document.file_name || "Unnamed file"}</strong>
                <div>{document.classification || "Unclassified"}</div>
                <div className="item-row__meta">
                  {document.processing_status || "queued"} | confidence {Math.round((document.classification_confidence || 0) * 100)}%
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="report-grid__column">
          <div className="report-panel">
            <div className="card__header">
              <div>
                <p className="page__kicker">Review Summary</p>
                <h2 className="section-title">Agent Scores</h2>
              </div>
            </div>
            <div className="stack">
              <div className="data-row">
                <div className="data-row__title">Security</div>
                <div>{report.security_review?.grade || "Pending"} | {report.security_review?.overall_score ?? "-"}</div>
              </div>
              <div className="data-row">
                <div className="data-row__title">Compliance</div>
                <div>{report.compliance_review?.grade || "Pending"} | {report.compliance_review?.overall_score ?? "-"}</div>
              </div>
              <div className="data-row">
                <div className="data-row__title">Financial</div>
                <div>{report.financial_review?.grade || "Pending"} | {report.financial_review?.overall_score ?? "-"}</div>
              </div>
            </div>
          </div>

          <div className="report-panel">
            <div className="card__header">
              <div>
                <p className="page__kicker">Risk and Approval</p>
                <h2 className="section-title">Decision Context</h2>
              </div>
            </div>
            <div className="stack">
              <div className="data-row">
                <div className="data-row__title">Overall Risk</div>
                <div>{report.risk_assessment?.overall_risk_score ?? "-"}</div>
              </div>
              <div className="data-row">
                <div className="data-row__title">Risk Level</div>
                <div>{report.risk_assessment?.risk_level || "Pending"}</div>
              </div>
              <div className="data-row">
                <div className="data-row__title">Approval Tier</div>
                <div>{report.risk_assessment?.approval_tier || report.approval?.approval_tier || "Pending"}</div>
              </div>
              <div className="data-row">
                <div className="data-row__title">Approval Status</div>
                <div>{report.approval?.status || "No approval"}</div>
              </div>
            </div>
            <p className="panel-muted">{report.risk_assessment?.executive_summary || "Executive summary pending."}</p>
          </div>
        </div>
      </section>

      <section className="report-panel">
        <div className="card__header">
          <div>
            <p className="page__kicker">Audit Trail</p>
            <h2 className="section-title">Persisted Workflow Events</h2>
          </div>
        </div>
        <div className="report-list">
          {(report.audit_trail || []).map((entry, index) => (
            <div className="report-list__item" key={`${entry.action}-${index}`}>
              <strong>{entry.action || entry.agent || "Audit Event"}</strong>
              <div>{entry.agent || "system"} | {entry.status || "recorded"} | {entry.tool || "no-tool"}</div>
              <div className="item-row__meta">{formatDateTime(entry.timestamp)}</div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
