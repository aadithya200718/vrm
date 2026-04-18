import { useQuery } from "@tanstack/react-query";
import { useDeferredValue, useMemo } from "react";
import { Link } from "react-router-dom";
import { useShell } from "../app/ShellContext";
import { StateView } from "../components/StateView";
import { StatusBadge } from "../components/StatusBadge";
import { listVendors } from "../lib/api";
import { PIPELINE_STAGES, resolveStageFromStatus, toneForRisk, toneForStatus } from "../lib/status";
import { formatCurrency, formatDateTime, normalizeText } from "../lib/utils";

export function VendorsPage() {
  const { searchValue } = useShell();
  const deferredSearch = useDeferredValue(normalizeText(searchValue));
  const vendorsQuery = useQuery({
    queryKey: ["vendors", "queue"],
    queryFn: () => listVendors(),
  });

  const vendors = vendorsQuery.data?.vendors || [];
  const filteredVendors = useMemo(() => {
    return vendors.filter((vendor) => {
      const haystack = normalizeText(
        `${vendor.name} ${vendor.domain || ""} ${vendor.status || ""} ${vendor.risk_level || ""}`,
      );
      return deferredSearch ? haystack.includes(deferredSearch) : true;
    });
  }, [deferredSearch, vendors]);

  if (vendorsQuery.isLoading) {
    return (
      <div className="page">
        <StateView detail="Loading vendor review queue." title="Vendor Queue Loading" />
      </div>
    );
  }

  if (vendorsQuery.isError) {
    return (
      <div className="page">
        <StateView
          detail="The backend vendor listing failed, so the review queue is unavailable."
          title="Vendor Queue Unavailable"
          tone="danger"
        />
      </div>
    );
  }

  return (
    <div className="page">
      <section className="page__header">
        <div>
          <h1 className="page__title">Vendors</h1>
          <p className="page__subtitle">
            Review queue aligned to the active workflow, evidence, risk, and approval stages.
          </p>
        </div>
        <div className="metrics-grid">
          <div className="metric-card metric-card--accent">
            <span className="metric-card__label">Queue Size</span>
            <span className="metric-card__value">{filteredVendors.length}</span>
          </div>
          <div className="metric-card">
            <span className="metric-card__label">Search Filter</span>
            <span className="metric-card__value">{deferredSearch ? "ON" : "OFF"}</span>
          </div>
        </div>
      </section>

      <section className="queue-panel">
        <div className="queue-panel__header">
          <div>
            <p className="page__kicker">Mapped from Stitch</p>
            <h2 className="section-title">Condensed Compliance Flow</h2>
          </div>
          <Link className="button" to="/intake">
            New Assessment
          </Link>
        </div>

        <div className="table">
          <div className="table__header">
            <div>Vendor Entity</div>
            <div>Stage</div>
            <div>Risk</div>
            <div>Approval</div>
            <div>Contract</div>
          </div>

          {filteredVendors.map((vendor) => {
            const stage = PIPELINE_STAGES.find(
              (entry) => entry.key === resolveStageFromStatus(vendor),
            );
            return (
              <div className="table__row" key={vendor.id}>
                <div>
                  <Link className="table__link" to={`/vendors/${vendor.id}`}>
                    {vendor.name}
                  </Link>
                  <div className="table__meta">
                    {vendor.domain || vendor.contact_email || formatDateTime(vendor.updated_at)}
                  </div>
                </div>
                <StatusBadge tone="muted">{stage?.label || "Review"}</StatusBadge>
                <StatusBadge tone={toneForRisk(vendor.risk_level)}>
                  {vendor.risk_level || "Pending"}
                </StatusBadge>
                <StatusBadge tone={toneForStatus(vendor.approval_status || vendor.status)}>
                  {vendor.approval_status || vendor.status || "Queued"}
                </StatusBadge>
                <div>{formatCurrency(vendor.contract_value)}</div>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
