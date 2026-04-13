# OPUS Phase 2: Compliance, Financial & Evidence Coordination

## Objective
Expand the system with Compliance Review Agent, Financial Review Agent, and Evidence Coordinator Agent. Implement parallel review execution, evidence gap analysis, and automated evidence requests. Build on Phase 1 foundation to create a comprehensive multi-domain assessment system.

---

## Prerequisites from Phase 1

**Must be complete before starting Phase 2:**
- ✅ Core infrastructure (FastAPI, Supabase PostgreSQL, Redis, Qdrant)
- ✅ Ollama + Groq fallback LLM setup
- ✅ Sentence Transformers embeddings
- ✅ Supervisor Agent working
- ✅ Document Intake Agent working
- ✅ Security Review Agent working
- ✅ LangGraph state machine foundation
- ✅ Shared state management
- ✅ Tool framework
- ✅ API endpoints
- ✅ Testing framework
- ✅ Observability

---

## What to Build in Phase 2

### 1. Database Schema Extensions

**New Tables (Supabase PostgreSQL):**
- compliance_reviews table
- financial_reviews table
- evidence_requests table
- evidence_tracking table
- compliance_policies table
- financial_policies table
- breaches table (internal breach database)

**Schema Updates:**
- Add compliance_findings to VendorReviewState
- Add financial_findings to VendorReviewState
- Add evidence_gaps to VendorReviewState
- Add evidence_requests_sent to VendorReviewState

---

### 2. Vector Store Extensions

**New Policy Indexes (Qdrant Collections):**
- Compliance policies collection (384 dimensions)
  - GDPR requirements
  - HIPAA requirements
  - PCI-DSS requirements
  - SOC2 compliance requirements
  - Industry-specific regulations

- Financial policies collection (384 dimensions)
  - Insurance requirements by contract value
  - Credit rating thresholds
  - Financial stability criteria
  - Business continuity requirements

**Embeddings:**
- Use Sentence Transformers (all-MiniLM-L6-v2)
- Generate embeddings locally (no API costs)
- Store in Qdrant with metadata

**Policy Ingestion:**
- Compliance policy loader
- Financial policy loader
- Embedding generation
- Index management

---

### 3. Compliance Review Agent (Complete Implementation)

**Agent Definition:**
- LangGraph agent node
- Compliance domain expertise in prompt
- ReAct loop for autonomous reasoning
- Tool access configuration

**All 10 Tools Implemented:**

1. **search_compliance_policies**
   - Vector search in Qdrant compliance policies collection
   - Use Sentence Transformers embeddings
   - Query by vendor type, data handling, industry
   - Return relevant regulations
   - Include applicability reasoning

2. **check_gdpr_compliance**
   - Verify GDPR requirements
   - Check: EU data center, DPO appointment, data subject rights, breach notification
   - Parse vendor documentation
   - LLM-powered assessment
   - Return compliance status and gaps

3. **check_hipaa_compliance**
   - Verify HIPAA requirements
   - Check: BAA existence, PHI handling, security safeguards, breach procedures
   - Parse vendor documentation
   - LLM-powered assessment
   - Return compliance status and gaps

4. **check_pci_compliance**
   - Verify PCI-DSS requirements
   - Check: cardholder data handling, network security, access controls
   - Parse vendor documentation
   - LLM-powered assessment
   - Return compliance status and gaps

5. **verify_data_processing_agreement**
   - Parse DPA document
   - Check for Article 28 GDPR clauses
   - Verify: purpose limitation, data security, subprocessor disclosure, audit rights
   - LLM-powered completeness check
   - Flag missing clauses

6. **assess_data_retention_policy**
   - Parse retention policy document
   - Check: retention periods, deletion procedures, data minimization
   - Compare against regulatory requirements
   - LLM-powered assessment
   - Return adequacy score

7. **check_subprocessor_list**
   - Extract subprocessor list from documents
   - Verify disclosure completeness
   - Check subprocessor locations
   - Flag high-risk jurisdictions
   - Return subprocessor analysis

