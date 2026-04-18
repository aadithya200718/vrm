export interface VendorSummary {
  id: string;
  name: string;
  vendor_type?: string;
  workflow_type?: "saas" | "healthcare";
  ephi_involved?: boolean;
  status?: string;
  contract_value?: number;
  domain?: string;
  contact_email?: string;
  created_at?: string;
  updated_at?: string;
  overall_risk_score?: number | null;
  risk_level?: string | null;
  approval_tier?: string | null;
  approval_status?: string | null;
}

export interface VendorStatus {
  vendor_id: string;
  vendor_name: string;
  vendor_type?: string;
  workflow_type?: "saas" | "healthcare";
  ephi_involved?: boolean;
  vendor_domain?: string;
  contract_value?: number;
  contact_email?: string;
  status?: string;
  current_phase?: string;
  current_agent?: string;
  current_step?: string;
  progress_percentage?: number;
  errors?: string[];
  agent_errors?: Array<{
    agent?: string;
    action?: string;
    error?: string;
    timestamp?: string;
  }>;
  has_errors?: boolean;
  overall_risk_score?: number | null;
  risk_level?: string | null;
  approval_tier?: string | null;
  approval_status?: string | null;
  approval_id?: string | null;
}

export interface ReviewResponse {
  vendor_id: string;
  vendor_name?: string;
  status?: string;
  message?: string;
  security_review?: Record<string, unknown>;
  compliance_review?: Record<string, unknown>;
  financial_review?: Record<string, unknown>;
}

export interface EvidenceRequest {
  id: string;
  document_type: string;
  criticality?: string;
  reason?: string;
  status?: string;
  email_sent?: boolean;
  deadline?: string;
  created_at?: string;
}

export interface EvidenceGapResponse {
  vendor_id: string;
  vendor_name?: string;
  total_requests?: number;
  pending?: number;
  received?: number;
  completion_percentage?: number;
  evidence_requests?: EvidenceRequest[];
}

export interface EvidenceStatusResponse {
  vendor_id: string;
  vendor_name?: string;
  evidence_requests?: number;
  tracking_entries?: number;
  requests?: Array<{
    id: string;
    document_type: string;
    status?: string;
    email_sent?: boolean;
    deadline?: string;
  }>;
  recent_tracking?: Array<{
    action?: string;
    actor?: string;
    details?: string;
    created_at?: string;
  }>;
}

export interface RiskAssessmentResponse {
  vendor_id: string;
  status?: string;
  message?: string;
  risk_assessment?: {
    overall_risk_score?: number;
    risk_level?: string;
    approval_tier?: string;
    breakdown?: Record<string, { score?: number; weight?: number }>;
    executive_summary?: string;
    critical_blockers?: string[];
    conditional_items?: string[];
    mitigation_recommendations?: string[];
    completed_at?: string;
    bayesian_tier?: string;
    rl_tier?: string;
    models_agree?: boolean;
    confidence_indicator?: string;
  };
}

export interface VendorReport {
  vendor: {
    id: string;
    name: string;
    type?: string;
    contract_value?: number;
    domain?: string;
    status?: string;
  };
  documents: {
    total?: number;
    items?: Array<{
      id: string;
      file_name?: string;
      classification?: string;
      classification_confidence?: number;
      processing_status?: string;
      extracted_dates?: Record<string, unknown>;
    }>;
  };
  security_review?: {
    overall_score?: number;
    grade?: string;
    status?: string;
    report?: Record<string, unknown>;
  } | null;
  compliance_review?: {
    overall_score?: number;
    grade?: string;
    status?: string;
    report?: Record<string, unknown>;
  } | null;
  financial_review?: {
    overall_score?: number;
    grade?: string;
    status?: string;
    report?: Record<string, unknown>;
  } | null;
  risk_assessment?: {
    overall_risk_score?: number;
    risk_level?: string;
    approval_tier?: string;
    executive_summary?: string;
    critical_blockers?: string[];
    conditional_items?: string[];
  } | null;
  approval?: {
    id?: string;
    status?: string;
    approval_tier?: string;
    required_approvers?: Array<Record<string, unknown>>;
    deadline?: string;
  } | null;
  evidence_gaps?: {
    total?: number;
    pending?: number;
    received?: number;
  };
  audit_trail?: Array<{
    agent?: string;
    action?: string;
    tool?: string;
    status?: string;
    duration_ms?: number;
    timestamp?: string;
  }>;
}

export interface DocumentListResponse {
  vendor_id: string;
  vendor_name?: string;
  total_documents?: number;
  documents?: Array<{
    id: string;
    file_name?: string;
    file_type?: string;
    classification?: string;
    classification_confidence?: number;
    extracted_metadata?: Record<string, unknown>;
    extracted_dates?: Record<string, unknown>;
    processing_status?: string;
    created_at?: string;
  }>;
}

