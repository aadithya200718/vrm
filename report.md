# OPUS Vendor Risk Management System - Code Analysis Report

## System Overview

OPUS is a multi-agent autonomous vendor risk assessment platform built with FastAPI, LangGraph, and LangChain. The system processes vendor documents, performs security/compliance/financial reviews, and coordinates evidence collection through specialized AI agents.

---

## Architecture Components

### Core Infrastructure Files

#### backend/app/main.py
**Purpose**: FastAPI application entry point and server configuration

**How it works**:
- Initializes structured logging with structlog
- Sets up FastAPI application with CORS middleware
- Configures Prometheus metrics instrumentation for monitoring
- Creates upload directory for vendor documents
- Initializes Qdrant vector database collections on startup
- Includes all API routes from routes.py
- Provides root endpoint with system information

#### backend/app/config.py
**Purpose**: Centralized configuration management using Pydantic

**How it works**:
- Loads environment variables from .env file
- Manages credentials for Supabase (database), Ollama/Groq (LLM), Redis (state), Qdrant (vector store)
- Configures Mailtrap for email delivery
- Provides singleton pattern via @lru_cache for settings access
- Supports both development and production environments

---

## Database Layer (backend/app/core/)

#### backend/app/core/db.py
**Purpose**: Supabase database client and all database operations

**How it works**:
- Creates singleton Supabase client for connection pooling
- Provides CRUD operations for:
  - **Vendors**: create, get, update vendor records
  - **Documents**: create, get, update, check duplicates
  - **Security Reviews**: create, get, update security assessment records
  - **Compliance Reviews**: create, get, update compliance assessment records
  - **Financial Reviews**: create, get, update financial assessment records
  - **Evidence Requests**: create, get, update missing document requests
  - **Evidence Tracking**: log evidence collection actions
  - **Audit Logs**: comprehensive audit trail of all agent actions
  - **Policies**: store and retrieve internal policy documents
  - **Breaches**: search historical breach data
- Handles file uploads to Supabase Storage
- Provides health check functionality

#### backend/app/core/redis_state.py
**Purpose**: Redis-backed state management for active workflows

**How it works**:
- Creates singleton Redis client
- Stores active vendor review state with 7-day TTL
- Provides functions to save/load/delete/update state
- Tracks current phase, agent, progress percentage
- Maintains message history and error log
- Enables workflow resumption after failures
- Provides health check functionality

#### backend/app/core/state.py
**Purpose**: Pydantic models for LangGraph shared state schema

**How it works**:
- Defines VendorReviewState as the single source of truth
- Contains vendor information, documents, review results, evidence gaps
- Tracks workflow control (current phase, agent, progress)
- Maintains audit trail and error log
- Provides serialization helpers for Redis/database storage
- Uses Pydantic for type safety and validation

#### backend/app/core/vector.py
**Purpose**: Qdrant vector store with Sentence Transformers for RAG

**How it works**:
- Creates singleton Qdrant client and SentenceTransformer embedder
- Uses "all-MiniLM-L6-v2" model for 384-dimensional embeddings
- Manages three collections: security_policies, compliance_policies, financial_policies
- Provides functions to:
  - Initialize collections on startup
  - Generate embeddings for text
  - Upsert policy documents with metadata
  - Perform semantic search with score threshold
  - Filter by category
- Enables agents to search internal policies using natural language

#### backend/app/core/llm.py
**Purpose**: LLM configuration with Ollama primary and Groq fallback

**How it works**:
- Creates singleton LLM instance with automatic fallback
- Primary: ChatOllama (local, free, llama3.1:8b)
- Fallback: ChatGroq (cloud, free tier, llama-3.1-70b-versatile)
- Configures temperature=0 for deterministic outputs
- Sets max tokens to 4096
- Provides health check for both services
- Automatically switches to Groq if Ollama fails

---

## Tool Layer (backend/app/tools/)

