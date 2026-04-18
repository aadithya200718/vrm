# Phase 2: Intake, Document Collection & Parallel Verification

## Objective
Implement the complete intake workflow with ePHI gate routing, vendor invitation system, document collection portals, document classification and embedding pipeline, and parallel verification agents for both standard and HIPAA-specific checks.

## Context
Building on Phase 1's infrastructure, this phase implements the first half of the vendor onboarding pipeline. The system must intelligently route vendors through either SaaS or Healthcare workflows based on ePHI involvement, collect appropriate documents (8 for SaaS, 11 for Healthcare), and run verification checks in parallel using both Celery workers simultaneously.

## Intake Agent Implementation

### Employee Intake Endpoints

**SaaS Intake:**
- Endpoint: `POST /api/v1/vendor/request`
- Auth: JWT required (employee role)
- Request body: `VendorRequestSchema`
  - vendor_name, service_type, reason, contract_value, contact_email
- Workflow:
  1. Validate JWT and employee role
  2. Check if vendor already exists (idempotency)
  3. Create `vendor_requests` record with `status: PENDING_REVIEW`
  4. Publish `send_notification_task` to `notification_queue` (notify procurement)
  5. Create OpenTelemetry trace span
  6. Return: `{ status, request_id, message }`

**Healthcare Intake (with ePHI Gate):**
- Endpoint: `POST /api/v1/healthcare/vendor/request`
- Auth: JWT required (employee role)
- Request body: `HealthcareVendorRequestSchema`
  - All SaaS fields PLUS:
  - `ephi_involved` (boolean) - CRITICAL routing field
  - `ephi_types` (array) - Types of ePHI: ["patient_records", "billing_data", "clinical_notes", "lab_results"]
- Workflow:
  1. Validate JWT and employee role
  2. **ePHI Gate Decision:**
     - If `ephi_involved = false` → redirect to SaaS workflow (call SaaS intake internally)
     - If `ephi_involved = true` → proceed with Healthcare workflow
  3. Create `vendor_requests` record with `hipaa_required: true`, `status: HIPAA_REVIEW_TRIGGERED`
  4. Publish notification to both Procurement AND Compliance Officer
  5. Create OpenTelemetry trace span with `ephi_involved` tag
  6. Return: `{ status, request_id, workflow_type: "healthcare", message }`

### Frontend Integration for Intake

**Existing Frontend Components:**
- `IntakePage.tsx` - Employee intake form
- Update to include Healthcare option with ePHI gate checkbox

**Required UI Changes:**
1. Add workflow type selector: "IT/SaaS Vendor" vs "Healthcare Vendor"
2. If Healthcare selected, show:
   - Checkbox: "Does this vendor handle ePHI (electronic Protected Health Information)?"
   - If checked, show multi-select: "Types of ePHI" (patient records, billing, clinical notes, lab results)
3. Submit to appropriate endpoint based on selection
4. Display confirmation with workflow type and next steps

## Vendor Invitation Agent

### Invitation Endpoints

**SaaS Invitation:**
- Endpoint: `POST /api/v1/vendor/invite/{request_id}`
- Auth: JWT (admin/procurement role)
- Workflow:
  1. Validate request exists and is in PENDING_REVIEW status
  2. Generate UUID token, store in `onboarding_tokens` with 7-day expiry
  3. Publish `send_invitation_email` task to `notification_queue`
  4. Email content:
     - Vendor portal link: `{FRONTEND_URL}/vendor/register?token={uuid}`
     - 8-document checklist: GST, PAN, Incorporation cert, Cancelled cheque, SOC 2, ISO 27001, Pen test report, NDA
     - Deadline: 7 days
  5. Update status: `INVITATION_SENT`
  6. Return: `{ status, token, portal_url, expires_at }`

