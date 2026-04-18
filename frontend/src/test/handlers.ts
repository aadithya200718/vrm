import { http, HttpResponse } from "msw";

const API = "http://127.0.0.1:8000/api/v1";

const vendors = [
  {
    id: "vendor-1",
    name: "Datastream.io",
    vendor_type: "observability",
    workflow_type: "healthcare",
    ephi_involved: true,
    status: "pending_approval",
    contract_value: 240000,
    domain: "datastream.io",
    contact_email: "security@datastream.io",
    updated_at: "2026-04-15T10:30:00Z",
    risk_level: "Moderate Risk",
    approval_tier: "Tier 1",
    approval_status: "pending",
  },
  {
    id: "vendor-2",
    name: "CloudStream Systems Ltd.",
    vendor_type: "cloud",
    workflow_type: "saas",
    ephi_involved: false,
    status: "processing",
    contract_value: 125000,
    domain: "cloudstream.io",
    contact_email: "ops@cloudstream.io",
    updated_at: "2026-04-15T11:00:00Z",
    risk_level: "High Risk",
    approval_tier: "Tier 2",
    approval_status: null,
  },
];

const vendorStatus = {
  vendor_id: "vendor-1",
  vendor_name: "Datastream.io",
  vendor_type: "observability",
  vendor_domain: "datastream.io",
  contract_value: 240000,
  contact_email: "security@datastream.io",
  status: "pending_approval",
  current_phase: "evidence_coordination",
  current_agent: "evidence_coordinator",
  current_step: "waiting_for_soc2",
  progress_percentage: 68,
  errors: [],
  agent_errors: [],
  has_errors: false,
  overall_risk_score: 74,
  risk_level: "Moderate Risk",
  approval_tier: "Tier 1",
  approval_status: "pending",
  approval_id: "approval-1",
  workflow_type: "healthcare",
  ephi_involved: true,
};

const vendorReport = {
  vendor: {
    id: "vendor-1",
    name: "Datastream.io",
    type: "observability",
    contract_value: 240000,
    domain: "datastream.io",
    status: "pending_approval",
  },
  documents: {
    total: 2,
    items: [
      {
        id: "doc-1",
        file_name: "security_questionnaire.pdf",
        classification: "Security Questionnaire",
        classification_confidence: 0.96,
        processing_status: "processed",
      },
      {
        id: "doc-2",
        file_name: "privacy_policy.pdf",
        classification: "Privacy Policy",
        classification_confidence: 0.88,
        processing_status: "processed",
      },
    ],
  },
  security_review: { overall_score: 81, grade: "B", status: "completed" },
  compliance_review: { overall_score: 77, grade: "B", status: "completed" },
  financial_review: { overall_score: 69, grade: "C", status: "completed" },
  risk_assessment: {
    overall_risk_score: 74,
    risk_level: "Moderate Risk",
    approval_tier: "Tier 1",
    executive_summary: "Moderate risk due to missing evidence and access control exceptions.",
    critical_blockers: ["MFA enforcement missing for admin database access"],
    conditional_items: ["Provide updated SOC2 Type II report"],
  },
  approval: {
    id: "approval-1",
    status: "pending",
    approval_tier: "Tier 1",
    required_approvers: [{ role: "approver" }],
  },
  evidence_gaps: { total: 2, pending: 1, received: 1 },
  audit_trail: [
    {
      agent: "security_review",
      action: "review_completed",
      status: "success",
      timestamp: "2026-04-15T10:20:00Z",
    },
  ],
};

