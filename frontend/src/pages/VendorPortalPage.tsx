import { useMutation, useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { StateView } from "../components/StateView";
import { StatusBadge } from "../components/StatusBadge";
import {
  sendHealthcareChat,
  uploadHealthcareTokenDocuments,
  uploadVendorTokenDocuments,
  validateOnboardingToken,
} from "../lib/api";

export function VendorPortalPage({ healthcare }: { healthcare: boolean }) {
  const [searchParams] = useSearchParams();
  const [files, setFiles] = useState<File[]>([]);
  const [message, setMessage] = useState("");
  const token = searchParams.get("token") || "";

  const tokenQuery = useQuery({
    queryKey: ["portal-token", token],
    queryFn: () => validateOnboardingToken(token),
    enabled: Boolean(token),
  });

  const uploadMutation = useMutation({
    mutationFn: () =>
      healthcare
        ? uploadHealthcareTokenDocuments(token, files)
        : uploadVendorTokenDocuments(token, files),
  });

  const chatMutation = useMutation({
    mutationFn: () =>
      sendHealthcareChat({
        token,
        vendor_id: tokenQuery.data?.vendor_id,
        message,
      }),
  });

  const title = healthcare ? "Healthcare Vendor Portal" : "Vendor Portal";
  const requiredCount = tokenQuery.data?.documents_required || (healthcare ? 11 : 8);
  const uploadedCount = uploadMutation.data?.documents_received || 0;
  const missing = uploadMutation.data?.missing || [];
  const groupedChecklist = useMemo(() => {
    if (!healthcare) {
      return ["GST Certificate", "PAN Card", "Incorporation Certificate", "Cancelled Cheque", "SOC 2 Type II", "ISO 27001", "Penetration Test Report", "NDA"];
    }
    return [
      "GST Certificate",
      "PAN Card",
      "Incorporation Certificate",
      "Cancelled Cheque",
      "HIPAA Attestation",
      "BAA",
      "SOC 2 Type II",
      "ePHI Data Flow Map",
      "Subprocessor List",
      "Cyber Insurance",
      "Breach Policy",
    ];
  }, [healthcare]);

  if (!token) {
    return (
      <div className="page">
        <StateView detail="A portal token is required in the URL." title="Missing Token" tone="danger" />
      </div>
    );
  }

  if (tokenQuery.isLoading) {
    return (
      <div className="page">
        <StateView detail="Validating portal token and loading checklist." title="Portal Loading" />
      </div>
    );
  }

  if (!tokenQuery.data?.valid) {
    return (
      <div className="page">
        <StateView detail="This onboarding token is invalid or expired." title="Token Invalid" tone="danger" />
      </div>
    );
  }

  return (
    <div className="page">
      <section className="page__header">
        <div>
          <h1 className="page__title page__title--compact">{title}</h1>
          <p className="page__subtitle">
            {tokenQuery.data.vendor_name || "Vendor"} can upload the required onboarding package here.
          </p>
        </div>
        <div className="metrics-grid">
          <div className="metric-card">
            <span className="metric-card__label">Required</span>
            <span className="metric-card__value">{requiredCount}</span>
          </div>
          <div className="metric-card metric-card--accent">
            <span className="metric-card__label">Uploaded</span>
            <span className="metric-card__value">{uploadedCount}</span>
          </div>
        </div>
      </section>

      <section className="split-grid">
        <div className="form-panel">
          <div className="card__header">
            <div>
              <p className="page__kicker">Step 1</p>
              <h2 className="section-title">Document Upload</h2>
            </div>
            <StatusBadge tone="info">{String(tokenQuery.data.workflow_type || "portal")}</StatusBadge>
          </div>
          <div className="stack">
            <label className="field">
              <span>Upload documents</span>
              <input multiple onChange={(event) => setFiles(Array.from(event.target.files || []))} type="file" />
            </label>
            {files.length ? (
              <div className="file-list">
                {files.map((file) => (
                  <span className="file-pill" key={`${file.name}-${file.size}`}>
                    {file.name}
                  </span>
                ))}
              </div>
            ) : null}
            <button
              className="button button--primary"
              disabled={!files.length || uploadMutation.isPending}
              onClick={() => uploadMutation.mutate()}
              type="button"
            >
              {uploadMutation.isPending ? "Uploading..." : "Upload Documents"}
            </button>
            {uploadMutation.data ? (
              <div className="card" style={{ background: "var(--yellow)" }}>
                <div className="card__header">
                  <div>
                    <p className="page__kicker">Submission State</p>
                    <h2 className="section-title">Checklist Progress</h2>
                  </div>
                  <StatusBadge tone="warning">
                    {`${uploadMutation.data.documents_received}/${uploadMutation.data.documents_required}`}
                  </StatusBadge>
                </div>
                <p>
                  Missing items: {missing.length ? missing.join(", ") : "None. Verification has started."}
                </p>
              </div>
            ) : null}
          </div>
        </div>

        <div className="detail-grid__column">
          <div className="card">
            <div className="card__header">
              <div>
                <p className="page__kicker">Step 2</p>
                <h2 className="section-title">Checklist</h2>
              </div>
            </div>
            <div className="stack">
              {groupedChecklist.map((item) => (
                <div className={`item-row ${missing.includes(item) ? "item-row--warning" : ""}`} key={item}>
                  <div className="item-row__title">{item}</div>
                  <div>{missing.includes(item) ? "Pending" : "Required for submission"}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="card">
            <div className="card__header">
              <div>
                <p className="page__kicker">Step 3</p>
                <h2 className="section-title">{healthcare ? "HIPAA Chat Assistant" : "Portal Support"}</h2>
              </div>
            </div>
            <div className="stack">
              <label className="field">
                <span>Ask a question</span>
                <textarea onChange={(event) => setMessage(event.target.value)} rows={4} value={message} />
              </label>
              <button
                className="button button--blue"
                disabled={!message.trim() || chatMutation.isPending}
                onClick={() => chatMutation.mutate()}
                type="button"
              >
                {chatMutation.isPending ? "Thinking..." : "Send"}
              </button>
              {chatMutation.data ? <p>{chatMutation.data.reply}</p> : null}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
