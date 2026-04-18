import { useMutation } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useShell } from "../app/ShellContext";
import { StateView } from "../components/StateView";
import { StatusBadge } from "../components/StatusBadge";
import {
  createHealthcareVendorRequest,
  createVendorRequest,
  parseDocuments,
  uploadVendorDocuments,
} from "../lib/api";
import type { ParsedDocumentResult } from "../lib/api";

type WorkflowOption = "saas" | "healthcare";
type ParseStepKey = "parse" | "classify" | "metadata" | "dates";

const EPHI_TYPES = [
  "patient_records",
  "billing_data",
  "clinical_notes",
  "lab_results",
] as const;

const PARSE_STEPS: { key: ParseStepKey; label: string; desc: string }[] = [
  { key: "parse", label: "Extract Text", desc: "Parsing document content and tables" },
  { key: "classify", label: "Classify", desc: "Identifying document category" },
  { key: "metadata", label: "Extract Metadata", desc: "Pulling vendor details" },
  { key: "dates", label: "Extract Dates", desc: "Finding expiration and effective dates" },
];

function stepStatus(doc: ParsedDocumentResult, stepKey: ParseStepKey) {
  const step = doc.steps[stepKey];
  if (!step) return "pending" as const;
  if (step.status === "success") return "done" as const;
  if (step.status === "error") return "error" as const;
  return "done" as const;
}