### backend/app/tools/base.py
**Purpose**: Base tool framework with standardized interface

**How it works**:
- Provides ToolRegistry class for centralized tool registration
- Implements @traced_tool decorator for:
  - Timing measurement
  - Structured logging
  - Audit trail creation
  - Error handling
- Implements @with_retry decorator using tenacity for automatic retries
- Ensures all tool calls are logged to audit_logs table
- Captures input/output data, duration, and errors

### backend/app/tools/intake_tools.py
**Purpose**: 8 tools for document parsing, classification, and extraction

**Tools**:
1. **parse_pdf**: Extracts text and tables from PDF using pdfplumber
2. **parse_docx**: Extracts text and tables from Word documents
3. **parse_excel**: Extracts data from all Excel sheets with pandas
4. **classify_document**: Uses LLM to classify into categories (SOC2, ISO27001, Insurance, DPA, Financial_Statements, BCP, Pen_Test_Report, Security_Questionnaire, Privacy_Policy, Other)
5. **extract_vendor_metadata**: Uses LLM to extract company name, address, contacts, industry
6. **extract_dates**: Uses regex + LLM to find expiration, effective, issue dates
7. **store_document_metadata**: Saves processed document to database with deduplication
8. **ocr_scan**: Performs OCR on images using EasyOCR for scanned documents

**How it works**:
- Each tool is decorated with @tool for LangChain integration
- Returns JSON strings for structured output
- Handles errors gracefully with status/error fields
- Limits text extraction to prevent token overflow
- Uses LLM for intelligent extraction when needed

### backend/app/tools/compliance_tools.py
**Purpose**: 10 tools for regulatory compliance assessment

**Tools**:
1. **search_compliance_policies**: RAG search against internal compliance policies
2. **check_gdpr_compliance**: Verifies GDPR requirements (DPO, data subject rights, breach notification, etc.)
3. **check_hipaa_compliance**: Verifies HIPAA requirements (BAA, PHI handling, safeguards)
4. **check_pci_compliance**: Verifies PCI-DSS requirements (12 requirements)
5. **verify_data_processing_agreement**: Validates DPA for GDPR Article 28 clauses
6. **assess_data_retention_policy**: Checks retention periods, deletion procedures
7. **check_subprocessor_list**: Analyzes subprocessor disclosures and flags high-risk jurisdictions
8. **validate_privacy_policy**: Checks privacy policy completeness (10 criteria)
9. **calculate_compliance_score**: Computes weighted score (GDPR 30%, HIPAA 20%, PCI 15%, DPA 20%, Privacy 15%)
10. **generate_compliance_report**: Compiles findings into comprehensive report with LLM-generated executive summary

**How it works**:
- Uses LLM to analyze document text against regulatory requirements
- Returns structured JSON with scores, status, gaps, recommendations
- Adapts assessment based on vendor type and data handling
- Provides detailed compliance checks for each regulation

### backend/app/tools/financial_tools.py
**Purpose**: 9 tools for financial risk assessment

**Tools**:
1. **search_financial_policies**: RAG search against internal financial policies
2. **verify_insurance_coverage**: Validates insurance certificate adequacy based on contract value
3. **check_insurance_expiry**: Checks if insurance is expired or expiring soon
4. **get_credit_rating**: Gets credit rating (mock mode or OpenCorporates API)
5. **analyze_financial_statements**: Assesses financial health from balance sheets, P&L
6. **check_bankruptcy_records**: Searches for bankruptcy filings (mock mode or PACER integration)
7. **verify_business_continuity_plan**: Assesses BCP/DR documentation (RTO/RPO, backup procedures)
8. **calculate_financial_risk_score**: Computes weighted score (Insurance 35%, Credit 30%, Stability 25%, BCP 10%)
9. **generate_financial_report**: Compiles findings into comprehensive report