**Healthcare Invitation:**
- Endpoint: `POST /api/v1/healthcare/vendor/invite/{request_id}`
- Auth: JWT (admin/procurement role)
- Workflow:
  1. Validate request exists and is in HIPAA_REVIEW_TRIGGERED status
  2. Generate UUID token, store in `onboarding_tokens` with 10-day expiry (longer for Healthcare)
  3. Publish `send_hipaa_invitation_email` task to `notification_queue`
  4. Email content:
     - HIPAA vendor portal link: `{FRONTEND_URL}/vendor/healthcare/register?token={uuid}`
     - 11-document checklist:
       - Standard: GST, PAN, Incorporation cert, Cancelled cheque
       - HIPAA-specific: HIPAA Compliance Attestation, Signed BAA, SOC 2 Type II + HITECH, ePHI Data Flow Map, Subprocessor List, Cyber Liability Insurance, Breach Notification Policy
     - Pre-filled BAA template attachment
     - Deadline: 10 days
  5. Update status: `INVITATION_SENT`
  6. Return: `{ status, token, portal_url, expires_at, checklist_count: 11 }`

### Email Templates (SendGrid)

**SaaS Invitation Template:**
- Subject: "Action Required: Complete Vendor Onboarding for {company_name}"
- Body: Portal link, checklist, deadline, support contact

**Healthcare Invitation Template:**
- Subject: "Action Required: HIPAA Vendor Onboarding for {company_name}"
- Body: Portal link, HIPAA checklist, BAA template link, deadline, HIPAA compliance support contact

## Document Collection Portals

### Vendor Portal Endpoints

**Token Validation:**
- Endpoint: `GET /api/v1/vendor/validate-token/{token}`
- No auth required (token itself is auth)
- Workflow:
  1. Check `onboarding_tokens` table
  2. Verify token exists, not used, not expired
  3. Return: `{ valid: true, vendor_id, workflow_type: "saas"|"healthcare", expires_at, documents_required: 8|11 }`

**Document Upload (SaaS):**
- Endpoint: `POST /api/v1/vendor/upload/{token}`
- Auth: Token-based
- Request: multipart/form-data with files
- Workflow:
  1. Validate token
  2. For each file:
     - Extract text (PyPDF2, python-docx, pytesseract for images)
     - Store extracted text in `vendor_documents` table
     - Publish `classify_document_task` to `verification_queue`
     - Publish `embed_document_task` to `embedding_queue`
  3. Check if all 8 documents received
  4. If complete: Update status to `DOCUMENTS_SUBMITTED`, publish `start_verification_tasks`
  5. Return: `{ status, documents_received: 5, documents_required: 8, missing: ["SOC 2", "ISO 27001", "Pen test"] }`

**Document Upload (Healthcare):**
- Endpoint: `POST /api/v1/healthcare/vendor/upload/{token}`
- Auth: Token-based
- Request: multipart/form-data with files
- Workflow:
  1. Validate token
  2. For each file:
     - Extract text for standard docs
     - Store BAA and ePHI Data Flow Map in Supabase Storage (encrypted, 6-year retention for BAA)
     - Tag document type: `baa`, `hipaa_attestation`, `ephi_flow_map`, etc.
     - Publish `classify_document_task` to `verification_queue`
     - Publish `embed_document_task` to `embedding_queue`
  3. Check if all 11 documents received
  4. If complete: Update status to `DOCUMENTS_SUBMITTED`, publish `start_verification_tasks` to BOTH `verification_queue` AND `hipaa_check_queue`
  5. Return: `{ status, documents_received: 8, documents_required: 11, missing: ["BAA", "ePHI Flow Map", "Breach Policy"] }`

### Document Classification Agent (GPT-4o)

**Celery Task:** `classify_document_task` (verification_queue)
- Input: vendor_id, document_id, extracted_text
- Tool: GPT-4o (temperature=0, structured JSON output)
- Prompt: "Classify this document into one of: [GST Certificate, PAN Card, Incorporation Certificate, Cancelled Cheque, SOC 2 Type II, ISO 27001, Penetration Test Report, NDA, HIPAA Attestation, BAA, ePHI Data Flow Map, Subprocessor List, Cyber Insurance, Breach Policy]. Return JSON: {classification, confidence, key_fields_found}"
- Workflow:
  1. Check idempotency (skip if already classified)
  2. Call GPT-4o with extracted text (chunked if > 4000 tokens)
  3. Store classification in `vendor_documents.classification` with confidence score
  4. Create OpenTelemetry child span: `document_classification`
  5. If confidence < 0.7, flag for manual review

