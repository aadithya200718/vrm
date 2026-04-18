import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <div className="page">
      <div className="state-view">
        <h2>Route Not Found</h2>
        <p>The requested page is not part of the mapped workflow. Use one of the live routes below.</p>
        <div className="button-row">
          <Link className="button button--primary" to="/pipelines">
            Pipelines
          </Link>
          <Link className="button" to="/vendors">
            Vendors
          </Link>
          <Link className="button" to="/audit">
            Audit
          </Link>
        </div>
      </div>
    </div>
  );
}
