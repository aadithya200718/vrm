# Vendor Risk Control Tower - Multi-Agent Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         USER REQUEST                                     │
│              "Onboard Acme Corp vendor for review"                       │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      SUPERVISOR AGENT                                    │
│                     (Orchestrator/Router)                                │
│                                                                           │
│  Tools:                                                                   │
│  • delegate_to_security_agent()                                          │
│  • delegate_to_compliance_agent()                                        │
│  • delegate_to_financial_agent()                                         │
│  • delegate_to_evidence_agent()                                          │
│  • compile_approval_packet()                                             │
│  • get_worker_status()                                                   │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
                    ▼                         ▼
         ┌──────────────────┐      ┌──────────────────┐
         │  INTAKE PHASE    │      │  PARALLEL REVIEW │
         └──────────────────┘      └──────────────────┘
```

---

## Agent 1: Document Intake Agent

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    DOCUMENT INTAKE AGENT                                 │
│                  (Parse & Classify Documents)                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  TOOLS (8):                                                              │
│                                                                           │
│  📄 parse_pdf(file_path)                                                 │
│     └─ Extract text from PDF documents                                   │
│                                                                           │
│  📄 parse_docx(file_path)                                                │
│     └─ Extract text from Word documents                                  │
│                                                                           │
│  📊 parse_excel(file_path)                                               │
│     └─ Extract data from spreadsheets                                    │
│                                                                           │
│  🏷️  classify_document(text)                                             │
│     └─ Identify document type (SOC2, Insurance, DPA, etc.)              │
│                                                                           │
│  🔍 extract_vendor_metadata(text)                                        │
│     └─ Pull company name, address, contact, industry                     │
│                                                                           │
│  📅 extract_dates(text)                                                  │
│     └─ Find expiration dates, effective dates                            │
│                                                                           │
│  💾 store_document_metadata(data)                                        │
│     └─ Save structured data to database                                  │
│                                                                           │
│  🖼️  ocr_scan(image_file)                                                │
│     └─ Handle scanned/image documents                                    │
│                                                                           │
├─────────────────────────────────────────────────────────────────────────┤
│  OUTPUT: Structured vendor data + classified documents                   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Agent 2: Security Review Agent

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    SECURITY REVIEW AGENT                                 │
│                  (Assess Security Posture)                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  TOOLS (10):                                                             │
│                                                                           │
│  🔍 search_security_policies(query)                                      │
│     └─ RAG search in security policy database                            │
│                                                                           │
│  ✅ validate_soc2_certificate(cert_data)                                 │
│     └─ Verify SOC2 Type 2 authenticity                                   │
│                                                                           │
│  ✅ validate_iso27001_certificate(cert_data)                             │
│     └─ Verify ISO 27001 authenticity                                     │
│                                                                           │
│  📅 check_certificate_expiry(cert_data)                                  │
│     └─ Verify certificates are not expired                               │
│                                                                           │
│  🌐 scan_domain_security(domain)                                         │
│     └─ External security scan (SSL, headers, vulnerabilities)            │
│                                                                           │
│  🚨 check_breach_history(company_name)                                   │
│     └─ Search breach databases (HaveIBeenPwned, etc.)                    │
│                                                                           │
│  📋 analyze_security_questionnaire(responses)                            │
│     └─ Score vendor security questionnaire answers                       │
│                                                                           │
│  🎯 calculate_security_score(findings)                                   │
│     └─ Weighted risk score calculation                                   │
│                                                                           │
│  📊 generate_security_report(findings)                                   │
│     └─ Create structured JSON security assessment                        │
│                                                                           │
│  ⚠️  flag_critical_issues(findings)                                      │
│     └─ Identify security blockers                                        │
│                                                                           │
├─────────────────────────────────────────────────────────────────────────┤
│  OUTPUT: Security assessment report with risk score (0-100)              │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Agent 3: Compliance Review Agent

```
┌─────────────────────────────────────────────────────────────────────────┐
│                   COMPLIANCE REVIEW AGENT                                │
│                (Verify Regulatory Compliance)                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  TOOLS (10):                                                             │
│                                                                           │
│  🔍 search_compliance_policies(query)                                    │
│     └─ RAG search in compliance policy database                          │
│                                                                           │
│  🇪🇺 check_gdpr_compliance(vendor_data)                                  │
│     └─ Validate GDPR requirements (EU data, DPO, etc.)                   │
│                                                                           │
│  🏥 check_hipaa_compliance(vendor_data)                                  │
│     └─ Validate HIPAA requirements (BAA, PHI handling)                   │
│                                                                           │
│  💳 check_pci_compliance(vendor_data)                                    │
│     └─ Validate PCI-DSS requirements                                     │
│                                                                           │
│  📜 verify_data_processing_agreement(dpa_doc)                            │
│     └─ Check DPA completeness (Article 28 clauses)                       │
│                                                                           │
│  🗄️  assess_data_retention_policy(policy_doc)                            │
│     └─ Review data retention practices                                   │
│                                                                           │
│  👥 check_subprocessor_list(vendor_data)                                 │
│     └─ Verify subprocessor disclosures                                   │
│                                                                           │
│  🔒 validate_privacy_policy(policy_url)                                  │
│     └─ Analyze privacy policy completeness                               │
│                                                                           │
│  🎯 calculate_compliance_score(findings)                                 │
│     └─ Weighted compliance score                                         │
│                                                                           │
│  📊 generate_compliance_report(findings)                                 │
│     └─ Create structured JSON compliance assessment                      │
│                                                                           │
├─────────────────────────────────────────────────────────────────────────┤
│  OUTPUT: Compliance assessment report with score (0-100)                 │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Agent 4: Financial Review Agent

