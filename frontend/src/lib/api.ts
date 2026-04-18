import { API_BASE_URL } from "./config";
import type {
  ApprovalDecisionListResponse,
  ApprovalPacket,
  ApprovalStatusResponse,
  ApprovalWorkflowResponse,
  AuditTrailResponse,
  ComplianceQueryResponse,
  DashboardRecentResponse,
  DashboardStatsResponse,
  DocumentListResponse,
  EphiAccessLogResponse,
  EvidenceGapResponse,
  EvidenceStatusResponse,
  HealthcareChatResponse,
  PortalUploadResponse,
  RiskAssessmentResponse,
  ReviewResponse,
  TokenValidationResponse,
  VendorReport,
  VendorRequestResponse,
  VendorStatus,
  VendorSummary,
} from "./types";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

type RequestOptions = {
  method?: string;
  body?: BodyInit | null;
  headers?: HeadersInit;
  allow404?: false;
};

type RequestOptionsAllow404 = Omit<RequestOptions, "allow404"> & {
  allow404: true;
};

async function fetchJson<T>(path: string, options: RequestOptionsAllow404): Promise<T | null>;
async function fetchJson<T>(path: string, options?: RequestOptions): Promise<T>;
async function fetchJson<T>(path: string, options: RequestOptions | RequestOptionsAllow404 = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: options.method || "GET",
    body: options.body,
    headers: options.headers,
  });

  if (options.allow404 && response.status === 404) {
    return null;
  }

  if (!response.ok) {
    throw new ApiError(response.status, await response.text());
  }

  return (await response.json()) as T;
}

export function getVendorEventsUrl(vendorId: string) {
  return `${API_BASE_URL}/vendors/${vendorId}/events`;
}

export function createVendorRequest(payload: {
  vendor_name: string;
  service_type: string;
  reason: string;
  contract_value: number;
  contact_email: string;
}, token?: string) {
  return fetchJson<VendorRequestResponse>("/vendor/request", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(payload),
  });
}

export function createHealthcareVendorRequest(payload: {
  vendor_name: string;
  service_type: string;
  reason: string;
  contract_value: number;
  contact_email: string;
  ephi_involved: boolean;
  ephi_types: string[];
}, token?: string) {
  return fetchJson<VendorRequestResponse>("/healthcare/vendor/request", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(payload),
  });
}

export function inviteVendor(requestId: string, healthcare = false, token?: string) {
  return fetchJson<{
    status: string;
    token: string;
    portal_url: string;
    expires_at: string;
    checklist_count: number;
  }>(`/${healthcare ? "healthcare/" : ""}vendor/invite/${requestId}`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  });
}

export function validateOnboardingToken(token: string) {
  return fetchJson<TokenValidationResponse>(`/vendor/validate-token/${token}`);
}

export function uploadVendorTokenDocuments(token: string, files: File[]) {
  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file);
  }
  return fetchJson<PortalUploadResponse>(`/vendor/upload/${token}`, {
    method: "POST",
    body: formData,
  });
}

export function uploadHealthcareTokenDocuments(token: string, files: File[]) {
  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file);
  }
  return fetchJson<PortalUploadResponse>(`/healthcare/vendor/upload/${token}`, {
    method: "POST",
    body: formData,
  });
}

export function listVendors(status?: string) {
  const params = new URLSearchParams();
  if (status) {
    params.set("status", status);
  }

  const query = params.toString();
  return fetchJson<{ total: number; vendors: VendorSummary[] }>(
    `/vendors${query ? `?${query}` : ""}`,
  );
}

export function getDashboardStats() {
  return fetchJson<DashboardStatsResponse>("/dashboard/stats");
}

export function getDashboardRecent() {
  return fetchJson<DashboardRecentResponse>("/dashboard/recent");
}

export function getVendorStatus(vendorId: string) {
  return fetchJson<VendorStatus>(`/vendors/${vendorId}/status`);
}

export function getVendorReport(vendorId: string) {
  return fetchJson<VendorReport>(`/vendors/${vendorId}/report`);
}

export function getVendorSecurity(vendorId: string) {
  return fetchJson<ReviewResponse>(`/vendors/${vendorId}/security`);
}

export function getVendorCompliance(vendorId: string) {
  return fetchJson<ReviewResponse>(`/vendors/${vendorId}/compliance`);
}

export function getVendorFinancial(vendorId: string) {
  return fetchJson<ReviewResponse>(`/vendors/${vendorId}/financial`);
}

