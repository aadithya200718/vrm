# Phase 1: Foundation & Infrastructure Setup

## Objective
Establish the complete backend infrastructure, database architecture, authentication system, and frontend-backend integration layer for both Healthcare (HIPAA-compliant) and IT SaaS vendor onboarding workflows.

## Context
You're building a dual-workflow vendor onboarding system that handles both standard IT/SaaS vendors and HIPAA-compliant healthcare vendors. The system uses an event-driven architecture with LangGraph orchestration, FastAPI backend, React frontend, Supabase database, and Celery workers for async processing.

## Backend Architecture Requirements

### Project Structure (MVC Pattern)
Initialize FastAPI project with clean separation:
- `/api` - REST endpoint handlers (Views layer)
- `/agents` - LangGraph agent logic per workflow (Controllers)
- `/models` - Pydantic schemas and database models
- `/tools` - External API integrations (Signzy, Surepass, Decentro, OIG, ComplyAdvantage)
- `/tasks` - Celery task definitions for async processing
- `/learning` - ML components (RL model, Bayesian scorer, continual learner, federated client)
- `/rag` - LangChain RAG implementation with pgvector
- `/compliance` - HIPAA-specific checks (BAA parser, ePHI analyzer, OIG checker)
- `/core` - Singleton Supabase client, logger, configuration
- `/middleware` - Auth middleware, PII/ePHI masking for API responses

### Database Schema (Supabase PostgreSQL)

**Core Tables (Both Workflows):**
- `vendor_requests` - Employee intake submissions with ePHI gate field
- `vendors` - Master vendor records with encrypted PII (GST, PAN, bank account via pgcrypto)
- `vendor_documents` - Extracted document text and metadata
- `verification_results` - All verification check results with confidence scores
- `approvals` - Multi-step approval decisions (legal, finance, IT, compliance_officer)
- `onboarding_tokens` - Vendor portal access tokens with expiry
- `notifications_log` - Email audit trail

**Healthcare-Specific Tables:**
- `hipaa_verifications` - HIPAA compliance check results
- `baa_records` - BAA clause analysis (6 mandatory clauses tracked)
- `ephi_access_log` - APPEND-ONLY audit log (Supabase trigger blocks UPDATE/DELETE)
- `scheduled_tasks` - BAA renewal reminders, annual reassessments

**ML & Analytics Tables:**
- `bayesian_scores` - Bayesian confidence scores per verification check
- `hipaa_bayesian_scores` - HIPAA-specific Bayesian scores (weighted 2x)
- `rl_training_episodes` - Reinforcement learning experience replay buffer
- `risk_model_feedback` - Ground truth outcomes for model retraining
- `model_versions` - ML model version history with accuracy metrics
- `vendor_embeddings` - pgvector embeddings for RAG queries

**Security Configuration:**
- Enable pgcrypto extension for PII encryption
- Enable pgvector extension for RAG
- Enable Row Level Security (RLS) on all tables
- Define roles: employee, vendor, legal, finance, it, compliance_officer, admin
- `ephi_access_log` INSERT-only policy (no role can UPDATE/DELETE)

### Authentication & Authorization (Supabase Auth)
- Email + password authentication
- MFA via OTP email (Supabase built-in)
- Google OAuth provider (bonus feature)
- JWT access tokens (1 hour expiry)
- Refresh tokens (7 days expiry)
- Role-based access control mapped to RLS policies:
  - `compliance_officer` → read hipaa_verifications, baa_records, ephi_access_log
  - `it` → read verification_results, approve IT step
  - `legal` → read baa_records, approve legal step
  - `vendor` → scoped to own onboarding token only

### Event-Driven Architecture (Celery + Redis)

**Redis Configuration:**
- Message broker for Celery
- Task state storage
- Idempotency key storage with TTL

**Celery Queues (Healthcare):**
- `verification_queue` - Standard checks (GST, PAN, bank, MCA) - worker-1 & worker-2
- `hipaa_check_queue` - HIPAA checks (OIG, BAA, attestation, ePHI flow, subprocessors) - worker-1
- `approval_queue` - Approval routing tasks - worker-1
- `notification_queue` - Email notifications via SendGrid - worker-2
- `rl_training_queue` - RL model training - worker-2
- `continual_learning_queue` - Online learning updates - worker-1
- `embedding_queue` - Document embedding generation - worker-2
- `federated_queue` - Federated learning rounds - worker-1
- `scheduler_queue` - BAA renewal reminders, reassessments - worker-2
- `audit_log_queue` - ePHI access log writes - worker-2