8. **validate_privacy_policy**
   - Fetch privacy policy from vendor website
   - Parse and analyze content
   - Check: data collection disclosure, purpose specification, user rights, contact info
   - LLM-powered completeness check
   - Return compliance score

9. **calculate_compliance_score**
   - Weighted scoring algorithm
   - Factors: GDPR (30%), HIPAA (20%), PCI (15%), DPA (20%), Privacy Policy (15%)
   - Adjust weights based on vendor data handling
   - Return score 0-100
   - Return compliance grade

10. **generate_compliance_report**
    - Compile all compliance findings
    - Structured JSON output
    - Executive summary
    - Regulatory gap analysis
    - Required legal agreements
    - Recommendations

**Agent Behavior:**
- Determines applicable regulations based on vendor data handling
- Adapts assessment depth based on data sensitivity
- Handles missing legal agreements gracefully
- Provides detailed compliance reasoning
- Generates comprehensive report

---

### 4. Financial Review Agent (Complete Implementation)

**Agent Definition:**
- LangGraph agent node
- Financial domain expertise in prompt
- ReAct loop for autonomous reasoning
- Tool access configuration

**All 9 Tools Implemented:**

1. **search_financial_policies**
   - Vector search in Qdrant financial policies collection
   - Use Sentence Transformers embeddings
   - Query by contract value, vendor type
   - Return financial requirements
   - Include threshold reasoning

2. **verify_insurance_coverage**
   - Parse insurance certificate
   - Extract: coverage type, coverage amount, policy period
   - Compare against requirements
   - Check: general liability, professional liability, cyber insurance
   - Return adequacy assessment

3. **check_insurance_expiry**
   - Parse insurance policy dates
   - Calculate days until expiry
   - Flag if expired
   - Flag if expiring within 60 days
   - Return expiry status

4. **get_credit_rating**
   - Primary: Mock credit rating service (for development)
   - Secondary: OpenCorporates API (free, basic company info)
   - Query by company name and location
   - Extract: credit rating, risk score, company status
   - Handle API errors gracefully
   - Return credit assessment

5. **analyze_financial_statements**
   - Parse financial statement documents
   - Extract: revenue, profit, cash flow, assets, liabilities
   - LLM-powered financial health assessment
   - Calculate financial ratios
   - Return stability analysis

6. **check_bankruptcy_records**
   - Search public bankruptcy databases
   - Query by company name
   - Check federal and state records
   - Return bankruptcy history
   - Flag active proceedings

7. **verify_business_continuity_plan**
   - Parse BCP/DR document
   - Check: RTO/RPO definitions, backup procedures, disaster scenarios, testing schedule
   - LLM-powered adequacy assessment
   - Return BCP completeness score

8. **calculate_financial_risk_score**
   - Weighted scoring algorithm
   - Factors: insurance (35%), credit rating (30%), financial stability (25%), BCP (10%)
   - Adjust weights based on contract value
   - Return score 0-100
   - Return risk grade

9. **generate_financial_report**
   - Compile all financial findings
   - Structured JSON output
   - Executive summary
   - Insurance coverage summary
   - Financial stability assessment
   - Recommendations

**Agent Behavior:**
- Adapts requirements based on contract value
- Handles missing financial documents gracefully
- Considers vendor size and maturity
- Provides detailed financial reasoning
- Generates comprehensive report

---

### 5. Evidence Coordinator Agent (Complete Implementation)

**Agent Definition:**
- LangGraph agent node
- Evidence coordination expertise in prompt
- ReAct loop for autonomous reasoning
- Tool access configuration

**All 8 Tools Implemented:**

1. **get_required_documents**
   - Query requirements database
   - Filter by vendor type and contract value
   - Return list of required document types
   - Include requirement rationale
   - Prioritize by criticality