**How it works**:
- Determines minimum insurance requirements based on contract value
- Uses mock data for credit/bankruptcy in development mode
- Supports OpenCorporates API integration for production
- Analyzes financial statements using LLM
- Provides risk levels: low, medium, high, critical

### backend/app/tools/security_tools.py
**Purpose**: 10 tools for comprehensive security assessment

**Tools**:
1. **search_security_policies**: RAG search against internal security policies
2. **validate_soc2_certificate**: Validates SOC2 report (Type 1/2, auditor, opinion)
3. **validate_iso27001_certificate**: Validates ISO 27001 certificate (certification body, scope, dates)
4. **check_certificate_expiry**: Checks if certificates are expired or expiring within 90 days
5. **scan_domain_security**: Scans SSL/TLS and security headers (HSTS, CSP, X-Frame-Options, etc.)
6. **check_breach_history**: Searches internal database and HaveIBeenPwned API
7. **analyze_security_questionnaire**: Uses LLM to score questionnaire responses (8 areas)
8. **calculate_security_score**: Computes weighted score (Certificates 40%, Domain 30%, Breaches 20%, Questionnaire 10%)
9. **generate_security_report**: Compiles findings into comprehensive report
10. **flag_critical_issues**: Identifies blocking issues (expired certs, active breaches, no encryption)

**How it works**:
- Validates certificates by extracting key details with LLM
- Performs live SSL/TLS scans using Python ssl module
- Checks security headers via HTTP requests
- Searches breach databases for vendor history
- Flags critical issues that would block approval

### backend/app/tools/evidence_tools.py
**Purpose**: 8 tools for evidence gap analysis and collection

**Tools**:
1. **get_required_documents**: Determines required documents by vendor type and contract value
2. **compare_required_vs_submitted**: Gap analysis comparing required vs submitted documents
3. **generate_evidence_request_email**: Uses LLM to generate professional request email
4. **send_email**: Sends email via Mailtrap API
5. **create_followup_task**: Creates internal follow-up task for procurement team
6. **track_document_status**: Tracks status of all evidence requests
7. **send_reminder_email**: Generates and sends polite reminder for outstanding documents
8. **update_evidence_log**: Logs evidence tracking actions to database

**How it works**:
- Defines document requirements by vendor type (technology, healthcare, financial)
- Adds high-value requirements for contracts > $100K
- Compares submitted documents against requirements
- Generates professional emails using LLM
- Sends emails via Mailtrap API (or logs in mock mode)
- Tracks evidence requests in database with status (pending, received, reviewed)

### backend/app/tools/supervisor_tools.py
**Purpose**: 6 tools for orchestrating multi-agent workflow

**Tools**:
1. **delegate_to_security_agent**: Creates security review task and passes vendor context
2. **delegate_to_compliance_agent**: Creates compliance review task
3. **delegate_to_financial_agent**: Creates financial review task
4. **delegate_to_evidence_agent**: Creates evidence coordination task
5. **compile_approval_packet**: Aggregates all review findings into comprehensive packet
6. **get_worker_status**: Gets current status and progress from Redis state

**How it works**:
- Creates review records in database before delegation
- Passes vendor context and document data to agents
- Compiles aggregate scores from all reviews
- Calculates overall recommendation (APPROVE, CONDITIONAL_APPROVE, REJECT, PENDING_REVIEW)
- Checks Redis for active workflow state
- Provides progress tracking for frontend

---

## Agent Layer (backend/app/agents/)

### backend/app/agents/document_intake.py
**Purpose**: Autonomous document processing agent using ReAct pattern

**How it works**:
- Uses create_react_agent from LangGraph with 8 intake tools
- System prompt instructs agent to:
  1. Parse each document with appropriate parser
  2. Classify document into category
  3. Extract vendor metadata
  4. Extract important dates
  5. Store metadata in database
- Processes all files systematically
- Uses OCR as fallback if parsing fails
- Returns summary of processed documents with classifications
- Logs all actions to audit trail