**Celery Queues (IT SaaS):**
Same queues except no `hipaa_check_queue`, `scheduler_queue`, `audit_log_queue`

**Idempotency Strategy:**
- Check if result exists in DB before task execution
- Store task_id in Redis with TTL atomically before execution
- Tasks picked with Redis BRPOP (atomic, prevents double-processing)

### Docker Compose Architecture (Single Network)

**Services:**
- `fastapi` - API server (port 8000)
- `celery-worker-1` - Handles verification, HIPAA checks, continual learning, federated learning
- `celery-worker-2` - Handles approvals, notifications, RL training, embeddings, scheduler, audit logs
- `redis` - Message broker + state (port 6379)
- `prometheus` - Metrics scraper (port 9090)
- `grafana` - Dashboards for metrics + logs (port 3000)
- `loki` - Log aggregation (port 3100)
- `jaeger` - Request tracing UI (port 16686, optional)

**Network:** `vendor-onboarding-network` (all services discoverable by name)

**Worker Requirements:**
- Minimum 2 workers always running (demonstrates parallelization)
- Worker-1 and worker-2 process different queues simultaneously
- Atomic task pickup via Redis BRPOP

### Observability Stack

**OpenTelemetry Integration:**
- Trace spans for every HTTP request
- Span propagation from API → Celery worker → agent tool calls
- HIPAA check spans: `oig_check`, `baa_parser`, `ephi_analyzer` traced separately

**Prometheus Metrics:**
- API request rate and latency
- HIPAA check pass/fail rates
- Celery queue depth per queue (monitor `hipaa_check_queue` closely)
- Worker throughput (worker-1 vs worker-2)

**Loki Logs:**
- Structured JSON logs from all containers
- Fields: timestamp, service, level, vendor_id, agent, message

**Grafana Dashboards:**
1. API request rate + latency
2. Worker-1 vs worker-2 throughput comparison
3. HIPAA agent success/failure rates
4. Queue depths over time (highlight `hipaa_check_queue`)
5. BAA expiry timeline (upcoming renewals)
6. Federated learning round history

**Alerts:**
- `hipaa_check_queue` depth > 50 → alert admin
- Continual learning accuracy < 75% → alert compliance officer

### Security Middleware

**PII/ePHI Masking Middleware:**
- Intercept all outgoing API responses
- Strip: `pan`, `gst`, `bank_account`, `ephi_types` from payloads
- Internal service-to-service calls use service role JWT for full data access
- All Pydantic response schemas whitelist only safe fields

**Additional Security:**
- HTTPS enforced (TLS at reverse proxy)
- `ephi_access_log` writes go through `audit_log_queue` - never direct DB writes from API
- JWT validation on all protected endpoints

### LangGraph Orchestration Setup

**Supervisor Graph Structure:**
- First decision node: ePHI gate
  - `ephi_involved = false` → route to SaaS workflow graph
  - `ephi_involved = true` → route to Healthcare workflow graph
- Learning Feedback Node after every vendor outcome (feeds RL model)

**Workflow Graphs:**
- Healthcare: 24 agents (includes OIG, BAA parser, ePHI analyzer, 4-step approval)
- SaaS: 18 agents (3-step approval, no HIPAA checks)

## Frontend Integration Requirements

### API Client Configuration
The existing frontend uses:
- Base URL: `VITE_API_BASE_URL` environment variable (defaults to `http://127.0.0.1:8000`)
- API client in `frontend/src/lib/api.ts` with typed endpoints
- React Query for data fetching and caching
- React Router for navigation

### Backend API Endpoints to Implement