2. **compare_required_vs_submitted**
   - Compare required documents list with submitted documents
   - Identify missing documents
   - Identify incomplete documents
   - Identify expired documents
   - Return gap analysis

3. **generate_evidence_request_email**
   - LLM-powered email generation
   - Professional tone
   - Clear list of missing items
   - Explanation of why each is needed
   - Deadline specification
   - Contact information
   - Return formatted email

4. **send_email**
   - Integration with Mailgun API (5,000/month free)
   - Send email to vendor contact
   - Handle delivery failures
   - Track email status
   - Return send confirmation

5. **create_followup_task**
   - Integration with project management system (Jira, Asana, or internal)
   - Create task for internal team
   - Assign to procurement owner
   - Set due date
   - Include context and links
   - Return task ID

6. **track_document_status**
   - Query evidence tracking table
   - Return status for each requested document
   - Calculate completion percentage
   - Identify overdue items
   - Return tracking summary

7. **send_reminder_email**
   - LLM-powered reminder email generation
   - Polite but firm tone
   - List outstanding items
   - Emphasize urgency
   - Provide support contact
   - Return send confirmation

8. **update_evidence_log**
   - Update evidence tracking table
   - Record request sent date
   - Record response received date
   - Update document status
   - Log all interactions
   - Return update confirmation

**Agent Behavior:**
- Analyzes findings from all review agents
- Determines what evidence is missing
- Prioritizes critical vs nice-to-have documents
- Generates contextual evidence requests
- Tracks evidence collection progress
- Sends timely reminders
- Provides status updates

---

### 6. Supervisor Agent Extensions

**Updated Tools:**

1. **delegate_to_compliance_agent** (now fully implemented)
   - Create compliance review task
   - Pass vendor context and classified documents
   - Set timeout
   - Return task ID

2. **delegate_to_financial_agent** (now fully implemented)
   - Create financial review task
   - Pass vendor context and classified documents
   - Set timeout
   - Return task ID

3. **delegate_to_evidence_agent** (now fully implemented)
   - Create evidence coordination task
   - Pass all review findings
   - Set timeout
   - Return task ID

**Enhanced Orchestration:**
- Parallel execution of Security, Compliance, Financial agents
- Wait for all three to complete
- Aggregate results
- Delegate to Evidence Coordinator
- Handle partial failures gracefully

---

### 7. LangGraph State Machine Extensions

**Updated Graph Structure:**
```
START
  ↓
Supervisor Agent
  ↓
Document Intake Agent
  ↓
Supervisor Agent (routing decision)
  ↓
┌─────────────┴─────────────┐
│                           │
▼                           ▼
Security Agent    ┌─→ Compliance Agent
                  │
                  └─→ Financial Agent
                  
(All three run in parallel)
│                           │
└─────────────┬─────────────┘
              ↓
Supervisor Agent (aggregate results)
  ↓
Evidence Coordinator Agent
  ↓
Supervisor Agent (compile results)
  ↓
END
```

**New Node Definitions:**
- compliance_node: Compliance Review Agent
- financial_node: Financial Review Agent
- evidence_node: Evidence Coordinator Agent

**Parallel Execution:**
- Security, Compliance, Financial agents run simultaneously
- Use LangGraph parallel execution feature
- Wait for all to complete before proceeding
- Handle individual agent failures

**Enhanced Conditional Logic:**
- Supervisor decides which agents to invoke based on vendor type
- Skips agents if not applicable
- Handles missing data gracefully
- Retries failed agents

---

### 8. API Endpoints (Phase 2 Extensions)

**Compliance Review:**
- GET /api/v1/vendors/{vendor_id}/compliance
  - Return compliance review findings
  - Include score and grade
  - Include regulatory gaps
  - Include required agreements

**Financial Review:**
- GET /api/v1/vendors/{vendor_id}/financial
  - Return financial review findings
  - Include score and grade
  - Include insurance summary
  - Include credit rating

**Evidence Coordination:**
- GET /api/v1/vendors/{vendor_id}/evidence-gaps
  - List missing documents
  - Include criticality
  - Include request status

