# OPUS Phase 1: Foundation & Core Infrastructure

## Objective
Build the foundational infrastructure, implement the Supervisor Agent, Document Intake Agent, and one complete review agent (Security) with full autonomous capabilities. Establish the multi-agent orchestration pattern and prove the autonomous decision-making works end-to-end.

--

## What to Build in Phase 1

### 1. Core Infrastructure Setup

**Backend Foundation:**
- FastAPI application with project structure
- PostgreSQL database with initial schema
- Redis for state management
- Environment configuration management
- Logging and error handling framework
- Health check endpoints

**Database Schema (Phase 1 Tables):**
- Supabase PostgreSQL setup
- vendors table
- documents table
- security_reviews table
- audit_logs table
- policies table (for security policies only)
- Supabase Storage for document files

**Vector Store Setup:**
- Qdrant instance (Docker deployment)
- Sentence Transformers embeddings (all-MiniLM-L6-v2, 384 dimensions)
- Security policy embeddings
- RAG search implementation
- Policy ingestion pipeline

**LLM Integration:**
- Ollama setup (primary LLM - llama3.1:8b)
- Groq API setup (fallback LLM - llama-3.1-70b-versatile)
- LangChain integration with fallback support
- LangGraph state machine foundation
- Token usage tracking

---

### 2. Shared State Management

**VendorReviewState Schema:**
Implement the shared state object that all agents will use:
- vendor_id
- vendor_name
- vendor_type
- contract_value
- submitted_documents
- classified_documents
- security_findings
- messages (agent communication history)
- current_phase
- errors

**State Persistence:**
- Redis for active state
- PostgreSQL for completed reviews
- State serialization/deserialization
- State recovery on failure

---

### 3. Tool Framework

**Tool Base Class:**
Create a standardized tool interface that all tools will follow:
- Tool name and description
- Input schema validation
- Output schema validation
- Error handling
- Logging and tracing
- Retry logic

**Tool Registry:**
- Central tool registration
- Tool discovery by agents
- Tool versioning
- Tool documentation generation

---

### 4. Document Intake Agent (Complete Implementation)

**Agent Definition:**
- LangGraph agent node
- Agent prompt engineering
- ReAct loop implementation
- Tool access configuration

**All 8 Tools Implemented:**

1. **parse_pdf**
   - Use pdfplumber (better extraction quality)
   - Extract text from all pages
   - Extract tables
   - Extract metadata
   - Handle encrypted PDFs
   - Error handling for corrupted files

2. **parse_docx**
   - Use python-docx
   - Extract text and formatting
   - Extract tables
   - Handle embedded objects

3. **parse_excel**
   - Use openpyxl or pandas
   - Extract data from all sheets
   - Handle formulas
   - Preserve data types

4. **classify_document**
   - LLM-powered classification
   - Prompt engineering for accuracy
   - Confidence scoring
   - Support for: SOC2, ISO27001, Insurance, DPA, Financial Statements, BCP, Pen Test Reports, Other

5. **extract_vendor_metadata**
   - LLM-powered extraction
   - Extract: company name, address, contact, industry, employee count
   - Structured output validation

6. **extract_dates**
   - Regex + LLM extraction
   - Find: expiration dates, effective dates, issue dates
   - Date normalization
   - Timezone handling

7. **store_document_metadata**
   - Database insertion
   - JSON metadata storage
   - File path management
   - Duplicate detection

8. **ocr_scan**
   - Use EasyOCR (better accuracy)
   - Image preprocessing
   - Text extraction
   - Multi-language support
   - Quality validation

**Agent Behavior:**
- Autonomous file processing
- Adaptive classification
- Error recovery
- Progress reporting

---

### 5. Supervisor Agent (Orchestrator)

**Agent Definition:**
- LangGraph supervisor node
- Routing logic
- Worker monitoring
- Result aggregation

**All 6 Tools Implemented:**

1. **delegate_to_security_agent**
   - Create security review task
   - Pass vendor context
   - Set timeout
   - Return task ID

2. **delegate_to_compliance_agent**
   - Placeholder for Phase 2
   - Returns "not implemented" message

3. **delegate_to_financial_agent**
   - Placeholder for Phase 2
   - Returns "not implemented" message

4. **delegate_to_evidence_agent**
   - Placeholder for Phase 2
   - Returns "not implemented" message

5. **compile_approval_packet**
   - Aggregate all findings
   - Generate summary document
   - Format for presentation

6. **get_worker_status**
   - Query agent state
   - Return progress percentage
   - Return current step
   - Return errors if any