**Vendor Management:**
- `POST /api/v1/vendor/request` - Employee intake (SaaS)
- `POST /api/v1/healthcare/vendor/request` - Employee intake (Healthcare with ePHI gate)
- `POST /api/v1/vendor/invite/{id}` - Send vendor portal link
- `POST /api/v1/healthcare/vendor/invite/{id}` - Send HIPAA portal link
- `GET /api/v1/vendor/validate-token/{token}` - Validate onboarding token
- `POST /api/v1/vendor/upload/{token}` - Upload documents (SaaS - 8 docs)
- `POST /api/v1/healthcare/vendor/upload/{token}` - Upload documents (Healthcare - 11 docs)
- `GET /api/v1/vendors` - List vendors with status filter
- `GET /api/v1/vendors/{id}/status` - Real-time vendor status
- `GET /api/v1/vendors/{id}/report` - Comprehensive vendor report
- `GET /api/v1/vendors/{id}/events` - SSE endpoint for real-time updates

**Document Management:**
- `GET /api/v1/vendors/{id}/documents` - List vendor documents
- `POST /api/v1/vendors/{id}/documents` - Upload additional documents
- `POST /api/v1/documents/parse` - Parse documents (returns classification, metadata, dates)

**Review Endpoints:**
- `GET /api/v1/vendors/{id}/security` - Security review results
- `GET /api/v1/vendors/{id}/compliance` - Compliance review results
- `GET /api/v1/vendors/{id}/financial` - Financial review results

**Risk Assessment:**
- `GET /api/v1/vendors/{id}/risk-assessment` - Bayesian + RL risk scores
- `GET /api/v1/vendors/{id}/evidence-gaps` - Missing documents
- `GET /api/v1/vendors/{id}/evidence-status` - Evidence tracking
- `POST /api/v1/vendors/{id}/request-evidence` - Trigger evidence request email

**Approval Workflow:**
- `GET /api/v1/vendors/{id}/approval-packet` - Complete approval package
- `GET /api/v1/vendors/{id}/approval-workflow` - Workflow configuration
- `GET /api/v1/vendors/{id}/approvals` - Approval decision history
- `GET /api/v1/vendors/{id}/approval-status` - Current approval status
- `POST /api/v1/approvals/{id}/legal` - Legal approval (SaaS & Healthcare)
- `POST /api/v1/approvals/{id}/finance` - Finance approval (SaaS & Healthcare)
- `POST /api/v1/approvals/{id}/it` - IT approval (SaaS & Healthcare)
- `POST /api/v1/healthcare/approvals/{id}/compliance` - Compliance Officer approval (Healthcare only)

**Healthcare-Specific:**
- `GET /api/v1/healthcare/ephi-log/{vendor_id}` - ePHI access log (compliance_officer only)
- `POST /api/v1/rag/compliance/query` - RAG compliance queries (compliance_officer, admin)
- `POST /api/v1/chat/vendor/healthcare` - HIPAA-aware chatbot

**Dashboard:**
- `GET /api/v1/dashboard/stats` - Dashboard statistics
- `GET /api/v1/dashboard/recent` - Recent vendors, approvals, completions

**Audit:**
- `GET /api/v1/vendors/{id}/audit-trail` - Complete audit trail

**Metrics:**
- `GET /metrics` - Prometheus metrics scrape endpoint

### Frontend-Backend Integration Points

**Real-Time Updates:**
- Implement Server-Sent Events (SSE) at `/api/v1/vendors/{id}/events`
- Frontend already has `getVendorEventsUrl()` helper
- Emit events: `status_change`, `agent_start`, `agent_complete`, `error`, `approval_required`
- Event payload: `{ vendor_id, event_type, data: {...} }`

**File Upload Flow:**
1. Frontend: User uploads files via `IntakePage` or vendor portal
2. Backend: FastAPI receives multipart/form-data
3. Backend: Extract text, classify document type (GPT-4o)
4. Backend: Publish `embed_document_task` to `embedding_queue`
5. Backend: Return upload confirmation with document IDs
6. Frontend: Poll `/vendors/{id}/status` or listen to SSE for processing updates

**Approval Flow:**
1. Frontend: Approver navigates to `/audit/{vendorId}`
2. Frontend: Fetch approval packet via `GET /api/v1/vendors/{id}/approval-packet`
3. Frontend: Display Bayesian score, RL prediction, risk assessment, documents
4. Frontend: Approver submits decision via `POST /api/v1/approvals/{id}/{role}`
5. Backend: LangGraph `interrupt()` resumes workflow
6. Backend: If all approvals complete → trigger ERP setup
7. Frontend: SSE event `approval_complete` updates UI