- POST /api/v1/vendors/{vendor_id}/request-evidence
  - Manually trigger evidence request
  - Specify custom message
  - Return confirmation

- GET /api/v1/vendors/{vendor_id}/evidence-status
  - Track evidence collection progress
  - Show completion percentage
  - List outstanding items

- POST /api/v1/vendors/{vendor_id}/evidence/{doc_type}/received
  - Mark document as received
  - Trigger re-processing
  - Update status

**Policy Management:**
- POST /api/v1/policies/compliance
  - Upload compliance policy document
  - Trigger embedding generation
  - Store in vector database

- POST /api/v1/policies/financial
  - Upload financial policy document
  - Trigger embedding generation
  - Store in vector database

- GET /api/v1/policies
  - List all policies
  - Filter by type
  - Include metadata

---

### 9. External Integrations

**Company Information APIs:**
- Mock credit rating service (primary, free)
- OpenCorporates API (secondary, free tier)
- Error handling and retries
- Rate limiting
- Response caching

**Mailgun API:**
- API key configuration (5,000 emails/month free)
- Email template management
- Delivery tracking
- Bounce handling
- Webhook support

**Breach Data:**
- Internal breach database (built from public sources)
- Query local PostgreSQL breaches table
- HaveIBeenPwned API as fallback (free, rate limited)
- No API costs for primary breach checks

**Security Scanning:**
- SSL Labs API (free, rate limited)
- SecurityHeaders.com (free)
- Mozilla Observatory (free)

**Optional Integrations:**
- Jira/Asana API for task management (if needed)

---

### 10. Email Templates

**Evidence Request Email:**
- Professional header
- Clear subject line
- Personalized greeting
- Context about the review
- Bulleted list of missing documents
- Explanation for each document
- Deadline
- Upload instructions
- Contact information
- Professional signature

**Reminder Email:**
- Polite reminder
- List of outstanding items
- Days remaining until deadline
- Offer to help
- Contact information

**Confirmation Email:**
- Thank you message
- Confirmation of received documents
- Next steps
- Timeline

---

### 11. Testing Extensions

**Unit Tests:**
- Test each new tool independently
- Mock external APIs (D&B, SendGrid)
- Validate input/output schemas
- Test error handling

**Integration Tests:**
- Test Compliance Agent end-to-end
- Test Financial Agent end-to-end
- Test Evidence Coordinator end-to-end
- Test parallel execution
- Test evidence request workflow

**Agent Behavior Tests:**
- Test compliance reasoning for different regulations
- Test financial assessment for different contract values
- Test evidence coordination for various gap scenarios
- Test adaptation to different vendor types

**End-to-End Tests:**
- Complete vendor review workflow
- Multiple vendor types (SaaS, Hardware, Consulting)
- Different contract values
- Various document combinations
- Missing document scenarios

---

### 12. Performance Optimization

**Parallel Execution:**
- Security, Compliance, Financial agents run simultaneously
- Measure speedup vs sequential execution
- Target: 3x faster than sequential

**Caching:**
- Cache policy search results
- Cache external API responses (credit ratings, breach data)
- Cache LLM responses for identical queries
- TTL configuration

**Async Processing:**
- Async tool execution where possible
- Async database queries
- Async external API calls
- Non-blocking email sending

---

## Phase 2 Deliverables

### Working System Components:
1. ✅ Compliance Review Agent (fully functional)
2. ✅ Financial Review Agent (fully functional)
3. ✅ Evidence Coordinator Agent (fully functional)
4. ✅ Enhanced Supervisor Agent with parallel execution
5. ✅ Extended LangGraph state machine
6. ✅ Compliance and financial policy vector stores
7. ✅ External API integrations (D&B, SendGrid)
8. ✅ Email templates and sending
9. ✅ Extended API endpoints
10. ✅ Complete test suite for Phase 2
11. ✅ Performance optimizations
12. ✅ Updated documentation