**Supervisor Behavior:**
- Receives vendor onboarding request
- Delegates to Document Intake Agent
- Waits for completion
- Delegates to Security Review Agent (Phase 1)
- Monitors progress
- Handles errors and retries
- Compiles results

---

### 6. Security Review Agent (Complete Implementation)

**Agent Definition:**
- LangGraph agent node
- Security domain expertise in prompt
- ReAct loop for autonomous reasoning
- Tool access configuration

**All 10 Tools Implemented:**

1. **search_security_policies**
   - Vector search in Qdrant
   - Use Sentence Transformers embeddings (all-MiniLM-L6-v2)
   - Semantic similarity search
   - Return top 5 relevant policies
   - Include relevance scores

2. **validate_soc2_certificate**
   - Parse SOC2 report
   - Extract: type (Type 1/2), auditor, date range, opinion
   - Validate format
   - Check auditor reputation (basic list)

3. **validate_iso27001_certificate**
   - Parse ISO27001 certificate
   - Extract: certification body, scope, validity dates
   - Validate format
   - Check certification body legitimacy

4. **check_certificate_expiry**
   - Parse expiration date
   - Calculate days until expiry
   - Flag if expired
   - Flag if expiring within 90 days

5. **scan_domain_security**
   - SSL/TLS check (certificate validity, version, cipher)
   - Security headers check (HSTS, CSP, X-Frame-Options, etc.)
   - Basic vulnerability scan
   - Calculate security score

6. **check_breach_history**
   - Query internal breach database (built from public sources)
   - Search by company name and domain
   - Return breach count and details
   - Include severity and date
   - Fallback to HaveIBeenPwned API if needed

7. **analyze_security_questionnaire**
   - LLM-powered analysis
   - Score responses against best practices
   - Identify red flags
   - Generate recommendations

8. **calculate_security_score**
   - Weighted scoring algorithm
   - Factors: certificates (40%), domain security (30%), breach history (20%), questionnaire (10%)
   - Return score 0-100
   - Return grade (A-F)

9. **generate_security_report**
   - Compile all findings
   - Structured JSON output
   - Executive summary
   - Detailed findings
   - Recommendations

10. **flag_critical_issues**
    - Identify blockers
    - Severity classification
    - Impact assessment
    - Remediation suggestions

**Agent Behavior:**
- Autonomous security assessment
- Adapts to available evidence
- Handles missing documents gracefully
- Provides detailed reasoning
- Generates comprehensive report

---

### 7. LangGraph State Machine

**Graph Structure:**
```
START
  ↓
Supervisor Agent
  ↓
Document Intake Agent
  ↓
Supervisor Agent (routing decision)
  ↓
Security Review Agent
  ↓
Supervisor Agent (compile results)
  ↓
END
```

**Node Definitions:**
- supervisor_node: Supervisor Agent
- intake_node: Document Intake Agent
- security_node: Security Review Agent

**Edge Definitions:**
- START → supervisor_node
- supervisor_node → intake_node (conditional)
- intake_node → supervisor_node
- supervisor_node → security_node (conditional)
- security_node → supervisor_node
- supervisor_node → END (conditional)

**Conditional Logic:**
- Supervisor decides next step based on state
- Handles errors and retries
- Supports parallel execution (foundation for Phase 2)

---

### 8. API Endpoints (Phase 1)

**Vendor Onboarding:**
- POST /api/v1/vendors/onboard
  - Accept vendor name, type, contract value
  - Accept file uploads
  - Return vendor_id and status
  - Trigger agent workflow

- GET /api/v1/vendors/{vendor_id}/status
  - Return current phase
  - Return progress percentage
  - Return current agent
  - Return errors if any

- GET /api/v1/vendors/{vendor_id}/report
  - Return complete assessment
  - Include all findings
  - Include audit trail

**Document Management:**
- POST /api/v1/vendors/{vendor_id}/documents
  - Upload additional documents
  - Trigger re-processing

- GET /api/v1/vendors/{vendor_id}/documents
  - List all documents
  - Include classification
  - Include metadata

**Security Review:**
- GET /api/v1/vendors/{vendor_id}/security
  - Return security review findings
  - Include score and grade
  - Include recommendations

**Admin:**
- POST /api/v1/policies/security
  - Upload security policy document
  - Generate embeddings using Sentence Transformers
  - Store in Qdrant vector database

- GET /api/v1/health
  - System health check
  - Database connectivity
  - Redis connectivity
  - LLM API connectivity

---

### 9. Testing Framework

**Unit Tests:**
- Test each tool independently
- Mock external dependencies
- Validate input/output schemas
- Test error handling

**Integration Tests:**
- Test Document Intake Agent end-to-end
- Test Security Review Agent end-to-end
- Test Supervisor orchestration
- Test state management