### backend/app/agents/security_review.py
**Purpose**: Autonomous security assessment agent using ReAct pattern

**How it works**:
- Uses create_react_agent with 10 security tools
- System prompt defines assessment workflow:
  1. Search internal security policies
  2. Validate SOC2/ISO27001 certificates
  3. Check certificate expiry
  4. Scan domain security
  5. Check breach history
  6. Analyze security questionnaire
  7. Calculate security score
  8. Flag critical issues
  9. Generate security report
- Adapts assessment based on available documents
- Uses scoring guide: Certificates 40%, Domain 30%, Breaches 20%, Questionnaire 10%
- Provides clear recommendation with grade (A-F)
- Updates security_reviews table with results

### backend/app/agents/compliance_review.py
**Purpose**: Autonomous regulatory compliance assessment agent

**How it works**:
- Uses create_react_agent with 10 compliance tools
- System prompt defines assessment process:
  1. Search internal compliance policies
  2. Determine applicable regulations (GDPR always, HIPAA/PCI if relevant)
  3. Check applicable regulations
  4. Verify DPA, retention policy, subprocessors, privacy policy
  5. Calculate compliance score
  6. Generate compliance report
- Adapts depth based on data sensitivity
- Uses scoring: GDPR 30%, HIPAA 20%, PCI 15%, DPA 20%, Privacy 15%
- Provides grade and risk level
- Updates compliance_reviews table with results

### backend/app/agents/financial_review.py
**Purpose**: Autonomous financial risk assessment agent

**How it works**:
- Uses create_react_agent with 9 financial tools
- System prompt defines assessment process:
  1. Search internal financial policies
  2. Get credit rating
  3. Check bankruptcy records
  4. Analyze insurance coverage and expiry
  5. Analyze financial statements
  6. Verify business continuity plan
  7. Calculate financial risk score
  8. Generate financial report
- Adjusts requirements based on contract value
- Uses scoring: Insurance 35%, Credit 30%, Stability 25%, BCP 10%
- Flags red flags (credit < BB, active bankruptcy, missing statements)
- Updates financial_reviews table with results

### backend/app/agents/evidence_coordinator.py
**Purpose**: Autonomous evidence gap analysis and collection agent

**How it works**:
- Uses create_react_agent with 8 evidence tools
- System prompt defines workflow:
  1. Determine required documents by vendor type/contract value
  2. Compare required vs submitted documents
  3. Identify gaps
  4. Generate professional evidence request email
  5. Send email to vendor contact
  6. Create follow-up task for procurement team
  7. Update evidence log
- Prioritizes required > recommended > optional documents
- Sets deadlines based on criticality (7 days critical, 14 days standard)
- Handles missing contact email gracefully
- Tracks all actions in evidence_tracking table

### backend/app/agents/supervisor.py
**Purpose**: Orchestrates the entire multi-agent workflow

**How it works**:
- Uses create_react_agent with 6 supervisor tools
- System prompt defines workflow:
  1. Acknowledge vendor onboarding request
  2. Delegate to Security Agent (Phase 1)
  3. Check worker status
  4. Compile approval packet after reviews complete
  5. Present final recommendation
- In Phase 2: Delegates to Compliance, Financial, and Evidence agents
- Monitors progress via Redis state
- Handles errors gracefully
- Updates vendor status to "review_completed"
- Provides final recommendation

### backend/app/agents/graph.py
**Purpose**: LangGraph state machine for multi-agent orchestration

**How it works**:
- Defines GraphState TypedDict with all workflow state
- Builds state graph with nodes:
  - **intake_node**: Processes documents (10% progress)
  - **security_node**: Security review (35% progress)
  - **compliance_node**: Compliance review (parallel)
  - **financial_node**: Financial review (parallel)
  - **supervisor_aggregate_node**: Aggregates parallel results (60% progress)
  - **evidence_node**: Evidence coordination (75% progress)
  - **supervisor_final_node**: Final compilation (90% progress)