### Demonstrated Capabilities:
- ✅ Multi-domain assessment (Security, Compliance, Financial)
- ✅ Parallel agent execution
- ✅ Autonomous compliance reasoning
- ✅ Autonomous financial assessment
- ✅ Evidence gap analysis
- ✅ Automated evidence requests
- ✅ Email communication with vendors
- ✅ Task creation for internal team
- ✅ Evidence tracking
- ✅ Complete multi-agent workflow

### Example End-to-End Flow:
```
User uploads vendor documents
  ↓
Supervisor receives request
  ↓
Document Intake Agent processes files
  ↓
Supervisor delegates to 3 agents in parallel:
  ├─→ Security Agent assesses security
  ├─→ Compliance Agent checks regulations
  └─→ Financial Agent reviews financials
  ↓
All three agents complete and return reports
  ↓
Supervisor aggregates findings
  ↓
Evidence Coordinator identifies gaps
  - Missing: Penetration Test Report, DPA
  - Generates evidence request email
  - Sends email to vendor
  - Creates follow-up task for procurement
  ↓
Supervisor compiles results
  ↓
User receives comprehensive assessment with:
  - Security score: 87/100
  - Compliance score: 78/100
  - Financial score: 92/100
  - Evidence gaps: 2 items requested
  - Follow-up tasks: 1 created
```

---

## Success Criteria for Phase 2

### Functional Requirements:
- ✅ System performs multi-domain assessment autonomously
- ✅ Parallel execution works correctly
- ✅ Compliance agent handles multiple regulations
- ✅ Financial agent integrates with external APIs
- ✅ Evidence coordinator identifies gaps accurately
- ✅ Email requests are professional and clear
- ✅ Evidence tracking works correctly
- ✅ Complete audit trail includes all agents

### Performance Requirements:
- ✅ Parallel review execution: < 7 minutes (vs 15 minutes sequential)
- ✅ Evidence gap analysis: < 1 minute
- ✅ Email generation and sending: < 30 seconds
- ✅ End-to-end workflow: < 15 minutes

### Quality Requirements:
- ✅ Unit test coverage: > 80% for new code
- ✅ Integration tests: All critical paths covered
- ✅ Agent reasoning: Clear and logical across all domains
- ✅ Email quality: Professional and actionable
- ✅ Documentation: Complete and accurate

---

## Phase 2 Timeline Estimate

**Week 1-2: Compliance Review Agent**
- All 10 tools implementation
- Agent definition and prompt
- Testing and refinement

**Week 3-4: Financial Review Agent**
- All 9 tools implementation
- External API integrations (D&B)
- Agent definition and prompt
- Testing and refinement

**Week 5-6: Evidence Coordinator Agent**
- All 8 tools implementation
- Email template design
- SendGrid integration
- Agent definition and prompt
- Testing and refinement

**Week 7: Parallel Execution & Integration**
- LangGraph parallel execution
- Supervisor enhancements
- End-to-end integration
- Performance optimization

**Week 8: Testing & Documentation**
- Comprehensive testing
- Performance testing
- Documentation updates
- Bug fixes

**Total: 8 weeks for Phase 2**

---

## Technical Decisions for Phase 2

### External APIs:
- Credit ratings: Mock service (free) + OpenCorporates (free)
- Email: Mailgun (5,000/month free)
- Breach data: Internal database (free) + HaveIBeenPwned fallback (free)

### Email Service:
- Production: Mailgun (5,000/month free tier)
- Development: Gmail SMTP or email logging
- Retry logic: 3 attempts with exponential backoff

### Parallel Execution:
- LangGraph built-in parallel execution
- Timeout per agent: 10 minutes
- Failure handling: Continue with partial results

### Caching Strategy (Redis):
- Policy searches: 1 hour TTL
- Credit ratings: 24 hour TTL
- Breach data: 7 day TTL
- Ollama responses: 1 hour TTL (for identical queries)
- External API responses: 24 hour TTL