export function getVendorDocuments(vendorId: string) {
  return fetchJson<DocumentListResponse>(`/vendors/${vendorId}/documents`);
}

export function getVendorEvidenceGaps(vendorId: string) {
  return fetchJson<EvidenceGapResponse>(`/vendors/${vendorId}/evidence-gaps`);
}

export function getVendorEvidenceStatus(vendorId: string) {
  return fetchJson<EvidenceStatusResponse>(`/vendors/${vendorId}/evidence-status`);
}

export function requestVendorEvidence(vendorId: string) {
  return fetchJson<{ status: string; message: string }>(
    `/vendors/${vendorId}/request-evidence`,
    { method: "POST" },
  );
}

export function getVendorRiskAssessment(vendorId: string) {
  return fetchJson<RiskAssessmentResponse>(
    `/vendors/${vendorId}/risk-assessment`,
  );
}

export function getVendorApprovalPacket(vendorId: string) {
  return fetchJson<ApprovalPacket>(`/vendors/${vendorId}/approval-packet`, {
    allow404: true,
  });
}

export function getVendorApprovalWorkflow(vendorId: string) {
  return fetchJson<ApprovalWorkflowResponse>(
    `/vendors/${vendorId}/approval-workflow`,
  );
}

export function getVendorApprovalDecisions(vendorId: string) {
  return fetchJson<ApprovalDecisionListResponse>(
    `/vendors/${vendorId}/approvals`,
  );
}

export function getVendorApprovalStatus(vendorId: string) {
  return fetchJson<ApprovalStatusResponse>(
    `/vendors/${vendorId}/approval-status`,
  );
}

export function getVendorAuditTrail(vendorId: string) {
  return fetchJson<AuditTrailResponse>(`/vendors/${vendorId}/audit-trail`, {
    allow404: true,
  });
}

export function submitApprovalDecision(
  vendorId: string,
  token: string,
  role: "legal" | "finance" | "it" | "compliance_officer",
  payload: {
    decision: "approve" | "reject" | "request_changes";
    comments: string;
    conditions: string[];
    permission_level?: "read-only" | "read-write" | "admin";
  },
) {
  const path =
    role === "compliance_officer"
      ? `/healthcare/approvals/${vendorId}/compliance`
      : `/approvals/${vendorId}/${role}`;
  return fetchJson<{
    status: string;
    message: string;
    decision_id: string;
    approval_complete: boolean;
    final_outcome?: string;
    next_step?: string;
  }>(path, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export function onboardVendor(input: { prompt: string; files: File[] }) {
  const formData = new FormData();
  formData.append("prompt", input.prompt);
  for (const file of input.files) {
    formData.append("files", file);
  }

  return fetchJson<{
    status: string;
    vendor_id: string;
    message: string;
    status_url: string;
    report_url: string;
  }>("/vendors/onboard", {
    method: "POST",
    body: formData,
  });
}

export interface ParseStepResult {
  status: string;
  error?: string;
  [key: string]: unknown;
}

export interface ParsedDocumentResult {
  file_name: string;
  file_size: number;
  status: string;
  error?: string;
  steps: {
    parse?: ParseStepResult;
    classify?: ParseStepResult;
    metadata?: ParseStepResult;
    dates?: ParseStepResult;
  };
}

export interface ParseDocumentsResponse {
  status: string;
  total_files: number;
  results: ParsedDocumentResult[];
}

export function parseDocuments(files: File[]) {
  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file);
  }

  return fetchJson<ParseDocumentsResponse>("/documents/parse", {
    method: "POST",
    body: formData,
  });
}

export function uploadVendorDocuments(vendorId: string, files: File[]) {
  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file);
  }

  return fetchJson<{
    status: string;
    message: string;
    vendor_id: string;
    files_uploaded: string[];
  }>(`/vendors/${vendorId}/documents`, {
    method: "POST",
    body: formData,
  });
}

export function getEphiAccessLog(vendorId: string, token: string) {
  return fetchJson<EphiAccessLogResponse>(`/healthcare/ephi-log/${vendorId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export function queryComplianceRag(
  payload: { query: string; vendor_id?: string },
  token: string,
) {
  return fetchJson<ComplianceQueryResponse>("/rag/compliance/query", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export function sendHealthcareChat(payload: { token?: string; vendor_id?: string; message: string }) {
  return fetchJson<HealthcareChatResponse>("/chat/vendor/healthcare", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}