### Document Embedding Agent (Self-Supervised)

**Celery Task:** `embed_document_task` (embedding_queue)
- Input: vendor_id, document_id, extracted_text, doc_type
- Tool: OpenAI text-embedding-3-small
- Workflow:
  1. Check idempotency (skip if embedding exists for this vendor + doc_type)
  2. Generate embedding vector (1536 dimensions)
  3. Store in `vendor_embeddings` table (pgvector)
  4. Tag with doc_type for RAG retrieval
  5. Special tags for Healthcare:
     - `doc_type: 'baa'` for BAA documents
     - `doc_type: 'hipaa_attestation'` for attestations
  6. Create OpenTelemetry child span: `document_embedding`

### Document Checklist Tracker

**Celery Beat Task:** `check_incomplete_submissions` (runs daily)
- Workflow:
  1. Query `vendor_requests` where status = `INVITATION_SENT` and created_at > 3 days ago
  2. For each incomplete submission:
     - Count documents received vs required
     - If missing docs, publish `send_reminder_email` to `notification_queue`
  3. If deadline passed (7 days SaaS, 10 days Healthcare):
     - Update status to `SUBMISSION_EXPIRED`
     - Notify procurement team

### Frontend Portal Components

**SaaS Vendor Portal (`/vendor/register?token=`):**
- Step 1: Company information form
- Step 2: Document upload (8 documents)
  - Drag-and-drop file upload
  - Progress indicator: "5 of 8 documents uploaded"
  - Missing documents highlighted in red
- Step 3: Confirmation and submission
- AI chatbot widget (vendor support)

**Healthcare Vendor Portal (`/vendor/healthcare/register?token=`):**
- Step 1: Company information + ePHI types confirmation
- Step 2: Document upload (11 documents)
  - Grouped by category: Standard (4), HIPAA Compliance (7)
  - BAA template download link
  - ePHI Data Flow Map example/template
  - Progress indicator: "8 of 11 documents uploaded"
- Step 3: HIPAA attestation review and confirmation
- HIPAA-aware AI chatbot widget

## Parallel Verification Agents

### Standard Verification Agents (Both Workflows)

All run as parallel Celery tasks on `verification_queue`, picked by worker-1 AND worker-2 simultaneously.

**GST Verification Agent:**
- Celery task: `verify_gst_task`
- Tool: Signzy/IDfy GST API
- Input: GST number from document
- Workflow:
  1. Idempotency check (skip if result exists)
  2. Call Signzy API
  3. Extract: company name, registration date, status (active/cancelled)
  4. Calculate confidence score (0.0-1.0)
  5. Store in `verification_results` table
  6. Create OpenTelemetry span: `gst_verification`
- Output: `{ result: "verified"|"failed", confidence_score, details }`

**PAN Verification Agent:**
- Celery task: `verify_pan_task`
- Tool: Surepass PAN API
- Input: PAN number from document
- Workflow: Same as GST
- Output: `{ result, confidence_score, name_match, details }`

**Bank Validation Agent:**
- Celery task: `verify_bank_task`
- Tool: Decentro penny drop API
- Input: Account number, IFSC from cancelled cheque
- Workflow:
  1. Idempotency check
  2. Initiate penny drop (₹1 deposit)
  3. Verify account holder name matches company name
  4. Calculate confidence score
  5. Store result
- Output: `{ result, confidence_score, account_holder_name, name_match_percentage }`

**MCA Verification Agent:**
- Celery task: `verify_mca_task`
- Tool: Karza/Signzy MCA API
- Input: Company name, CIN from incorporation certificate
- Workflow:
  1. Idempotency check
  2. Call MCA API
  3. Extract: director names, company age, status
  4. Store director names for sanctions cross-check
  5. Calculate confidence score
