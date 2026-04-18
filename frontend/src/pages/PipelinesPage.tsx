import { useQuery } from "@tanstack/react-query";
import { useDeferredValue, useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { StateView } from "../components/StateView";
import { StatusBadge } from "../components/StatusBadge";
import { useShell } from "../app/ShellContext";
import { getDashboardRecent, getDashboardStats, listVendors } from "../lib/api";
import { PIPELINE_STAGES, deriveStageCounts, resolveStageFromStatus, toneForRisk, toneForStatus } from "../lib/status";
import { formatCompactNumber, formatDateTime, normalizeText } from "../lib/utils";

export function PipelinesPage() {
  const { searchValue } = useShell();
  const deferredSearch = useDeferredValue(normalizeText(searchValue));
  const [searchParams, setSearchParams] = useSearchParams();
  const stageFilter = searchParams.get("stage") || "";

  const vendorsQuery = useQuery({
    queryKey: ["vendors", "pipelines"],
    queryFn: () => listVendors(),
  });
  const statsQuery = useQuery({
    queryKey: ["dashboard", "stats"],
    queryFn: getDashboardStats,
  });
  const recentQuery = useQuery({
    queryKey: ["dashboard", "recent"],
    queryFn: getDashboardRecent,
  });

  const vendors = vendorsQuery.data?.vendors || [];
  const stageCounts = deriveStageCounts(vendors);

  const filteredVendors = useMemo(() => {
    return vendors.filter((vendor) => {
      const matchesStage = stageFilter
        ? resolveStageFromStatus(vendor) === stageFilter
        : true;
      const haystack = normalizeText(
        `${vendor.name} ${vendor.domain || ""} ${vendor.status || ""} ${vendor.risk_level || ""}`,
      );
      const matchesSearch = deferredSearch ? haystack.includes(deferredSearch) : true;
      return matchesStage && matchesSearch;
    });
  }, [deferredSearch, stageFilter, vendors]);

  if (vendorsQuery.isLoading) {
    return (
      <div className="page">
        <StateView
          detail="Loading vendor pipelines and dashboard metrics."
          title="Pipeline Loading"
        />
      </div>
    );
  }

  if (vendorsQuery.isError) {
    return (
      <div className="page">
        <StateView
          detail="The vendor list did not load, so the pipeline cannot be derived."
          title="Pipeline Unavailable"
          tone="danger"
        />
      </div>
    );
  }

  const highRiskCount = vendors.filter((vendor) =>
    normalizeText(vendor.risk_level || "").includes("high"),
  ).length;

  return (
    <div className="page">
      <section className="page__header">
        <div>
          <h1 className="page__title">Pipeline</h1>
          <p className="page__subtitle">
            Real-time synchronization of vendor compliance and risk mitigation across five strategic gates.
          </p>
        </div>
        <div className="stats-row">
          <div className="metric-card">
            <span className="metric-card__label">Active Objects</span>
            <span className="metric-card__value">{formatCompactNumber(vendors.length)}</span>
          </div>
          <div className="metric-card metric-card--blue">
            <span className="metric-card__label">Alert Level</span>
            <span className="metric-card__value">{highRiskCount ? "CRIT" : "NOM"}</span>
          </div>
        </div>
      </section>

      <section className="pipeline-grid">
        {PIPELINE_STAGES.map((stage) => (
          <button
            className={`pipeline-card ${stageFilter === stage.key ? "pipeline-card--active" : ""}`}
            key={stage.key}
            onClick={() => {
              const next = new URLSearchParams(searchParams);
              if (stageFilter === stage.key) {
                next.delete("stage");
              } else {
                next.set("stage", stage.key);
              }
              setSearchParams(next);
            }}
            type="button"
          >
            <div className="pipeline-card__icon">
              {stage.key === "intake" ? "01" : stage.key === "review" ? "02" : stage.key === "evidence" ? "03" : stage.key === "risk" ? "04" : "05"}
            </div>
            <div className="pipeline-card__value">{stageCounts[stage.key]}</div>
            <h2 className="pipeline-card__title">{stage.label}</h2>
            <div className="button-row">
              <StatusBadge tone={stageFilter === stage.key ? "warning" : "muted"}>
                {stageFilter === stage.key ? "Filtered" : "Open"}
              </StatusBadge>
            </div>
          </button>
        ))}
      </section>

      <section className="page-grid">
        <div className="queue-panel">
          <div className="queue-panel__header">
            <div>
              <p className="page__kicker">Workflow Queue</p>
              <h2 className="section-title">Vendor Routing</h2>
            </div>
            <StatusBadge tone="info">{`${filteredVendors.length} Visible`}</StatusBadge>
          </div>
          <div className="table">
            <div className="table__header">
              <div>Vendor</div>
              <div>Stage</div>
              <div>Risk</div>
              <div>Approval</div>
              <div>Updated</div>
            </div>
            {filteredVendors.map((vendor) => {
              const stage = resolveStageFromStatus(vendor);
              return (
                <div className="table__row" key={vendor.id}>
                  <Link className="table__link" to={`/vendors/${vendor.id}`}>
                    {vendor.name}
                  </Link>
                  <StatusBadge tone="muted">
                    {PIPELINE_STAGES.find((entry) => entry.key === stage)?.label || stage}
                  </StatusBadge>
                  <StatusBadge tone={toneForRisk(vendor.risk_level)}>
                    {String(vendor.risk_level || "Pending")}
                  </StatusBadge>
                  <StatusBadge tone={toneForStatus(vendor.approval_status || vendor.status)}>
                    {String(vendor.approval_status || vendor.status || "Queued")}
                  </StatusBadge>
                  <div className="table__meta">{formatDateTime(vendor.updated_at)}</div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="detail-grid__column">
          <div className="card">
            <div className="card__header">
              <div>
                <p className="page__kicker">Dashboard Feed</p>
                <h2 className="section-title">System Snapshot</h2>
              </div>
            </div>
            <div className="stack">
              {Object.entries(statsQuery.data || {}).slice(0, 4).map(([key, value]) => (
                <div className="data-row" key={key}>
                  <div className="data-row__title">{key.replace(/_/g, " ")}</div>
                  <div>{String(value)}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="card">
            <div className="card__header">
              <div>
                <p className="page__kicker">Recent Activity</p>
                <h2 className="section-title">Approvals and Completions</h2>
              </div>
            </div>
            <div className="stack">
              {(recentQuery.data?.recent_completions || []).slice(0, 4).map((vendor) => (
                <Link className="timeline-item" key={vendor.id} to={`/audit/${vendor.id}`}>
                  <span className="timeline-item__title">{vendor.name}</span>
                  <span>{vendor.status || "completed"}</span>
                  <span className="timeline-item__meta">{formatDateTime(vendor.updated_at)}</span>
                </Link>
              ))}
              {(recentQuery.data?.recent_vendors || []).slice(0, 4).map((vendor) => (
                <Link className="timeline-item" key={`recent-${vendor.id}`} to={`/trace/${vendor.id}`}>
                  <span className="timeline-item__title">{vendor.name}</span>
                  <span>{vendor.status || "processing"}</span>
                  <span className="timeline-item__meta">{formatDateTime(vendor.updated_at)}</span>
                </Link>
              ))}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