- Uses conditional routing after intake (fan-out to parallel reviews)
- Fan-in after parallel reviews to supervisor aggregate
- Sequential flow: aggregate → evidence → final → END
- Saves state to Redis at each step
- Creates audit logs for all agent actions
- Handles errors and continues workflow
- Returns final report with all results

---

## API Layer (backend/app/api/)

### backend/app/api/routes.py
**Purpose**: REST API endpoints for vendor onboarding and status tracking

**Endpoints**:

**Vendor Onboarding**:
- `POST /api/v1/vendors/onboard`: Start vendor onboarding with file uploads
  - Accepts vendor details and documents
  - Creates vendor record in database
  - Saves uploaded files to disk
  - Triggers multi-agent workflow in background
  - Returns vendor_id and status URLs

**Status Tracking**:
- `GET /api/v1/vendors/{vendor_id}/status`: Get current workflow status
  - Returns current phase, agent, progress percentage
  - Checks Redis for active state
  - Returns errors if any

- `GET /api/v1/vendors/{vendor_id}/report`: Get complete assessment report
  - Returns vendor info, documents, all review results
  - Includes evidence gaps and audit trail
  - Provides comprehensive findings

**Document Management**:
- `POST /api/v1/vendors/{vendor_id}/documents`: Upload additional documents
  - Saves files and triggers re-processing
  - Runs intake agent in background

- `GET /api/v1/vendors/{vendor_id}/documents`: List all vendor documents
  - Returns classifications and metadata

**Review Findings**:
- `GET /api/v1/vendors/{vendor_id}/security`: Get security findings
- `GET /api/v1/vendors/{vendor_id}/compliance`: Get compliance findings
- `GET /api/v1/vendors/{vendor_id}/financial`: Get financial findings

**Evidence Coordination**:
- `GET /api/v1/vendors/{vendor_id}/evidence-gaps`: List missing documents
- `POST /api/v1/vendors/{vendor_id}/request-evidence`: Trigger evidence request
- `GET /api/v1/vendors/{vendor_id}/evidence-status`: Track evidence collection
- `POST /api/v1/vendors/{vendor_id}/evidence/{doc_type}/received`: Mark document received

**Admin**:
- `POST /api/v1/policies/{policy_type}`: Upload policy document for RAG
- `GET /api/v1/policies`: List all policies
- `GET /api/v1/health`: System health check (database, Redis, Qdrant, LLM)

**How it works**:
- Uses FastAPI dependency injection
- Runs workflows in background tasks to avoid blocking
- Returns immediate response with status URLs
- Provides comprehensive error handling
- Logs all operations

---

## Agent Workflow (Detailed)

### Phase 1: Document Intake (10-20% progress)

1. **User uploads vendor documents** via POST /api/v1/vendors/onboard
2. **API creates vendor record** in database with status "processing"
3. **Files saved to disk** in uploads/{vendor_id}/ directory
4. **Background task starts** run_full_workflow()
5. **LangGraph invokes intake_node**:
   - Calls run_intake_agent() with vendor_id and file_paths
   - Agent receives task: "Process these files for vendor_id X"
   - Agent uses ReAct pattern to reason and act:
     - Determines file type from extension
     - Calls parse_pdf/parse_docx/parse_excel/ocr_scan
     - Calls classify_document with extracted text
     - Calls extract_vendor_metadata
     - Calls extract_dates
     - Calls store_document_metadata
   - Agent processes all files systematically
   - Returns summary of classifications
6. **State updated** in Redis: current_phase="intake_complete", progress=20%
7. **Audit logs created** for all tool calls

### Phase 2: Parallel Reviews (20-60% progress)

**After intake, graph fans out to 3 parallel agents:**