function ParseResultCard({ doc }: { doc: ParsedDocumentResult }) {
  return (
    <div className="card">
      <div className="card__header">
        <div>
          <p className="page__kicker">Parsed Document</p>
          <h2 className="section-title">{doc.file_name}</h2>
        </div>
        <StatusBadge tone={doc.status === "completed" ? "info" : "danger"}>
          {doc.status}
        </StatusBadge>
      </div>
      <div className="stack">
        <div className="parse-step-grid">
          {PARSE_STEPS.map((step, i) => {
            const s = stepStatus(doc, step.key);
            const stepData = doc.steps[step.key];
            return (
              <div className={`parse-step parse-step--${s}`} key={step.key}>
                <div className="parse-step__number">{i + 1}</div>
                <div className="parse-step__content">
                  <div className="parse-step__title">{step.label}</div>
                  <div className="parse-step__desc">
                    {s === "pending"
                      ? "Waiting..."
                      : s === "error"
                        ? String(stepData?.error || "Failed")
                        : step.desc}
                  </div>
                </div>
                <StatusBadge tone={s === "done" ? "info" : s === "error" ? "danger" : "muted"}>
                  {s === "done" ? "Done" : s === "error" ? "Error" : "Pending"}
                </StatusBadge>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

export function IntakePage() {
  const navigate = useNavigate();
  const { approvalToken } = useShell();
  const [workflowType, setWorkflowType] = useState<WorkflowOption>("saas");
  const [vendorName, setVendorName] = useState("");
  const [serviceType, setServiceType] = useState("");
  const [reason, setReason] = useState("");
  const [contractValue, setContractValue] = useState("100000");
  const [contactEmail, setContactEmail] = useState("");
  const [ephiInvolved, setEphiInvolved] = useState(false);
  const [ephiTypes, setEphiTypes] = useState<string[]>([]);
  const [files, setFiles] = useState<File[]>([]);
  const [submittedSummary, setSubmittedSummary] = useState<{
    workflow_type: string;
    request_id: string;
    vendor_id?: string;
    message: string;
  } | null>(null);

  const parseMutation = useMutation({
    mutationFn: () => parseDocuments(files),
  });

  const intakeMutation = useMutation({
    mutationFn: async () => {
      const commonPayload = {
        vendor_name: vendorName,
        service_type: serviceType,
        reason,
        contract_value: Number(contractValue || 0),
        contact_email: contactEmail,
      };
      const response =
        workflowType === "healthcare"
          ? await createHealthcareVendorRequest(
              {
                ...commonPayload,
                ephi_involved: ephiInvolved,
                ephi_types: ephiInvolved ? ephiTypes : [],
              },
              approvalToken,
            )
          : await createVendorRequest(commonPayload, approvalToken);

      if (response.vendor_id && files.length) {
        await uploadVendorDocuments(response.vendor_id, files);
      }
      return response;
    },
    onSuccess: (result) => {
      setSubmittedSummary(result);
      if (result.vendor_id) {
        navigate(`/vendors/${result.vendor_id}`);
      }
    },
  });

  const parseResults = parseMutation.data?.results || [];
  const checklistCount = useMemo(
    () => (workflowType === "healthcare" && ephiInvolved ? 11 : 8),
    [ephiInvolved, workflowType],
  );

  return (
    <div className="page">
      <section className="page__header">
        <div>
          <h1 className="page__title page__title--compact">Vendor Intake</h1>
          <p className="page__subtitle">
            Submit a SaaS or Healthcare vendor request, trigger the ePHI gate, and optionally pre-parse the first document bundle.
          </p>
        </div>
      </section>

      <section className="split-grid">
        <div className="form-panel">
          <div className="card__header">
            <div>
              <p className="page__kicker">Request Form</p>
              <h2 className="section-title">Workflow Selection</h2>
            </div>
          </div>
          <div className="stack">
            <div className="button-row">
              <button
                className={`button ${workflowType === "saas" ? "button--primary" : ""}`}
                onClick={() => setWorkflowType("saas")}
                type="button"
              >
                IT/SaaS Vendor
              </button>
              <button
                className={`button ${workflowType === "healthcare" ? "button--primary" : ""}`}
                onClick={() => setWorkflowType("healthcare")}
                type="button"
              >
                Healthcare Vendor
              </button>
            </div>

            <label className="field">
              <span>Vendor name</span>
              <input onChange={(event) => setVendorName(event.target.value)} value={vendorName} />
            </label>
            <label className="field">
              <span>Service type</span>
              <input onChange={(event) => setServiceType(event.target.value)} value={serviceType} />
            </label>
            <label className="field">
              <span>Reason</span>
              <textarea onChange={(event) => setReason(event.target.value)} rows={4} value={reason} />
            </label>
            <label className="field">
              <span>Contract value</span>
              <input
                inputMode="numeric"
                onChange={(event) => setContractValue(event.target.value)}
                value={contractValue}
              />
            </label>
            <label className="field">
              <span>Vendor contact email</span>
              <input onChange={(event) => setContactEmail(event.target.value)} value={contactEmail} />
            </label>

            {workflowType === "healthcare" ? (
              <>
                <label className="field">
                  <span>ePHI gate</span>
                  <label className="button-row" style={{ justifyContent: "flex-start" }}>
                    <input
                      checked={ephiInvolved}
                      onChange={(event) => setEphiInvolved(event.target.checked)}
                      type="checkbox"
                    />
                    <span>Does this vendor handle ePHI?</span>
                  </label>
                </label>
                {ephiInvolved ? (
                  <div className="field">
                    <span>Types of ePHI</span>
                    <div className="file-list">
                      {EPHI_TYPES.map((value) => (
                        <label className="file-pill" key={value}>
                          <input
                            checked={ephiTypes.includes(value)}
                            onChange={(event) => {
                              if (event.target.checked) {
                                setEphiTypes((current) => [...current, value]);
                              } else {
                                setEphiTypes((current) => current.filter((item) => item !== value));
                              }
                            }}
                            type="checkbox"
                          />
                          {value.replace(/_/g, " ")}
                        </label>
                      ))}
                    </div>
                  </div>
                ) : null}
              </>
            ) : null}

            <label className="field">
              <span>Optional starter files</span>
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

            <div className="button-row">
              <button
                className="button button--blue"
                disabled={!files.length || parseMutation.isPending}
                onClick={() => parseMutation.mutate()}
                type="button"
              >
                {parseMutation.isPending ? "Parsing..." : "Parse Files"}
              </button>
              <button
                className="button button--primary"
                disabled={
                  intakeMutation.isPending ||
                  !vendorName.trim() ||
                  !serviceType.trim() ||
                  !reason.trim() ||
                  !contactEmail.trim() ||
                  !approvalToken
                }
                onClick={() => intakeMutation.mutate()}
                type="button"
              >
                {intakeMutation.isPending ? "Submitting..." : "Submit Intake"}
              </button>
            </div>

            {!approvalToken ? (
              <StateView
                detail="Paste a bearer token in Settings. For local development, use a dev token such as dev-role:admin:ops@hackstrom.local."
                title="Auth Required"
              />
            ) : null}

            {submittedSummary ? (
              <div className="card" style={{ background: "var(--yellow)" }}>
                <div className="card__header">
                  <div>
                    <p className="page__kicker">Submitted</p>
                    <h2 className="section-title">{submittedSummary.workflow_type.toUpperCase()} Workflow</h2>
                  </div>
                  <StatusBadge tone="info">{submittedSummary.request_id}</StatusBadge>
                </div>
                <p>{submittedSummary.message}</p>
              </div>
            ) : null}
          </div>
        </div>

        <div className="detail-grid__column">
          <div className="card">
            <div className="card__header">
              <div>
                <p className="page__kicker">Checklist Preview</p>
                <h2 className="section-title">Expected Document Bundle</h2>
              </div>
              <StatusBadge tone="info">{`${checklistCount} docs`}</StatusBadge>
            </div>
            <div className="stack">
              <div className="item-row">
                <div className="item-row__title">Routing</div>
                <div>
                  {workflowType === "healthcare" && ephiInvolved
                    ? "Healthcare workflow with HIPAA checks, 4-step approval, and append-only ePHI auditing."
                    : "SaaS workflow with standard verification, risk scoring, and 3-step approval."}
                </div>
              </div>
              <div className="item-row">
                <div className="item-row__title">Portal invite</div>
                <div>
                  {workflowType === "healthcare" && ephiInvolved
                    ? "10-day healthcare portal token with 11-document checklist."
                    : "7-day vendor portal token with 8-document checklist."}
                </div>
              </div>
              <div className="item-row">
                <div className="item-row__title">Parallel work</div>
                <div>Document parsing, embeddings, verifications, and risk scoring continue after upload completion.</div>
              </div>
            </div>
          </div>

          {parseResults.length ? (
            <>
              {parseResults.map((doc) => (
                <ParseResultCard doc={doc} key={doc.file_name} />
              ))}
            </>
          ) : (
            <div className="card">
              <div className="card__header">
                <div>
                  <p className="page__kicker">Flow Mapping</p>
                  <h2 className="section-title">What Happens Next</h2>
                </div>
              </div>
              <div className="stack">
                <div className="item-row">
                  <div className="item-row__title">1. Intake</div>
                  <div>Employee request is persisted with the workflow route and ePHI context.</div>
                </div>
                <div className="item-row">
                  <div className="item-row__title">2. Invite</div>
                  <div>Procurement sends a vendor portal token with the correct checklist.</div>
                </div>
                <div className="item-row">
                  <div className="item-row__title">3. Verify</div>
                  <div>Standard checks run in parallel; healthcare adds OIG, BAA, attestation, ePHI flow, and subprocessor checks.</div>
                </div>
                <div className="item-row">
                  <div className="item-row__title">4. Score</div>
                  <div>Bayesian and RL models generate a risk tier, blockers, and approval packet.</div>
                </div>
              </div>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