```
┌─────────────────────────────────────────────────────────────────────────┐
│                   FINANCIAL REVIEW AGENT                                 │
│              (Assess Financial Stability & Insurance)                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  TOOLS (9):                                                              │
│                                                                           │
│  🔍 search_financial_policies(query)                                     │
│     └─ RAG search in financial requirements database                     │
│                                                                           │
│  🛡️  verify_insurance_coverage(policy_doc)                               │
│     └─ Check liability insurance coverage amounts                        │
│                                                                           │
│  📅 check_insurance_expiry(policy_doc)                                   │
│     └─ Verify insurance policy is current                                │
│                                                                           │
│  📊 get_credit_rating(company_name)                                      │
│     └─ External credit check (Dun & Bradstreet API)                      │
│                                                                           │
│  💰 analyze_financial_statements(statements)                             │
│     └─ Review balance sheet, P&L, cash flow                              │
│                                                                           │
│  ⚖️  check_bankruptcy_records(company_name)                              │
│     └─ Search public bankruptcy records                                  │
│                                                                           │
│  📋 verify_business_continuity_plan(bcp_doc)                             │
│     └─ Review BCP/DR plan adequacy                                       │
│                                                                           │
│  🎯 calculate_financial_risk_score(findings)                             │
│     └─ Weighted financial risk score                                     │
│                                                                           │
│  📊 generate_financial_report(findings)                                  │
│     └─ Create structured JSON financial assessment                       │
│                                                                           │
├─────────────────────────────────────────────────────────────────────────┤
│  OUTPUT: Financial assessment report with risk score (0-100)             │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Agent 5: Evidence Coordinator Agent

```
┌─────────────────────────────────────────────────────────────────────────┐
│                  EVIDENCE COORDINATOR AGENT                              │
│            (Identify Gaps & Request Missing Documents)                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  TOOLS (8):                                                              │
│                                                                           │
│  📋 get_required_documents(vendor_type, contract_value)                  │
│     └─ Fetch document requirements from policy DB                        │
│                                                                           │
│  🔍 compare_required_vs_submitted(required, submitted)                   │
│     └─ Gap analysis - identify missing documents                         │
│                                                                           │
│  ✉️  generate_evidence_request_email(gaps, vendor_contact)               │
│     └─ Draft professional evidence request email                         │
│                                                                           │
│  📧 send_email(recipient, subject, body)                                 │
│     └─ Send email via SMTP/SendGrid                                      │
│                                                                           │
│  ✅ create_followup_task(assignee, description, due_date)                │
│     └─ Create task in project management system                          │
│                                                                           │
│  📊 track_document_status(vendor_id)                                     │
│     └─ Monitor document submission status                                │
│                                                                           │
│  🔔 send_reminder_email(vendor_contact, outstanding_items)               │
│     └─ Send follow-up reminder                                           │
│                                                                           │
│  💾 update_evidence_log(vendor_id, status)                               │
│     └─ Record evidence collection progress                               │
│                                                                           │
├─────────────────────────────────────────────────────────────────────────┤
│  OUTPUT: Evidence gap report + follow-up tasks created                   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Agent 6: Risk Assessment Agent

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    RISK ASSESSMENT AGENT                                 │
│          (Aggregate Findings & Calculate Overall Risk)                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  TOOLS (8):                                                              │
│                                                                           │
│  🔄 aggregate_findings(security, compliance, financial)                  │
│     └─ Combine all worker agent reports                                  │
│                                                                           │
│  🎯 calculate_overall_risk_score(aggregated_data)                        │
│     └─ Weighted risk algorithm (security 40%, compliance 35%, fin 25%)   │
│                                                                           │
│  🚨 identify_critical_blockers(findings)                                 │
│     └─ Flag must-fix issues that prevent approval                        │
│                                                                           │
│  ⚠️  identify_conditional_approvals(findings)                            │
│     └─ Flag items that need conditions/mitigations                       │
│                                                                           │
│  📊 generate_executive_summary(data)                                     │
│     └─ High-level summary for leadership                                 │
│                                                                           │
│  👔 recommend_approval_tier(risk_score)                                  │
│     └─ Determine approval chain (auto/manager/VP/exec)                   │
│                                                                           │
│  📈 create_risk_matrix(findings)                                         │
│     └─ Visual risk breakdown by category                                 │
│                                                                           │
│  💡 generate_mitigation_recommendations(issues)                          │
│     └─ Suggest risk mitigation strategies                                │
│                                                                           │
├─────────────────────────────────────────────────────────────────────────┤
│  OUTPUT: Overall risk assessment + approval recommendation               │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Agent 7: Approval Orchestrator Agent