**Agent Behavior Tests:**
- Test autonomous decision making
- Test adaptation to different scenarios
- Test error recovery
- Test reasoning quality

**Test Data:**
- Sample vendor documents (SOC2, insurance, etc.)
- Sample security policies
- Mock API responses
- Edge case scenarios

---

### 10. Observability

**Logging:**
- Agent reasoning traces
- Tool call logs with parameters
- State transitions
- Error logs with full context

**Metrics:**
- Agent execution time
- Tool call latency
- Success/failure rates
- LLM token usage

**Tracing:**
- Distributed tracing for agent workflows
- Tool call traces
- State change traces
- End-to-end request traces

**Dashboard:**
- Real-time agent status
- Active workflows
- Error rates
- Performance metrics

---

## Phase 1 Deliverables

### Working System Components:
1. ✅ FastAPI backend with core infrastructure
2. ✅ PostgreSQL database with Phase 1 schema
3. ✅ Redis state management
4. ✅ Vector store with security policies
5. ✅ Document Intake Agent (fully functional)
6. ✅ Security Review Agent (fully functional)
7. ✅ Supervisor Agent (orchestrating Phase 1 agents)
8. ✅ LangGraph state machine
9. ✅ API endpoints for vendor onboarding and status
10. ✅ Complete test suite
11. ✅ Observability and monitoring
12. ✅ Documentation

### Demonstrated Capabilities:
- ✅ Autonomous document processing
- ✅ Autonomous security assessment
- ✅ Multi-agent orchestration
- ✅ ReAct pattern in action
- ✅ Adaptive decision making
- ✅ Error handling and recovery
- ✅ Complete audit trail

### Example End-to-End Flow:
```
User uploads vendor documents
  ↓
Supervisor receives request
  ↓
Document Intake Agent processes files
  - Parses PDFs
  - Classifies documents
  - Extracts metadata
  - Stores in database
  ↓
Supervisor receives structured data
  ↓
Security Review Agent assesses security
  - Searches security policies
  - Validates SOC2 certificate
  - Scans domain security
  - Checks breach history
  - Calculates security score
  - Generates report
  ↓
Supervisor compiles results
  ↓
User receives security assessment report
```

---

## Success Criteria for Phase 1

### Functional Requirements:
- ✅ System can process vendor documents autonomously
- ✅ System can classify documents with >90% accuracy
- ✅ System can perform complete security assessment
- ✅ Agents demonstrate autonomous decision making
- ✅ System handles errors gracefully
- ✅ Complete audit trail is generated

### Performance Requirements:
- ✅ Document processing: < 2 minutes for 5 documents
- ✅ Security review: < 5 minutes
- ✅ End-to-end workflow: < 10 minutes
- ✅ API response time: < 500ms (excluding agent execution)

### Quality Requirements:
- ✅ Unit test coverage: > 80%
- ✅ Integration tests: All critical paths covered
- ✅ Agent reasoning: Clear and logical
- ✅ Error handling: No unhandled exceptions
- ✅ Documentation: Complete and accurate

---

## Phase 1 Timeline Estimate

**Week 1-2: Infrastructure**
- Backend setup
- Database schema
- Vector store setup
- LLM integration
- State management

**Week 3-4: Document Intake Agent**
- All 8 tools implementation
- Agent definition and prompt
- Testing and refinement

**Week 5-6: Security Review Agent**
- All 10 tools implementation
- Agent definition and prompt
- Testing and refinement

**Week 7: Supervisor Agent**
- Orchestration logic
- LangGraph state machine
- Integration testing

**Week 8: API & Testing**
- API endpoints
- End-to-end testing
- Performance testing
- Documentation

**Total: 8 weeks for Phase 1**

---

## Technical Decisions for Phase 1

### LLM Provider:
- Primary: Ollama (llama3.1:8b, self-hosted, free)
- Fallback: Groq (llama-3.1-70b-versatile, free tier)
- Temperature: 0 for consistent reasoning
- Max tokens: 4096 for agent responses
- Automatic fallback configuration

### Vector Store:
- Qdrant (self-hosted via Docker)
- Embedding model: Sentence Transformers (all-MiniLM-L6-v2)
- Index dimension: 384
- Collections: security_policies, compliance_policies, financial_policies

### Document Processing:
- PDF: pdfplumber (better extraction)
- DOCX: python-docx
- Excel: openpyxl + pandas
- OCR: EasyOCR (better accuracy)

### State Management:
- Active state: Redis (self-hosted) with JSON serialization
- Persistent state: Supabase PostgreSQL with JSONB columns
- State TTL: 7 days in Redis
- Document storage: Supabase Storage