**Healthcare ePHI Gate:**
1. Frontend: Employee submits vendor request with `ephi_involved` checkbox
2. Backend: Intake agent checks `ephi_involved` field
3. Backend: Route to Healthcare workflow if `true`, SaaS workflow if `false`
4. Frontend: Display appropriate checklist (11 docs for Healthcare, 8 for SaaS)

### Environment Variables

**Backend (.env):**
```
SUPABASE_URL=
SUPABASE_KEY=
SUPABASE_SERVICE_ROLE_KEY=
OPENAI_API_KEY=
REDIS_URL=redis://redis:6379
CELERY_BROKER_URL=redis://redis:6379
CELERY_RESULT_BACKEND=redis://redis:6379
SENDGRID_API_KEY=
SIGNZY_API_KEY=
SUREPASS_API_KEY=
DECENTRO_API_KEY=
COMPLYADVANTAGE_API_KEY=
OIG_API_URL=https://oig.hhs.gov/exclusions/api
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000
LOKI_PORT=3100
```

**Frontend (.env):**
```
VITE_API_BASE_URL=http://localhost:8000
VITE_APPROVER_BEARER_TOKEN=
```

## Implementation Checklist

### Backend Setup
- [ ] Initialize FastAPI project with MVC structure
- [ ] Implement Singleton Supabase client in `/core/supabase_client.py`
- [ ] Create all database tables in Supabase with RLS policies
- [ ] Enable pgcrypto and pgvector extensions
- [ ] Configure Supabase Auth with email, MFA, Google OAuth
- [ ] Set up Redis and Celery with all queues
- [ ] Implement idempotency checks in all Celery tasks
- [ ] Create docker-compose.yml with all services on single network
- [ ] Configure OpenTelemetry SDK in FastAPI and Celery
- [ ] Set up Prometheus metrics endpoints
- [ ] Configure Loki log aggregation
- [ ] Create Grafana dashboards (5 dashboards)
- [ ] Implement PII/ePHI masking middleware
- [ ] Set up LangGraph supervisor with ePHI gate decision node
- [ ] Create README.md with problem statement, tech stack, setup instructions

### API Endpoints
- [ ] Implement all vendor management endpoints
- [ ] Implement document upload and parsing endpoints
- [ ] Implement review endpoints (security, compliance, financial)
- [ ] Implement risk assessment endpoints
- [ ] Implement approval workflow endpoints (3-step SaaS, 4-step Healthcare)
- [ ] Implement Healthcare-specific endpoints (ePHI log, RAG, chatbot)
- [ ] Implement dashboard and audit endpoints
- [ ] Implement SSE endpoint for real-time updates
- [ ] Add Prometheus metrics scrape endpoint

### Frontend Integration
- [ ] Update `frontend/src/lib/api.ts` with new Healthcare endpoints
- [ ] Add TypeScript types for Healthcare-specific responses
- [ ] Implement SSE connection in `ShellContext` for real-time updates
- [ ] Create Healthcare vendor intake form with ePHI gate checkbox
- [ ] Create Healthcare vendor portal with 11-document checklist
- [ ] Update approval dashboard to show 4-step workflow for Healthcare vendors
- [ ] Add Compliance Officer approval UI (Healthcare only)
- [ ] Implement ePHI access log viewer (compliance_officer role)
- [ ] Add RAG compliance query interface
- [ ] Integrate HIPAA-aware chatbot widget on vendor portal

### Security & Testing
- [ ] Test PII/ePHI masking on all API responses
- [ ] Verify RLS policies block cross-role data access
- [ ] Test JWT expiry enforcement
- [ ] Test MFA OTP flow
- [ ] Test Google OAuth login
- [ ] Verify `ephi_access_log` UPDATE/DELETE returns error
- [ ] Test pgcrypto encryption (verify ciphertext in DB)
- [ ] Test idempotency (run same task twice, second skipped)
- [ ] Test parallel workers (submit 5 vendors, both workers active)
- [ ] Verify OpenTelemetry traces appear in Jaeger
- [ ] Verify logs appear in Loki from both workers




## Next Phase Preview
Phase 2 will implement the intake and document collection agents, including the ePHI gate logic, vendor invitation system, multi-step document upload portals (8 docs for SaaS, 11 for Healthcare), document classification with GPT-4o, and self-supervised embedding generation for RAG.