- Output: `{ result, confidence_score, directors: [], company_age_years, status }`

**Sanctions Check Agent:**
- Celery task: `check_sanctions_task`
- Tool: ComplyAdvantage API
- Input: Company name, director names (from MCA)
- Workflow:
  1. Idempotency check
  2. Check company name against sanctions lists
  3. Check each director name
  4. If any match found → flag as HIGH RISK
  5. Calculate confidence score
- Output: `{ result: "clear"|"flagged", confidence_score, matches: [], risk_level }`

**SOC 2 Parser Agent:**
- Celery task: `parse_soc2_task`
- Tool: GPT-4o (temperature=0, structured JSON)
- Input: SOC 2 report text
- Workflow:
  1. Idempotency check
  2. Chunk document (500-token chunks)
  3. Extract: audit type (Type I/II), expiry date, auditing firm, failed controls
  4. Self-consistency: run 3 times, compare results
  5. If results disagree → flag for manual review
  6. Calculate confidence score
- Output: `{ result, confidence_score, audit_type, expiry_date, failed_controls: [], auditing_firm }`

### Healthcare-Specific Verification Agents

All run as parallel Celery tasks on `hipaa_check_queue`, picked by worker-1 while worker-2 handles standard checks.

**OIG Exclusion Check Agent:**
- Celery task: `check_oig_task` (hipaa_check_queue)
- Tool: OIG LEIE API (free, public)
- Input: Vendor name, director names (from MCA agent)
- Workflow:
  1. Idempotency check
  2. Check vendor name against OIG exclusion list
  3. Check each director name
  4. **If excluded → AUTO_REJECT immediately** (hard override)
  5. Publish `rejection_notification_task` if excluded
  6. Confidence: 1.0 if clear, 0.0 if excluded
  7. Store in `hipaa_verifications` table
- Output: `{ result: "clear"|"excluded", confidence_score: 1.0|0.0, excluded_parties: [] }`
- OpenTelemetry span: `oig_exclusion_check`

**Extended Sanctions Check (Healthcare):**
- Celery task: `check_healthcare_sanctions_task` (hipaa_check_queue)
- Tool: ComplyAdvantage + CDSCO + NMC blacklists
- Input: Company name, directors
- Workflow: Same as standard sanctions but includes healthcare-specific lists
- Output: `{ result, confidence_score, matches: [], lists_checked: ["ComplyAdvantage", "CDSCO", "NMC"] }`

**BAA Parser Agent:**
- Celery task: `parse_baa_task` (hipaa_check_queue)
- Tool: GPT-4o (temperature=0, structured JSON)
- Input: BAA document text from Supabase Storage
- Workflow:
  1. Idempotency check
  2. Chunk BAA into 500-token chunks
  3. Check for 6 mandatory HIPAA clauses:
     - Breach notification within 60 days
     - Encryption of ePHI at rest and in transit
     - Subprocessor obligation clause
     - PHI return/destruction on termination
     - Audit rights clause
     - Minimum necessary use clause
  4. Self-consistency: run 3 times, compare clause detection
  5. For each clause: `{ present: boolean, exact_quote, confidence }`
  6. Calculate overall confidence: (clauses_present / 6)
  7. If incomplete → publish `baa_revision_request_task` to notify vendor
  8. Store in `baa_records` table
- Output: `{ result: "BAA_COMPLETE"|"BAA_INCOMPLETE", confidence_score, clauses_present: [], clauses_missing: [], expiry_date }`
- OpenTelemetry span: `baa_parser`

**HIPAA Attestation Validator Agent:**
- Celery task: `validate_hipaa_attestation_task` (hipaa_check_queue)
- Tool: GPT-4o (temperature=0, structured JSON)
- Input: HIPAA attestation document text
- Workflow:
  1. Idempotency check
  2. Extract: year, signatory name, title, safeguards covered
  3. Grounding: require exact quotes for each field
  4. Verify signatory has authority (cross-check with MCA directors)
  5. Calculate confidence score
  6. Store in `hipaa_verifications`