export const handlers = [
  http.get(`${API}/vendors`, () =>
    HttpResponse.json({
      total: vendors.length,
      vendors,
    }),
  ),
  http.get(`${API}/dashboard/stats`, () =>
    HttpResponse.json({
      active_reviews: 3,
      pending_approvals: 1,
      completed_reviews: 7,
      total_vendors: 12,
    }),
  ),
  http.get(`${API}/dashboard/recent`, () =>
    HttpResponse.json({
      recent_vendors: vendors,
      recent_approvals: [
        {
          vendor_name: "CloudStream Systems Ltd.",
          status: "approved",
          decided_at: "2026-04-15T10:00:00Z",
        },
      ],
      recent_completions: [vendors[0]],
    }),
  ),
  http.get(`${API}/vendors/vendor-1/status`, () => HttpResponse.json(vendorStatus)),
  http.get(`${API}/vendors/vendor-1/report`, () => HttpResponse.json(vendorReport)),
  http.get(`${API}/vendors/vendor-1/security`, () =>
    HttpResponse.json({
      vendor_id: "vendor-1",
      security_review: {
        status: "completed",
        overall_score: 81,
        grade: "B",
        critical_issues: ["MFA enforcement missing for administrative access"],
        report: { summary: "Security scan complete." },
      },
    }),
  ),
  http.get(`${API}/vendors/vendor-1/compliance`, () =>
    HttpResponse.json({
      vendor_id: "vendor-1",
      compliance_review: {
        status: "completed",
        overall_score: 77,
        grade: "B",
        gaps: ["DPA annex requires updated processor inventory"],
        report: { summary: "Compliance review complete." },
      },
    }),
  ),
  http.get(`${API}/vendors/vendor-1/financial`, () =>
    HttpResponse.json({
      vendor_id: "vendor-1",
      financial_review: {
        status: "completed",
        overall_score: 69,
        grade: "C",
        findings: ["Insurance coverage expires in 60 days"],
        report: { summary: "Financial review complete." },
      },
    }),
  ),
  http.get(`${API}/vendors/vendor-1/evidence-gaps`, () =>
    HttpResponse.json({
      vendor_id: "vendor-1",
      vendor_name: "Datastream.io",
      total_requests: 2,
      pending: 1,
      received: 1,
      completion_percentage: 50,
      evidence_requests: [
        {
          id: "req-1",
          document_type: "SOC2 Type II (2023)",
          status: "pending",
          reason: "Latest assurance report required for approval packet.",
          deadline: "2026-04-20T10:00:00Z",
        },
      ],
    }),
  ),
  http.get(`${API}/vendors/vendor-1/evidence-status`, () =>
    HttpResponse.json({
      vendor_id: "vendor-1",
      vendor_name: "Datastream.io",
      evidence_requests: 2,
      tracking_entries: 1,
      recent_tracking: [
        {
          action: "reminder_sent",
          details: "SOC2 reminder sent to vendor contact.",
          created_at: "2026-04-15T09:45:00Z",
        },
      ],
    }),
  ),
  http.get(`${API}/vendors/vendor-1/risk-assessment`, () =>
    HttpResponse.json({
      vendor_id: "vendor-1",
      risk_assessment: {
        overall_risk_score: 74,
        risk_level: "Moderate Risk",
        approval_tier: "Tier 1",
        executive_summary:
          "Moderate risk driven by missing evidence and identity controls.",
        critical_blockers: ["MFA enforcement missing for admin database access"],
        conditional_items: ["Provide updated SOC2 Type II report"],
      },
    }),
  ),
  http.get(`${API}/vendors/vendor-1/approval-status`, () =>
    HttpResponse.json({
      vendor_id: "vendor-1",
      approval_id: "approval-1",
      status: "pending",
      completion_percentage: 50,
      total_required: 2,
      total_decided: 1,
      pending_approvers: [{ role: "security_lead" }],
    }),
  ),
  http.get(`${API}/vendors/vendor-1/documents`, () =>
    HttpResponse.json({
      vendor_id: "vendor-1",
      documents: [
        {
          id: "doc-1",
          file_name: "security_questionnaire.pdf",
          classification: "Security Questionnaire",
          processing_status: "processed",
          created_at: "2026-04-15T10:10:00Z",
        },
      ],
    }),
  ),
  http.get(`${API}/vendors/vendor-1/approval-packet`, () =>
    HttpResponse.json({
      vendor: { name: "Datastream.io", workflow_type: "healthcare" },
      verification_results: {
        standard: [
          {
            id: "verify-gst",
            kind: "gst",
            label: "GST Verification",
            result: "verified",
            status: "success",
            confidence_score: 0.91,
            agent_name: "GST Verification",
            details: { gst_number: "29ABCDE1234F1Z5" },
          },
          {
            id: "verify-soc2",
            kind: "soc2",
            label: "SOC 2 Review",
            result: "verified",
            status: "success",
            confidence_score: 0.88,
            agent_name: "SOC 2 Parser",
            details: { audit_type: "Type II", expiry_date: "2026-11-30" },
          },
        ],
        hipaa: [
          {
            id: "hipaa-oig",
            kind: "oig",
            label: "OIG Exclusion Check",
            result: "clear",
            status: "success",
            confidence_score: 0.95,
            agent_name: "OIG Exclusion Check",
            details: {},
          },
          {
            id: "hipaa-flow",
            kind: "ephi_flow",
            label: "ePHI Flow Analysis",
            result: "compliant",
            status: "success",
            confidence_score: 0.92,
            agent_name: "ePHI Data Flow Analyzer",
            details: {
              encryption_verified: true,
              jurisdiction_verified: true,
              risks: [],
            },
          },
        ],
      },
      recommendation: "Approve with conditions.",
      risk_assessment: {
        overall_risk_score: 74,
        risk_level: "Moderate Risk",
        approval_tier: "Tier 1",
        probability_legitimate: 0.74,
        probability_fraud: 0.26,
        confidence_interval: { low: 0.68, high: 0.8 },
        evidence_explanation: [
          "gst adjusted score by +0.16",
          "soc2 adjusted score by +0.15",
        ],
        bayesian_tier: "Tier 2",
        rl_tier: "Tier 2",
        models_agree: true,
        confidence_indicator: "green",
        executive_summary:
          "Approval can proceed once evidence and access control exceptions are resolved.",
        critical_blockers: ["MFA enforcement missing for admin database access"],
        conditional_items: ["Provide updated SOC2 Type II report"],
        mitigation_recommendations: [
          { description: "Enforce MFA for administrative access" },
        ],
        baa_clauses: {
          breach_notification_60_days: { present: true },
          encryption_at_rest_in_transit: { present: true },
        },
        baa_clauses_missing: [],
        baa_expiry_date: "2027-04-15T00:00:00Z",
      },
      approval_workflow: {
        name: "Tier 1 Review",
        current_step_role: "legal",
        deadline: "2026-04-22T12:00:00Z",
      },
    }),
  ),
  http.get(`${API}/vendors/vendor-1/approval-workflow`, () =>
    HttpResponse.json({
      vendor_id: "vendor-1",
      status: "pending",
      required_approvers: [{ role: "legal" }, { role: "finance" }, { role: "it" }, { role: "compliance_officer" }],
      workflow: { name: "Tier 1 Review", approval_order: "sequential", current_step_role: "legal" },
      deadline: "2026-04-22T12:00:00Z",
    }),
  ),
  http.get(`${API}/vendors/vendor-1/approvals`, () =>
    HttpResponse.json({
      vendor_id: "vendor-1",
      total: 1,
      decisions: [
        {
          id: "decision-1",
          approver_name: "Alice Approver",
          decision: "approve",
          comments: "Security controls acceptable with conditions.",
          decided_at: "2026-04-15T11:05:00Z",
        },
      ],
    }),
  ),
  http.get(`${API}/vendors/vendor-1/audit-trail`, () =>
    HttpResponse.json({
      vendor_id: "vendor-1",
      audit_trail: [
        {
          agent_name: "security_review",
          action: "review_completed",
          status: "success",
          created_at: "2026-04-15T10:20:00Z",
        },
      ],
      trail: [
        {
          agent_name: "evidence_coordinator",
          action: "reminder_sent",
          status: "success",
          created_at: "2026-04-15T10:40:00Z",
        },
      ],
    }),
  ),
  http.post(`${API}/vendors/onboard`, () =>
    HttpResponse.json({
      status: "accepted",
      vendor_id: "vendor-1",
      message: "Vendor Datastream.io onboarding started.",
      status_url: "/api/v1/vendors/vendor-1/status",
      report_url: "/api/v1/vendors/vendor-1/report",
    }),
  ),
  http.post(`${API}/vendor/request`, () =>
    HttpResponse.json({
      status: "pending_review",
      request_id: "request-1",
      vendor_id: "vendor-1",
      workflow_type: "saas",
      message: "Vendor request submitted successfully.",
    }),
  ),
  http.post(`${API}/healthcare/vendor/request`, () =>
    HttpResponse.json({
      status: "hipaa_review_triggered",
      request_id: "request-1",
      vendor_id: "vendor-1",
      workflow_type: "healthcare",
      message: "Healthcare workflow triggered through the ePHI gate.",
    }),
  ),
  http.post(`${API}/vendors/vendor-1/documents`, () =>
    HttpResponse.json({
      status: "accepted",
      vendor_id: "vendor-1",
      message: "Documents uploaded and processing started.",
      files_uploaded: ["extra-evidence.pdf"],
    }),
  ),
  http.post(`${API}/vendors/vendor-1/request-evidence`, () =>
    HttpResponse.json({
      status: "accepted",
      message: "Evidence coordination triggered.",
    }),
  ),
  http.post(`${API}/approvals/vendor-1/legal`, () =>
    HttpResponse.json({
      status: "pending",
      decision_id: "decision-2",
      approval_complete: false,
      next_step: "finance",
      message: "Decision recorded successfully.",
    }),
  ),
  http.post(`${API}/approvals/vendor-1/finance`, () =>
    HttpResponse.json({
      status: "pending",
      decision_id: "decision-3",
      approval_complete: false,
      next_step: "it",
      message: "Decision recorded successfully.",
    }),
  ),
  http.post(`${API}/approvals/vendor-1/it`, () =>
    HttpResponse.json({
      status: "pending",
      decision_id: "decision-4",
      approval_complete: false,
      next_step: "compliance_officer",
      message: "Decision recorded successfully.",
    }),
  ),
  http.post(`${API}/healthcare/approvals/vendor-1/compliance`, () =>
    HttpResponse.json({
      status: "success",
      decision_id: "decision-5",
      approval_complete: true,
      final_outcome: "approved",
      message: "Decision recorded successfully.",
    }),
  ),
  http.get(`${API}/healthcare/ephi-log/vendor-1`, () =>
    HttpResponse.json({
      vendor_id: "vendor-1",
      entries: [
        {
          id: "ephi-1",
          actor_email: "compliance@hackstrom.local",
          actor_role: "compliance_officer",
          action: "packet_opened",
          created_at: "2026-04-15T10:25:00Z",
        },
      ],
    }),
  ),
  http.post(`${API}/rag/compliance/query`, () =>
    HttpResponse.json({
      answer: "The BAA is complete and the ePHI flow map is compliant.",
      sources: [{ type: "baa_record", status: "BAA_COMPLETE" }],
    }),
  ),
];
