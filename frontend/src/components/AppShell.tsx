import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import {
  Navigate,
  NavLink,
  Outlet,
  useLocation,
  useNavigate,
  useParams,
} from "react-router-dom";
import { useShell } from "../app/ShellContext";
import { getDashboardRecent, listVendors } from "../lib/api";
import { ENV_APPROVAL_TOKEN } from "../lib/config";
import { formatDateTime, normalizeText } from "../lib/utils";

function shellStageLinks(vendorId?: string) {
  if (vendorId) {
    return {
      intake: `/vendors/${vendorId}#documents`,
      review: `/vendors/${vendorId}#review`,
      evidence: `/vendors/${vendorId}#evidence`,
      risk: `/vendors/${vendorId}#risk`,
      approval: `/audit/${vendorId}`,
    };
  }

  return {
    intake: "/intake",
    review: "/vendors",
    evidence: "/pipelines?stage=evidence",
    risk: "/pipelines?stage=risk",
    approval: "/audit",
  };
}

export function ApprovalAliasRedirect() {
  const { vendorId } = useParams();
  if (!vendorId) {
    return <Navigate replace to="/audit" />;
  }
  return <Navigate replace to={`/audit/${vendorId}`} />;
}

function AppPanel() {
  const { activePanel, closePanel, approvalToken, setApprovalToken } = useShell();
  const recentQuery = useQuery({
    queryKey: ["dashboard", "recent", "shell"],
    queryFn: getDashboardRecent,
  });

  if (!activePanel) {
    return null;
  }

  return (
    <div className="overlay" onClick={closePanel} role="presentation">
      <aside className="overlay-panel" onClick={(event) => event.stopPropagation()}>
        <div className="overlay-panel__header">
          <h2>
            {activePanel === "notifications"
              ? "Recent Activity"
              : activePanel === "settings"
                ? "Client Settings"
                : "Support"}
          </h2>
          <button className="icon-button" onClick={closePanel} type="button">
            <span className="material-symbols-outlined">close</span>
          </button>
        </div>

        {activePanel === "notifications" ? (
          <div className="overlay-panel__body">
            <p className="panel-kicker">Recent vendors and approvals from the backend feed.</p>
            {recentQuery.data ? (
              <div className="overlay-list">
                {(recentQuery.data.recent_vendors || []).slice(0, 6).map((vendor) => (
                  <div className="overlay-list__item" key={vendor.id}>
                    <strong>{vendor.name}</strong>
                    <span>{vendor.status || "processing"}</span>
                    <span>{formatDateTime(vendor.updated_at)}</span>
                  </div>
                ))}
                {(recentQuery.data.recent_approvals || []).slice(0, 4).map((approval, index) => (
                  <div className="overlay-list__item" key={`approval-${index}`}>
                    <strong>{String(approval.vendor_name || approval.vendor_id || "Approval")}</strong>
                    <span>{String(approval.status || approval.decision || "pending")}</span>
                    <span>{formatDateTime(String(approval.decided_at || approval.created_at || ""))}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="panel-muted">
                Live activity will appear here once the dashboard endpoints respond.
              </p>
            )}
          </div>
        ) : null}

        {activePanel === "settings" ? (
          <div className="overlay-panel__body overlay-form">
            <label className="field">
              <span>API base</span>
              <input
                readOnly
                value={import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000"}
              />
            </label>
            <label className="field">
              <span>Operator bearer token</span>
              <textarea
                onChange={(event) => setApprovalToken(event.target.value)}
                placeholder="Paste admin, employee, or approver token here"
                rows={4}
                value={approvalToken}
              />
            </label>
            <p className="panel-muted">
              Env token {ENV_APPROVAL_TOKEN ? "is present" : "is not configured"}.
              Local token {approvalToken ? "is active" : "is empty"}.
            </p>
          </div>
        ) : null}

        {activePanel === "support" ? (
          <div className="overlay-panel__body">
            <p className="panel-kicker">Route guidance for this MVP.</p>
            <div className="overlay-list">
              <div className="overlay-list__item">
                <strong>Intake</strong>
                <span>Create a vendor assessment and upload source documents.</span>
              </div>
              <div className="overlay-list__item">
                <strong>Trace</strong>
                <span>Watch vendor-scoped workflow events and audit logs.</span>
              </div>
              <div className="overlay-list__item">
                <strong>Audit</strong>
                <span>Review approval packet, blockers, decisions, and final rationale.</span>
              </div>
            </div>
          </div>
        ) : null}
      </aside>
    </div>
  );
}

export function AppShell() {
  const location = useLocation();
  const navigate = useNavigate();
  const { vendorId } = useParams();
  const vendorsQuery = useQuery({
    queryKey: ["vendors", "shell-selector"],
    queryFn: () => listVendors(),
  });
  const { searchValue, setSearchValue, openPanel } = useShell();

  const stageLinks = shellStageLinks(vendorId);

  useEffect(() => {
    setSearchValue("");
  }, [location.pathname, setSearchValue]);

  const activeVendorOptions = vendorsQuery.data?.vendors || [];

  return (
    <div className="shell-root">
      <header className="topbar print-hidden">
        <div className="topbar__brand">
          <button className="brand-mark" onClick={() => navigate("/pipelines")} type="button">
            Hackstrom Tower
          </button>
          <nav className="topbar__nav">
            <NavLink className="topbar__link" to="/trace">
              Trace
            </NavLink>
            <NavLink className="topbar__link" to="/pipelines">
              Pipelines
            </NavLink>
            <NavLink className="topbar__link" to="/vendors">
              Vendors
            </NavLink>
            <NavLink className="topbar__link" to="/audit">
              Audit
            </NavLink>
            <NavLink className="topbar__link" to="/dashboard/compliance">
              Compliance
            </NavLink>
          </nav>
        </div>
        <div className="topbar__actions">
          <label className="search-input">
            <span className="material-symbols-outlined">search</span>
            <input
              aria-label="Search current page"
              onChange={(event) => setSearchValue(event.target.value)}
              placeholder="SEARCH CURRENT PAGE"
              value={searchValue}
            />
          </label>
          <button className="icon-button" onClick={() => openPanel("notifications")} type="button">
            <span className="material-symbols-outlined">notifications</span>
          </button>
          <button className="icon-button" onClick={() => openPanel("settings")} type="button">
            <span className="material-symbols-outlined">settings</span>
          </button>
          <div className="avatar-block" aria-label="Operator avatar">
            HT
          </div>
        </div>
      </header>

      <div className="shell-body">
        <aside className="sidebar print-hidden">
          <div className="sidebar__header">
            <p>Control Tower</p>
            <span>v2.4.0</span>
          </div>

          <nav className="sidebar__nav">
            <NavLink
              className={
                normalizeText(location.pathname).includes("/intake")
                  ? "sidebar__stage sidebar__stage--active"
                  : "sidebar__stage"
              }
              to={stageLinks.intake}
            >
              <span className="material-symbols-outlined">input</span>
              <span>Intake</span>
            </NavLink>
            <NavLink
              className={
                normalizeText(location.pathname).includes("/vendors")
                  ? "sidebar__stage sidebar__stage--active"
                  : "sidebar__stage"
              }
              to={stageLinks.review}
            >
              <span className="material-symbols-outlined">visibility</span>
              <span>Review</span>
            </NavLink>
            <NavLink
              className={
                location.hash === "#evidence" ||
                normalizeText(location.search).includes("stage=evidence")
                  ? "sidebar__stage sidebar__stage--active"
                  : "sidebar__stage"
              }
              to={stageLinks.evidence}
            >
              <span className="material-symbols-outlined">fact_check</span>
              <span>Evidence</span>
            </NavLink>
            <NavLink
              className={
                location.hash === "#risk" ||
                normalizeText(location.search).includes("stage=risk")
                  ? "sidebar__stage sidebar__stage--active"
                  : "sidebar__stage"
              }
              to={stageLinks.risk}
            >
              <span className="material-symbols-outlined">warning</span>
              <span>Risk</span>
            </NavLink>
            <NavLink
              className={
                normalizeText(location.pathname).includes("/audit")
                  ? "sidebar__stage sidebar__stage--active"
                  : "sidebar__stage"
              }
              to={stageLinks.approval}
            >
              <span className="material-symbols-outlined">verified</span>
              <span>Approval</span>
            </NavLink>
          </nav>

          {vendorId ? (
            <div className="sidebar__selector">
              <label htmlFor="vendor-selector">Trace Vendor</label>
              <select
                id="vendor-selector"
                onChange={(event) => navigate(`/trace/${event.target.value}`)}
                value={vendorId}
              >
                {activeVendorOptions.map((vendor) => (
                  <option key={vendor.id} value={vendor.id}>
                    {vendor.name}
                  </option>
                ))}
              </select>
            </div>
          ) : null}

          <div className="sidebar__footer">
            <button className="button button--accent" onClick={() => navigate("/intake")} type="button">
              New Assessment
            </button>
            <button className="sidebar__support" onClick={() => openPanel("support")} type="button">
              <span className="material-symbols-outlined">help</span>
              <span>Support</span>
            </button>
          </div>
        </aside>

        <main className="page-canvas">
          <Outlet />
        </main>
      </div>

      <AppPanel />
    </div>
  );
}