- Output: `{ result: "valid"|"invalid", confidence_score, year, signatory, safeguards: [] }`

**ePHI Data Flow Analyzer Agent:**
- Celery task: `analyze_ephi_flow_task` (hipaa_check_queue)
- Tool: GPT-4o Vision (temperature=0, structured JSON)
- Input: ePHI Data Flow Map image/diagram from Supabase Storage
- Workflow:
  1. Idempotency check
  2. Analyze diagram with GPT-4o Vision
  3. Check: encryption at rest, encryption in transit, data jurisdiction, unprotected paths
  4. Identify risks: data leaving jurisdiction, unencrypted segments, third-party access points
  5. Calculate confidence score
  6. Store in `hipaa_verifications`
- Output: `{ result: "compliant"|"non_compliant", confidence_score, risks: [], encryption_verified, jurisdiction_verified }`
- OpenTelemetry span: `ephi_flow_analysis`

**Subprocessor Coverage Agent:**
- Celery task: `check_subprocessor_coverage_task` (hipaa_check_queue)
- Tool: GPT-4o (temperature=0, structured JSON)
- Input: Subprocessor list document, BAA clauses (from BAA Parser)
- Workflow:
  1. Idempotency check
  2. Parse subprocessor list
  3. For each subprocessor: check HIPAA eligibility
  4. Cross-check: are all subprocessors covered in BAA subprocessor clause?
  5. Identify gaps: subprocessors not covered in BAA
  6. Calculate confidence score
  7. Store in `hipaa_verifications`
- Output: `{ result: "all_covered"|"gaps_found", confidence_score, subprocessors: [], gaps: [] }`

### Parallel Execution Strategy

**Worker-1 Queue Assignment:**
- `verification_queue` - Standard checks (GST, PAN, bank, MCA, sanctions, SOC 2)
- `hipaa_check_queue` - HIPAA checks (OIG, BAA, attestation, ePHI flow, subprocessors)

**Worker-2 Queue Assignment:**
- `verification_queue` - Standard checks (parallel with worker-1)
- `embedding_queue` - Document embeddings
- `notification_queue` - Email notifications

**Execution Flow:**
1. When all documents submitted → publish tasks to BOTH queues simultaneously
2. Worker-1 picks from `verification_queue` AND `hipaa_check_queue`
3. Worker-2 picks from `verification_queue` (different tasks than worker-1)
4. Both workers process tasks in parallel
5. Idempotency ensures no duplicate processing if task retried

### Frontend Integration for Verification Status

**Real-Time Status Updates:**
- SSE endpoint: `GET /api/v1/vendors/{id}/events`
- Events emitted:
  - `verification_started` - `{ agent: "GST Verification", status: "in_progress" }`
  - `verification_complete` - `{ agent: "GST Verification", status: "success", confidence: 0.95 }`
  - `verification_failed` - `{ agent: "OIG Check", status: "failed", reason: "Excluded party found" }`
  - `hipaa_check_started` - `{ agent: "BAA Parser", status: "in_progress" }`
  - `hipaa_check_complete` - `{ agent: "BAA Parser", status: "success", result: "BAA_COMPLETE" }`

**Status Page Updates:**
- `VendorDetailPage.tsx` listens to SSE
- Display verification progress:
  - Standard Checks: 5/5 complete (GST ✓, PAN ✓, Bank ✓, MCA ✓, Sanctions ✓)
  - HIPAA Checks: 5/5 complete (OIG ✓, BAA ✓, Attestation ✓, ePHI Flow ✓, Subprocessors ✓)
- Show confidence scores per check
- Highlight failures in red with reason

## Implementation Checklist

### Intake Agents
- [ ] Implement SaaS intake endpoint with JWT validation
- [ ] Implement Healthcare intake endpoint with ePHI gate logic
- [ ] Create ePHI gate decision node in LangGraph supervisor
- [ ] Implement notification tasks for procurement and compliance officer
- [ ] Update frontend IntakePage with Healthcare option and ePHI checkbox