```
┌─────────────────────────────────────────────────────────────────────────┐
│                  APPROVAL ORCHESTRATOR AGENT                             │
│              (Route Approvals & Track Decisions)                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  TOOLS (9):                                                              │
│                                                                           │
│  🔍 get_approval_workflow(risk_tier)                                     │
│     └─ Fetch approval chain based on risk level                          │
│                                                                           │
│  📋 create_approval_request(approvers, packet)                           │
│     └─ Generate approval task with full context                          │
│                                                                           │
│  📧 send_approval_notification(approver, packet_link)                    │
│     └─ Email/Slack notification to approvers                             │
│                                                                           │
│  📊 track_approval_status(request_id)                                    │
│     └─ Monitor approval responses in real-time                           │
│                                                                           │
│  ✅ record_approval_decision(approver, decision, comments)               │
│     └─ Log individual approval decisions                                 │
│                                                                           │
│  🔍 check_all_approvals_complete(request_id)                             │
│     └─ Verify all required approvals received                            │
│                                                                           │
│  ✔️  finalize_vendor_status(vendor_id, approved, conditions)             │
│     └─ Update vendor status in system                                    │
│                                                                           │
│  📜 generate_audit_trail(vendor_id)                                      │
│     └─ Complete decision log with timestamps                             │
│                                                                           │
│  📧 send_vendor_notification(vendor_contact, outcome)                    │
│     └─ Inform vendor of approval decision                                │
│                                                                           │
├─────────────────────────────────────────────────────────────────────────┤
│  OUTPUT: Final approval decision + complete audit trail                  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Complete Workflow Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                                                                           │
│                            USER REQUEST                                   │
│                  "Onboard Acme Corp as vendor"                           │
│                                                                           │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │   SUPERVISOR AGENT     │
                    │    (Orchestrator)      │
                    │                        │
                    │  • Routes tasks        │
                    │  • Monitors progress   │
                    │  • Compiles results    │
                    └────────┬───────────────┘
                             │
                             ▼
                    ┌────────────────────────┐
                    │  DOCUMENT INTAKE       │
                    │  AGENT                 │
                    │                        │
                    │  8 tools               │
                    │  Parse, classify,      │
                    │  extract metadata      │
                    └────────┬───────────────┘
                             │
                             ▼
              ┌──────────────┴──────────────┐
              │                             │
              ▼                             ▼
    ┌─────────────────┐         ┌─────────────────┐
    │  PARALLEL       │         │  PARALLEL       │
    │  REVIEWS        │         │  REVIEWS        │
    └─────────────────┘         └─────────────────┘
              │                             │
    ┌─────────┼─────────┐         ┌────────┼────────┐
    │         │         │         │        │        │
    ▼         ▼         ▼         ▼        ▼        ▼
┌────────┐┌────────┐┌────────┐┌────────┐┌────────┐┌────────┐
│Security││Compli-││Finan-  ││Security││Compli- ││Finan-  │
│Agent   ││ance    ││cial    ││Agent   ││ance    ││cial    │
│        ││Agent   ││Agent   ││        ││Agent   ││Agent   │
│10 tools││10 tools││9 tools ││10 tools││10 tools││9 tools │
└───┬────┘└───┬────┘└───┬────┘└───┬────┘└───┬────┘└───┬────┘
    │         │         │         │        │        │
    └─────────┼─────────┘         └────────┼────────┘
              │                             │
              ▼                             ▼
    ┌─────────────────────────────────────────────┐
    │      EVIDENCE COORDINATOR AGENT             │
    │                                             │
    │  8 tools                                    │
    │  Gap analysis, request missing docs         │
    └──────────────────┬──────────────────────────┘
                       │
                       ▼
    ┌─────────────────────────────────────────────┐
    │       RISK ASSESSMENT AGENT                 │
    │                                             │
    │  8 tools                                    │
    │  Aggregate, score, recommend approval       │
    └──────────────────┬──────────────────────────┘
                       │
                       ▼
    ┌─────────────────────────────────────────────┐
    │     APPROVAL ORCHESTRATOR AGENT             │
    │                                             │
    │  9 tools                                    │
    │  Route approvals, track, finalize           │
    └──────────────────┬──────────────────────────┘
                       │
                       ▼
              ┌────────────────┐
              │ FINAL DECISION │
              │                │
              │ • Approved     │
              │ • Rejected     │
              │ • Conditional  │
              │                │
              │ + Audit Trail  │
              └────────────────┘
```