---

## Risks and Mitigations

### Risk: External API failures (OpenCorporates, Mailgun)
**Mitigation:** Graceful degradation, mock responses, retry logic, fallback to internal data

### Risk: Parallel execution complexity
**Mitigation:** Thorough testing, timeout handling, partial result handling

### Risk: Email deliverability issues
**Mitigation:** SendGrid reputation management, SPF/DKIM setup, bounce handling

### Risk: Compliance reasoning accuracy
**Mitigation:** Extensive prompt engineering, legal review of outputs, human-in-the-loop option

### Risk: Performance degradation with parallel execution
**Mitigation:** Resource monitoring, rate limiting, queue management

---

## Next Steps After Phase 2

Once Phase 2 is complete and validated:
1. Review multi-agent coordination quality
2. Optimize parallel execution performance
3. Validate compliance reasoning with legal team
4. Gather user feedback on evidence requests
5. Plan Phase 3 implementation (Risk Assessment & Approval Orchestration)

---

## Phase 2 Prompt for Claude Opus

**Use this prompt to build Phase 2:**

"Extend the multi-agent vendor risk assessment system with three additional agents: Compliance Review Agent, Financial Review Agent, and Evidence Coordinator Agent. Implement parallel execution for Security, Compliance, and Financial reviews.

Technology Stack (Phase 2 Extensions):
- LLM: Continue using Ollama (llama3.1:8b) with Groq fallback
- Vector Store: Extend Qdrant with compliance and financial policy collections
- Embeddings: Sentence Transformers (all-MiniLM-L6-v2) for all policy embeddings
- Email: Mailgun API (5,000/month free tier)
- Company Info: Mock service + OpenCorporates API (free)
- Breach Data: Internal PostgreSQL database + HaveIBeenPwned fallback

The Compliance Review Agent needs 10 tools: search_compliance_policies (Qdrant vector search), check_gdpr_compliance, check_hipaa_compliance, check_pci_compliance, verify_data_processing_agreement, assess_data_retention_policy, check_subprocessor_list, validate_privacy_policy, calculate_compliance_score, and generate_compliance_report. It should autonomously determine applicable regulations and assess compliance.

The Financial Review Agent needs 9 tools: search_financial_policies (Qdrant vector search), verify_insurance_coverage, check_insurance_expiry, get_credit_rating (mock service + OpenCorporates API), analyze_financial_statements, check_bankruptcy_records, verify_business_continuity_plan, calculate_financial_risk_score, and generate_financial_report. It should autonomously assess financial stability and insurance adequacy.

The Evidence Coordinator Agent needs 8 tools: get_required_documents, compare_required_vs_submitted, generate_evidence_request_email, send_email (Mailgun API), create_followup_task, track_document_status, send_reminder_email, and update_evidence_log. It should autonomously identify evidence gaps and coordinate collection.

Update the Supervisor Agent to execute Security, Compliance, and Financial agents in parallel using LangGraph parallel execution. After all three complete, delegate to Evidence Coordinator to identify gaps and send requests.

Extend the Supabase database schema with compliance_reviews, financial_reviews, evidence_requests, evidence_tracking, and breaches tables. Create new Qdrant collections for compliance and financial policies with Sentence Transformers embeddings (384 dimensions).

Implement professional email templates for evidence requests and reminders. Integrate with Mailgun for email delivery (5,000/month free). Use mock credit rating service for development with OpenCorporates API as secondary source.

Create API endpoints for compliance review, financial review, evidence gaps, evidence requests, and evidence tracking.

All agents should use the ReAct pattern for autonomous decision-making. Agents should adapt their assessment depth based on vendor type, contract value, and data sensitivity.

Include comprehensive testing for parallel execution, external API integrations, and evidence coordination workflows. Implement caching for policy searches and external API responses.

Provide complete implementation with all tools, agents, parallel orchestration, external integrations, API endpoints, tests, and documentation."