#### Security Review (security_node):
1. **LangGraph invokes security_node**
2. **Calls run_security_agent()** with vendor_id
3. **Agent receives context**: vendor info, document list, extracted texts
4. **Agent uses ReAct to execute workflow**:
   - Calls search_security_policies("security requirements")
   - If SOC2 document exists: calls validate_soc2_certificate(text)
   - If ISO27001 exists: calls validate_iso27001_certificate(text)
   - Calls check_certificate_expiry for each cert
   - If domain provided: calls scan_domain_security(domain)
   - Calls check_breach_history(company_name, domain)
   - If questionnaire exists: calls analyze_security_questionnaire(text)
   - Calls calculate_security_score(cert_score, domain_score, breach_score, quest_score)
   - Calls flag_critical_issues(findings_json)
   - Calls generate_security_report(vendor_name, score, grade, findings, recommendations)
5. **Agent returns** structured results with score, grade, findings
6. **Updates security_reviews table** with results
7. **State updated**: security_result={...}

#### Compliance Review (compliance_node):
1. **LangGraph invokes compliance_node** (parallel with security)
2. **Calls run_compliance_agent()** with vendor_id
3. **Agent receives context**: vendor info, documents, extracted texts
4. **Agent uses ReAct to execute workflow**:
   - Calls search_compliance_policies("compliance requirements")
   - Determines applicable regulations (GDPR always, HIPAA if healthcare, PCI if financial)
   - Calls check_gdpr_compliance(dpa_text, domain)
   - If healthcare: calls check_hipaa_compliance(baa_text)
   - If financial: calls check_pci_compliance(questionnaire_text)
   - Calls verify_data_processing_agreement(dpa_text)
   - Calls assess_data_retention_policy(policy_text)
   - Calls check_subprocessor_list(dpa_text)
   - Calls validate_privacy_policy(policy_text, domain)
   - Calls calculate_compliance_score(gdpr, hipaa, pci, dpa, privacy)
   - Calls generate_compliance_report(vendor_name, score, grade, findings, recommendations)
5. **Agent returns** structured results
6. **Updates compliance_reviews table**
7. **State updated**: compliance_result={...}

#### Financial Review (financial_node):
1. **LangGraph invokes financial_node** (parallel with security and compliance)
2. **Calls run_financial_agent()** with vendor_id
3. **Agent receives context**: vendor info, contract value, documents
4. **Agent uses ReAct to execute workflow**:
   - Calls search_financial_policies("financial requirements")
   - Calls get_credit_rating(company_name, location)
   - Calls check_bankruptcy_records(company_name)
   - If insurance cert exists: calls verify_insurance_coverage(cert_text, contract_value)
   - Calls check_insurance_expiry(expiry_date)
   - If financial statements exist: calls analyze_financial_statements(statement_text)
   - If BCP exists: calls verify_business_continuity_plan(bcp_text)
   - Calls calculate_financial_risk_score(insurance, credit, stability, bcp)
   - Calls generate_financial_report(vendor_name, score, grade, findings, recommendations)
5. **Agent returns** structured results
6. **Updates financial_reviews table**
7. **State updated**: financial_result={...}

**All three agents run in parallel, then fan-in to supervisor_aggregate_node**

### Phase 3: Supervisor Aggregation (60% progress)

1. **LangGraph invokes supervisor_aggregate_node**
2. **Gathers results** from security, compliance, financial agents
3. **Computes aggregate score**: average of all three scores
4. **Creates summary message**: "Parallel reviews complete. Security: X, Compliance: Y, Financial: Z"
5. **State updated**: current_phase="aggregated", progress=60%
6. **Audit log created**: "supervisor: aggregate_results"

### Phase 4: Evidence Coordination (60-75% progress)