---

## Agent Communication Flow

```
Supervisor Agent
    │
    ├─→ Delegates to: Document Intake Agent
    │   └─→ Returns: Structured vendor data
    │
    ├─→ Delegates to: Security Agent (parallel)
    │   └─→ Returns: Security report + score
    │
    ├─→ Delegates to: Compliance Agent (parallel)
    │   └─→ Returns: Compliance report + score
    │
    ├─→ Delegates to: Financial Agent (parallel)
    │   └─→ Returns: Financial report + score
    │
    ├─→ Delegates to: Evidence Coordinator
    │   └─→ Returns: Gap analysis + follow-up tasks
    │
    ├─→ Delegates to: Risk Assessor
    │   └─→ Returns: Overall risk + recommendation
    │
    └─→ Delegates to: Approval Orchestrator
        └─→ Returns: Final decision + audit trail
```

---

## Tool Categories Summary

| Category | Tools | Used By |
|----------|-------|---------|
| **Document Processing** | 8 | Intake Agent |
| **Security Assessment** | 10 | Security Agent |
| **Compliance Checking** | 10 | Compliance Agent |
| **Financial Analysis** | 9 | Financial Agent |
| **Evidence Management** | 8 | Evidence Coordinator |
| **Risk Calculation** | 8 | Risk Assessor |
| **Approval Workflow** | 9 | Approval Orchestrator |
| **Orchestration** | 6 | Supervisor Agent |
| **TOTAL** | **68 tools** | **8 agents** |

---

## Key Design Patterns Used

1. **Multi-Agent (Supervisor) Pattern**
   - Supervisor delegates to specialized workers
   - Workers report back to supervisor
   - Supervisor compiles final output

2. **Tool Use Pattern**
   - Each agent has domain-specific tools
   - LLM decides which tools to call
   - Tools return structured data

3. **ReAct Pattern (Reason + Act)**
   - Agent reasons about what to do
   - Agent acts by calling tools
   - Agent observes results
   - Agent reasons about next step
   - Loop continues until task complete

4. **Parallel Execution**
   - Security, Compliance, Financial reviews run simultaneously
   - Reduces total processing time
   - Results aggregated by Evidence Coordinator

5. **State Management**
   - Shared state across all agents
   - Each agent updates relevant state fields
   - Enables coordination and handoffs

---

## Technology Stack

```
Backend:
├── FastAPI (REST API)
├── LangGraph (Agent orchestration)
├── LangChain (Tool integration)
├── OpenAI GPT-4 / Anthropic Claude (LLM)
├── PostgreSQL (Data storage)
└── Redis (State management)

Document Processing:
├── Unstructured.io (Document parsing)
├── PyPDF2 (PDF extraction)
└── python-docx (Word processing)

Vector Store (RAG):
├── Pinecone / Qdrant
└── OpenAI Embeddings

External APIs:
├── Dun & Bradstreet (Credit ratings)
├── HaveIBeenPwned (Breach data)
├── SecurityScorecard (Security scans)
└── SendGrid (Email)

Frontend:
├── React
├── TypeScript
└── TailwindCSS
```

---

## Next Steps

1. Implement tool functions (68 tools)
2. Define agent prompts and behaviors
3. Build LangGraph state machine
4. Create API endpoints
5. Build React dashboard
6. Add audit logging
7. Implement approval workflow UI