### Deployment:
- Development: Docker Compose
- Production: Kubernetes (prepared for Phase 3)

---

## Risks and Mitigations

### Risk: LLM API rate limits
**Mitigation:** Implement exponential backoff, request queuing, and caching

### Risk: Document parsing failures
**Mitigation:** Multiple parsing libraries, fallback to OCR, manual review queue

### Risk: Agent reasoning quality
**Mitigation:** Extensive prompt engineering, few-shot examples, reflection pattern

### Risk: Performance issues
**Mitigation:** Async processing, caching, parallel execution where possible

### Risk: Cost overruns (LLM tokens)
**Mitigation:** Token usage monitoring, prompt optimization, caching strategies

---

## Next Steps After Phase 1

Once Phase 1 is complete and validated:
1. Review agent reasoning quality
2. Optimize prompts based on real usage
3. Gather performance metrics
4. Identify bottlenecks
5. Plan Phase 2 implementation (Compliance & Financial agents)

---

## Phase 1 Prompt for Claude Opus

**Use this prompt to build Phase 1:**

"Build a multi-agent vendor risk assessment system with autonomous decision-making capabilities. Implement the foundation with three agents: Supervisor Agent (orchestrator), Document Intake Agent (document processing), and Security Review Agent (security assessment).

Technology Stack:
- LLM: Ollama (llama3.1:8b) as primary with Groq (llama-3.1-70b-versatile) as fallback
- Agent Framework: LangGraph for orchestration, LangChain for tool integration
- Backend: FastAPI
- Database: Supabase (PostgreSQL) for persistence and file storage
- Cache: Redis (self-hosted) for state management
- Vector Store: Qdrant (self-hosted via Docker) for policy RAG search
- Embeddings: Sentence Transformers (all-MiniLM-L6-v2, 384 dimensions)
- Document Processing: pdfplumber for PDFs, python-docx for Word, EasyOCR for scanned documents

The Document Intake Agent needs 8 tools: parse_pdf (using pdfplumber), parse_docx, parse_excel, classify_document (using Ollama), extract_vendor_metadata (using Ollama), extract_dates, store_document_metadata (to Supabase), and ocr_scan (using EasyOCR). It should autonomously process uploaded documents, classify them, and extract structured data. Store files in Supabase Storage.

The Security Review Agent needs 10 tools: search_security_policies (Qdrant vector search with Sentence Transformers embeddings), validate_soc2_certificate, validate_iso27001_certificate, check_certificate_expiry, scan_domain_security (using SSL Labs API), check_breach_history (internal database + HaveIBeenPwned fallback), analyze_security_questionnaire, calculate_security_score, generate_security_report, and flag_critical_issues. It should autonomously assess vendor security posture using the ReAct pattern (Reason → Act → Observe → Repeat).

The Supervisor Agent needs 6 tools: delegate_to_security_agent, delegate_to_compliance_agent (placeholder), delegate_to_financial_agent (placeholder), delegate_to_evidence_agent (placeholder), compile_approval_packet, and get_worker_status. It should orchestrate the workflow, delegate tasks, monitor progress, and compile results.

Configure Ollama with automatic fallback to Groq:
```python
from langchain_community.llms import Ollama
from langchain_groq import ChatGroq

primary_llm = Ollama(model="llama3.1:8b", base_url="http://localhost:11434")
fallback_llm = ChatGroq(model="llama-3.1-70b-versatile", api_key=os.getenv("GROQ_API_KEY"))
llm = primary_llm.with_fallbacks([fallback_llm])
```

Set up Qdrant vector store with Sentence Transformers:
```python
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

qdrant = QdrantClient(url="http://localhost:6333")
embedder = SentenceTransformer('all-MiniLM-L6-v2')
```

Connect to Supabase for database and storage:
```python
from supabase import create_client
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
```

Implement the ReAct pattern for autonomous decision-making - agents should reason about what to do, call tools, observe results, and adapt their approach based on findings. No hardcoded if/else logic for agent behavior.

Create API endpoints for vendor onboarding, status checking, and report retrieval. Implement comprehensive logging, tracing, and monitoring. Include unit tests, integration tests, and agent behavior tests.

The system should demonstrate: autonomous document processing, autonomous security assessment, multi-agent orchestration, adaptive decision making, error handling, and complete audit trails.

Use Docker Compose for local development with Redis, Qdrant, Prometheus, and Grafana. Ensure Ollama is installed and llama3.1:8b model is pulled.

Provide complete implementation with all tools, agents, orchestration, API, tests, and documentation."