1. **LangGraph invokes evidence_node**
2. **Calls run_evidence_coordinator()** with vendor_id
3. **Agent receives context**: vendor info, submitted documents, review results
4. **Agent uses ReAct to execute workflow**:
   - Calls get_required_documents(vendor_type, contract_value)
   - Calls compare_required_vs_submitted(vendor_id, required_docs_json)
   - For each missing document:
     - Creates evidence_request record in database
   - Calls generate_evidence_request_email(vendor_name, contact_name, missing_docs, deadline_days)
   - If contact_email exists: calls send_email(to_email, subject, body, vendor_id)
   - Calls create_followup_task(vendor_id, task_description, assigned_to, due_days)
   - Calls update_evidence_log(vendor_id, request_id, action, details)
5. **Agent returns** summary of gaps and actions taken
6. **State updated**: evidence_result={...}, progress=75%

### Phase 5: Final Compilation (75-100% progress)

1. **LangGraph invokes supervisor_final_node**
2. **Calls run_supervisor()** with vendor_id
3. **Supervisor agent**:
   - Calls compile_approval_packet(vendor_id)
   - Aggregates all findings:
     - Vendor info
     - Document classifications
     - Security review (score, grade, findings)
     - Compliance review (score, grade, findings)
     - Financial review (score, grade, findings)
     - Evidence gaps (total, pending, received)
     - Audit trail
   - Calculates aggregate score (average of security, compliance, financial)
   - Determines recommendation:
     - APPROVE: score >= 70 AND no required evidence pending
     - CONDITIONAL_APPROVE: score >= 50
     - REJECT: score < 50
     - PENDING_REVIEW: no scores available
4. **Updates vendor status** to "review_completed"
5. **State updated**: current_phase="done", progress=100%
6. **Returns final report** with all results

### Phase 6: User Retrieval

1. **User polls** GET /api/v1/vendors/{vendor_id}/status
   - Returns current_phase="done", progress=100%
2. **User fetches** GET /api/v1/vendors/{vendor_id}/report
   - Returns complete assessment report with:
     - Vendor details
     - Document classifications
     - Security findings (score, grade, critical issues)
     - Compliance findings (score, grade, gaps)
     - Financial findings (score, grade, red flags)
     - Evidence gaps (missing documents)
     - Audit trail (all agent actions)
     - Final recommendation (APPROVE/CONDITIONAL/REJECT)

---

## Key Design Patterns

### ReAct Pattern (Reason + Act)
- All agents use create_react_agent from LangGraph
- Agent receives task → reasons about what to do → calls tools → observes results → repeats
- Enables autonomous decision-making without hardcoded workflows
- Agents adapt based on available documents and findings

### Tool-Based Architecture
- Each agent has specialized tools for its domain
- Tools are decorated with @tool for LangChain integration
- Tools return structured JSON for parsing
- Base tool framework provides tracing, logging, retries

### State Management
- LangGraph manages shared state across all nodes
- Redis stores active workflow state for resumption
- Database stores persistent results
- State includes vendor info, documents, review results, evidence gaps, audit trail

### Parallel Execution
- Security, Compliance, Financial agents run in parallel
- Fan-out after intake, fan-in before evidence coordination
- Reduces total workflow time by ~60%

### Audit Trail
- Every tool call logged to audit_logs table
- Captures agent, action, tool, input, output, duration, status
- Enables debugging and compliance tracking

### RAG (Retrieval Augmented Generation)
- Internal policies stored in Qdrant vector database
- Agents search policies using semantic similarity
- Provides context-aware assessments based on organizational requirements

### Graceful Degradation
- LLM fallback: Ollama → Groq
- Missing documents handled gracefully
- Errors logged but workflow continues
- Mock data for external APIs in development

---

## Summary

OPUS is a sophisticated multi-agent system that autonomously processes vendor documents, performs comprehensive risk assessments across security/compliance/financial domains, and coordinates evidence collection. The system uses LangGraph for orchestration, LangChain for agent creation, and the ReAct pattern for autonomous decision-making. All agents work in parallel where possible, maintain comprehensive audit trails, and adapt their assessments based on available evidence.