### Invitation Agents
- [ ] Implement SaaS invitation endpoint with 7-day token
- [ ] Implement Healthcare invitation endpoint with 10-day token
- [ ] Create SendGrid email templates (SaaS and Healthcare)
- [ ] Generate pre-filled BAA template for Healthcare invitations
- [ ] Implement token validation endpoint

### Document Collection
- [ ] Implement SaaS document upload endpoint (8 documents)
- [ ] Implement Healthcare document upload endpoint (11 documents)
- [ ] Set up Supabase Storage bucket for BAA and ePHI flow maps (encrypted, 6-year retention)
- [ ] Implement document classification agent with GPT-4o
- [ ] Implement document embedding agent with OpenAI embeddings
- [ ] Create document checklist tracker (Celery beat task)
- [ ] Implement reminder email task for incomplete submissions
- [ ] Build SaaS vendor portal frontend (multi-step form)
- [ ] Build Healthcare vendor portal frontend (11-doc checklist)

### Standard Verification Agents
- [ ] Implement GST verification agent (Signzy/IDfy)
- [ ] Implement PAN verification agent (Surepass)
- [ ] Implement bank validation agent (Decentro penny drop)
- [ ] Implement MCA verification agent (Karza/Signzy)
- [ ] Implement sanctions check agent (ComplyAdvantage)
- [ ] Implement SOC 2 parser agent (GPT-4o with self-consistency)
- [ ] Add idempotency checks to all agents
- [ ] Add OpenTelemetry spans to all agents

### Healthcare Verification Agents
- [ ] Implement OIG exclusion check agent with auto-reject logic
- [ ] Implement extended sanctions check (CDSCO, NMC)
- [ ] Implement BAA parser agent (6 mandatory clauses)
- [ ] Implement HIPAA attestation validator agent
- [ ] Implement ePHI data flow analyzer agent (GPT-4o Vision)
- [ ] Implement subprocessor coverage agent
- [ ] Add idempotency checks to all HIPAA agents
- [ ] Add OpenTelemetry spans with `hipaa_check` tag

### Parallel Execution
- [ ] Configure worker-1 to pick from verification_queue and hipaa_check_queue
- [ ] Configure worker-2 to pick from verification_queue, embedding_queue, notification_queue
- [ ] Test parallel execution (submit 5 vendors, verify both workers active)
- [ ] Verify idempotency (retry failed task, ensure no duplicate processing)

### Frontend Integration
- [ ] Implement SSE connection for real-time verification updates
- [ ] Update VendorDetailPage to show verification progress
- [ ] Display confidence scores per verification check
- [ ] Highlight HIPAA checks separately for Healthcare vendors
- [ ] Show auto-reject reason if OIG exclusion found
- [ ] Add BAA clause checklist visualization (6 clauses)

## Success Criteria
- Employee can submit vendor request with ePHI gate selection
- ePHI gate correctly routes to Healthcare or SaaS workflow
- Vendor receives appropriate invitation email (8-doc or 11-doc checklist)
- Vendor portal validates token and shows correct document checklist
- Documents are uploaded, classified, and embedded automatically
- All 6 standard verification agents run in parallel
- All 6 Healthcare verification agents run in parallel (for Healthcare vendors)
- Worker-1 and worker-2 process tasks simultaneously
- OIG exclusion triggers immediate auto-reject
- BAA parser detects all 6 mandatory clauses
- ePHI flow analyzer identifies risks in data flow diagrams
- Frontend shows real-time verification progress via SSE
- Confidence scores displayed for each verification check
- Idempotency prevents duplicate API calls on task retry

## Next Phase Preview
Phase 3 will implement the ML-powered risk assessment layer, including Bayesian risk scoring (with 2x weight for HIPAA checks), Reinforcement Learning risk model, continual learning module, and federated learning for cross-organization pattern sharing. This phase also includes the multi-step approval workflow (3-step for SaaS, 4-step for Healthcare with Compliance Officer).