export interface ApprovalWorkflowResponse {
  vendor_id: string;
  approval_id?: string;
  approval_tier?: string;
  status?: string;
  message?: string;
  required_approvers?: Array<Record<string, unknown>>;
  workflow?: {
    id?: string | null;
    name?: string;
    approval_order?: string;
    timeout_hours?: number;
    current_step_role?: string;
  };
  deadline?: string;
}

export interface ApprovalDecisionListResponse {
  vendor_id: string;
  total?: number;
  decisions?: Array<{
    id: string;
    approver_name?: string;
    approver_role?: string;
    decision?: string;
    comments?: string;
    conditions?: string[];
    decided_at?: string;
  }>;
}

export interface ApprovalStatusResponse {
  vendor_id: string;
  approval_id?: string;
  status?: string;
  completion_percentage?: number;
  total_required?: number;
  total_decided?: number;
  pending_approvers?: Array<Record<string, unknown>>;
  overdue?: boolean;
  final_decision?: string | null;
  decisions?: Array<{
    approver?: string;
    role?: string;
    decision?: string;
    decided_at?: string;
  }>;
}

export interface ApprovalPacket {
  verification_results?: {
    standard?: Array<{
      id: string;
      kind: string;
      label?: string;
      result?: string;
      status?: string;
      confidence_score?: number;
      details?: Record<string, unknown>;
      agent_name?: string;
      queue_name?: string;
      created_at?: string;
    }>;
    hipaa?: Array<{
      id: string;
      kind: string;
      label?: string;
      result?: string;
      status?: string;
      confidence_score?: number;
      details?: Record<string, unknown>;
      agent_name?: string;
      queue_name?: string;
      created_at?: string;
    }>;
  } | null;
  vendor?: {
    id?: string;
    name?: string;
    workflow_type?: "saas" | "healthcare";
    ephi_involved?: boolean;
    contact_email?: string;
    contract_value?: number;
    status?: string;
  };
  documents?: unknown[];
  security_review?: Record<string, unknown> | null;
  compliance_review?: Record<string, unknown> | null;
  financial_review?: Record<string, unknown> | null;
  aggregate_score?: number | null;
  risk_assessment?: {
    overall_risk_score?: number;
    risk_level?: string;
    approval_tier?: string;
    executive_summary?: string;
    probability_legitimate?: number;
    probability_fraud?: number;
    confidence_interval?: {
      low?: number;
      high?: number;
    } | null;
    evidence_explanation?: string[];
    hard_override?: string | null;
    hipaa_overrides?: string[];
    hipaa_risk_factors?: string[];
    critical_blockers?: string[];
    conditional_items?: string[];
    mitigation_recommendations?: Array<{
      description?: string;
      implementation?: string;
    }>;
    bayesian_tier?: string;
    rl_tier?: string;
    models_agree?: boolean;
    confidence_indicator?: string;
    baa_clauses?: Record<string, { present?: boolean; exact_quote?: string; confidence?: number }> | null;
    baa_clauses_missing?: string[];
    baa_expiry_date?: string | null;
  } | null;
  approval_workflow?: {
    name?: string;
    approval_order?: string;
    approvers?: Array<Record<string, unknown>>;
    current_step_role?: string | null;
    deadline?: string;
  } | null;
  evidence_gaps?: Array<Record<string, unknown>>;
  recommendation?: string;
  audit_trail_count?: number;
  status_history?: Array<Record<string, unknown>>;
  approval_history?: Array<Record<string, unknown>>;
  generated_at?: string;
}

export interface AuditTrailResponse {
  vendor_id?: string;
  vendor_name?: string;
  total_events?: number;
  trail?: Array<Record<string, unknown>>;
  audit_trail?: Array<Record<string, unknown>>;
  timeline?: Array<Record<string, unknown>>;
}

export interface DashboardRecentResponse {
  recent_vendors?: VendorSummary[];
  recent_approvals?: Array<Record<string, unknown>>;
  recent_completions?: VendorSummary[];
}

export interface DashboardStatsResponse {
  [key: string]: number | string | boolean | null | undefined;
}

export interface WorkflowEvent {
  vendor_id: string;
  event_type: string;
  data: Record<string, unknown>;
}

export interface VendorRequestResponse {
  status: string;
  request_id: string;
  vendor_id?: string;
  workflow_type: "saas" | "healthcare";
  message: string;
}

export interface TokenValidationResponse {
  valid: boolean;
  vendor_id?: string;
  vendor_name?: string;
  workflow_type?: "saas" | "healthcare";
  expires_at?: string;
  documents_required?: number;
}

export interface PortalUploadResponse {
  status: string;
  vendor_id: string;
  documents_received: number;
  documents_required: number;
  missing: string[];
  document_ids: string[];
}

export interface EphiAccessLogResponse {
  vendor_id: string;
  entries: Array<{
    id: string;
    actor_email: string;
    actor_role: string;
    action: string;
    details?: Record<string, unknown>;
    created_at?: string;
  }>;
}

export interface ComplianceQueryResponse {
  answer: string;
  sources?: Array<Record<string, unknown>>;
}

export interface HealthcareChatResponse {
  status: string;
  reply: string;
}
