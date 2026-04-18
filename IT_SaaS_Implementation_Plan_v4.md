
## Project Overview
A multi-agent system that automates end-to-end vendor onboarding for IT/SaaS companies.
Includes Reinforcement Learning, Bayesian Risk Scoring, Continual Learning, Federated Learning,
RAG-powered Vendor Query, full Docker-based event-driven architecture, platform security,
and production-grade observability.

Built using: LangGraph, GPT-4o, FastAPI, Supabase, Celery + Redis.
---
## Tech Stack
- Orchestration: LangGraph
- LLM: GPT-4o (OpenAI)
- Backend: FastAPI (Python) — MVC pattern
- Database: Supabase (PostgreSQL) with pgcrypto for PII encryption
- Task Queue: Celery + Redis (event-driven, 2 workers minimum)
- RL Framework: Stable Baselines3
- Bayesian Inference: PyMC or scikit-learn BayesianRidge
- Continual Learning: River (online ML library)
- Federated Learning: Flower (flwr)
- RAG: LangChain + Supabase pgvector
- Auth: Supabase Auth (JWT + Refresh Token + MFA OTP + Google OAuth)
- Observability: Prometheus + Grafana + Loki + OpenTelemetry
- Containerization: Docker + docker-compose (single network)
- Notifications: SendGrid
- Deployment: docker-compose locally, Minikube (bonus), Render + Vercel (cloud)

---

## Phase 1 — Project Setup & Infrastructure
Duration: Day 1–3

1.1 Initialize FastAPI Project Structure (Clean Architecture — MVC)
  - /api          → FastAPI route handlers (Views)
  - /agents       → Agent logic per agent (Controllers)
  - /models       → Pydantic schemas + Supabase table models (Models)
  - /tools        → External API wrappers (Signzy, Surepass, Decentro, etc.)
  - /tasks        → Celery task definitions
  - /learning     → rl_model, bayesian_scorer, continual_learner, federated_client
  - /rag          → LangChain RAG chain + pgvector retriever
  - /core         → supabase_client.py (Singleton), logger.py, config.py
  - /middleware   → auth middleware, PII masking middleware
  - README.md     → Problem Statement, Solution, Tech Stack, How to Run, Screenshots

1.2 Singleton DB Connection
  - /core/supabase_client.py:
      Supabase client initialized ONCE at app startup
      Imported and reused across all agents and tasks
      Never re-initialized per request (Singleton pattern enforced)

1.3 Set up Supabase Schema

  Core tables:
  - vendor_requests (id, employee_id, vendor_name, service_type, reason, status, created_at)
  - vendors (id, vendor_code, company_name, gst_encrypted, pan_encrypted, bank_account_encrypted, ifsc, contact_email, risk_tier, status, created_at)
  - vendor_documents (id, vendor_id, doc_type, extracted_data, verification_status, verified_at)
  - verification_results (id, vendor_id, check_type, result, confidence_score, details, checked_at)
  - approvals (id, vendor_id, approver_role, approver_email, status, comments, actioned_at)
  - onboarding_tokens (id, vendor_id, token, expires_at, used)
  - notifications_log (id, vendor_id, recipient, event_type, sent_at)

  tables:
  - bayesian_scores (id, vendor_id, check_type, confidence_score, probability_legitimate, probability_fraud, scored_at)
  - rl_training_episodes (id, vendor_id, state_vector, action_taken, reward, next_state, episode_date)
  - risk_model_feedback (id, vendor_id, predicted_tier, actual_outcome, outcome_date, model_version)
  - model_versions (id, model_type, version, accuracy, trained_on_date, is_active)
  - vendor_embeddings (id, vendor_id, doc_type, embedding vector, created_at)

  Security:
  - Enable pgcrypto extension in Supabase
  - Encrypt columns: gst, pan, bank_account using pgp_sym_encrypt
  - Enable Row Level Security (RLS) on all tables
  - Roles: employee, vendor, legal, finance, it, admin
  - Enable pgvector extension for RAG

1.4 Supabase Auth Setup
  - Enable email + password login
  - Enable MFA: OTP via email (Supabase built-in)
  - Enable Google OAuth provider (additional points)
  - JWT access token: 1 hour expiry
  - Refresh token: 7 days expiry
  - Map Supabase auth roles to RLS policies per table

1.5 Redis + Celery Setup
  - Redis as message broker
  - Celery app configured with Redis broker URL
  - Queues defined:
      verification_queue   → picked by worker-1 and worker-2
      approval_queue       → picked by worker-1
      notification_queue   → picked by worker-2
      rl_training_queue    → picked by worker-2
      continual_learning_queue → picked by worker-1
      embedding_queue      → picked by worker-2
      federated_queue      → picked by worker-1
  - Idempotency: before each task runs, check if result already exists in DB
      If yes → skip (prevents duplicate API calls on retry)
      If no → run task, mark as in-progress atomically

1.6 Docker + docker-compose Setup (Single Network)
  Services in docker-compose.yml:
  - fastapi          → FastAPI API server (port 8000)
  - celery-worker-1  → Celery worker (verification_queue, continual_learning_queue, federated_queue)
  - celery-worker-2  → Celery worker (approval_queue, notification_queue, rl_training_queue, embedding_queue)
  - redis            → Message broker + state store (port 6379)
  - prometheus       → Metrics scraper (port 9090)
  - grafana          → Dashboard: metrics + logs (port 3000)
  - loki             → Log aggregator (port 3100)
  - jaeger           → Request tracing UI (port 16686) [optional]

  All services on single Docker network: vendor-onboarding-network
  Services discoverable by service name (e.g., redis://redis:6379)
  Minimum 2 Celery workers running at all times (demonstrates parallelisation)
  Tasks picked atomically — Redis BRPOP ensures only one worker picks each task
  Idempotency maintained — task_id stored in Redis with TTL before execution

1.7 Observability Setup
  - OpenTelemetry SDK added to FastAPI:
      Every incoming HTTP request creates a trace span
      Span propagated through to Celery worker task
      Each agent tool call (Signzy, GPT-4o, etc.) creates a child span
  - Prometheus scrapes FastAPI /metrics endpoint:
      Tracks: request count, latency, agent success/failure rate
      Tracks: Celery task queue depth per queue
  - Loki collects logs from all containers via Docker logging driver
  - Grafana dashboards:
      Dashboard 1: API request rate + latency
      Dashboard 2: Celery worker task throughput (worker-1 vs worker-2)
      Dashboard 3: Agent success/failure rates per agent
      Dashboard 4: Queue depth over time
  - All logs structured as JSON with fields: timestamp, service, level, vendor_id, agent, message

1.8 Security Middleware
  - PII Masking Middleware:
      Intercepts all outgoing API responses
      Strips: pan, gst, bank_account from response payloads
      Only internal service-to-service calls get full PII
  - All Pydantic response schemas whitelist only safe fields
  - HTTPS enforced in production (TLS termination at reverse proxy)

1.9 LangGraph Setup
  - Supervisor graph node
  - Worker agent nodes (one per agent)
  - State schema for vendor onboarding flow

---

## Phase 2 — Intake & Invitation Agents
Duration: Day 4–5

2.1 Intake Agent
  - REST endpoint: POST /api/v1/vendor/request
  - Auth: JWT required (employee role only)
  - Request body validated by Pydantic schema (VendorRequestSchema)
  - Validates all fields
  - Checks Supabase if vendor already exists (idempotent check)
  - Creates vendor_request record → Status: PENDING_REVIEW
  - Publishes event to notification_queue (Celery)
  - OpenTelemetry: trace span created for this request
  - Error logged to Loki if any step fails

2.2 Vendor Invitation Agent
  - REST endpoint: POST /api/v1/vendor/invite/{request_id}
  - Auth: JWT required (admin/procurement role)
  - Generates unique UUID token, stores in onboarding_tokens with 7-day expiry
  - Publishes send_invitation_email task to notification_queue
  - Status: INVITATION_SENT
  - Celery worker-2 picks notification task, sends email via SendGrid

---

## Phase 3 — Document Collection Agent with Embedding
Duration: Day 6–7

3.1 Vendor Registration Portal (React Frontend)
  - Route: /vendor/register?token={uuid}
  - Token validated via GET /api/v1/vendor/validate-token/{token}
  - Multi-step form: Step 1 (company info) → Step 2 (document uploads)
  - Auth: token-based (no JWT required for vendor portal)

3.2 Document Upload Flow
  - POST /api/v1/vendor/upload/{token}
  - FastAPI receives file → extracts text → stores in vendor_documents
  - Publishes embed_document_task to embedding_queue (Celery worker-2)
  - Original file discarded after extraction (no S3 for MVP)
  - Documents: GST cert, PAN card, incorporation cert, cancelled cheque,
    SOC 2 Type II, ISO 27001, pen test report, signed NDA

3.3 Self-supervised Document Embedding 
  - Celery worker-2 picks embed_document_task from embedding_queue
  - Sends extracted text to OpenAI text-embedding-3-small API
  - Stores vector in vendor_embeddings (pgvector)
  - Idempotency: if embedding already exists for this vendor + doc_type → skip

3.4 Document Checklist Tracker
  - Celery beat task every 24 hours: check incomplete submissions
  - Day 3 missing docs → publish reminder_email_task to notification_queue
  - All 8 docs received → Status: DOCUMENTS_SUBMITTED
  - Publishes start_verification_task to verification_queue

---

## Phase 4 — Standard Verification Agents (Parallel)
Duration: Day 8–9

All verification agents run as parallel Celery tasks picked by worker-1 AND worker-2.
Demonstrates parallelisation — 2 workers simultaneously process different verification tasks.

4.1 GST Verification Agent
  - Celery task: verify_gst_task (verification_queue)
  - Idempotency: skip if verification_results has GST row for this vendor
  - Tool: Signzy/IDfy GST API
  - Result + confidence_score → verification_results table
  - OpenTelemetry child span: gst_verification

4.2 PAN Verification Agent
  - Celery task: verify_pan_task (verification_queue)
  - Tool: Surepass PAN API
  - Result + confidence_score → verification_results

4.3 Bank Validation Agent
  - Celery task: verify_bank_task (verification_queue)
  - Tool: Decentro penny drop
  - Result + confidence_score → verification_results

4.4 Sanctions Check Agent
  - Celery task: check_sanctions_task (verification_queue)
  - Tool: ComplyAdvantage API
  - Result + confidence_score → verification_results

4.5 MCA Company Verification Agent
  - Celery task: verify_mca_task (verification_queue)
  - Tool: Karza/Signzy MCA API
  - Extracts director names for sanctions cross-check
  - Result + confidence_score → verification_results

4.6 SOC 2 Parser Agent
  - Celery task: parse_soc2_task (verification_queue)
  - Tool: GPT-4o (temperature=0, structured JSON output)
  - Chunked document processing (500-token chunks)
  - Extracts: audit type, expiry date, auditing firm, failed controls
  - Self-consistency: run 3 times, compare — flag if disagree
  - Result + confidence_score → verification_results

---

## Phase 5 — Bayesian Risk Scoring Agent 
Duration: Day 10

5.1 Bayesian Risk Scoring Agent
  - Triggered after all 6 verification agents complete
  - Reads all confidence_scores from verification_results
  - Computes Bayesian posterior P(legitimate):
      Prior: historical approval rate from risk_model_feedback
      Likelihood: each confidence score updates prior via Bayes theorem
  - Output:
      P(legitimate): 0.0–1.0
      Confidence interval: ±X%
      Risk tier: Tier 1 / 2 / 3
      Evidence explanation: which checks drove score up/down
  - Hard rule overrides:
      Sanctions FLAGGED → AUTO_REJECT regardless of score
  - Result → bayesian_scores table + risk_tier → vendors table
  - Tool: PyMC / scikit-learn BayesianRidge

---

## Phase 6 — RL Risk Model Agent 
Duration: Day 11–12

6.1 RL Environment
  - State: 8-dimensional vector (GST, PAN, bank, sanctions, MCA, SOC2 type, SOC2 expiry, company age)
  - Actions: Tier 3 / Tier 2 / Tier 1 / Auto-reject
  - Rewards: +1 correct approval, +2 correct block, -5 false approval, -1 false block

6.2 Bootstrap Training
  - Celery task: train_rl_model_task (rl_training_queue)
  - Worker-2 picks task, trains PPO model on 500 synthetic vendor profiles
  - Model weights saved to /models folder + version logged in model_versions

6.3 Live Retraining
  - After each vendor outcome confirmed → Celery publishes rl_retrain_task
  - Model retrained incrementally, new version saved if accuracy improves

6.4 RL + Bayesian Integration
  - Both scores shown on approver dashboard
  - Models disagree → yellow flag → mandatory human review

---

## Phase 7 — Continual Learning Module 
Duration: Day 13

7.1 Online Model (River library)
  - Celery task: update_continual_model_task (continual_learning_queue)
  - Worker-1 picks task after each vendor outcome
  - River LogisticRegression updates weights per new sample
  - EWC prevents catastrophic forgetting of old fraud patterns

7.2 Model Monitoring
  - Celery beat: every 30 days evaluate accuracy on recent data
  - Alert via notification_queue if accuracy < 75%
  - Model version logged in model_versions table

---

## Phase 8 — Approval Routing Agent (Human-in-the-Loop)
Duration: Day 14

8.1 3-Step Sequential Approval with LangGraph interrupt()

  Step 1 → Legal Team
  - REST: POST /api/v1/approvals/{vendor_id}/legal
  - Auth: JWT required (legal role only)
  - Dashboard shows: NDA/MSA links, Bayesian score, RL prediction
  - Status: LEGAL_APPROVED / LEGAL_REJECTED

  Step 2 → Finance Team
  - REST: POST /api/v1/approvals/{vendor_id}/finance
  - Auth: JWT required (finance role only)
  - Status: FINANCE_APPROVED / FINANCE_REJECTED

  Step 3 → IT Team
  - REST: POST /api/v1/approvals/{vendor_id}/it
  - Auth: JWT required (it role only)
  - IT sets permission level in dashboard
  - Status: IT_APPROVED / IT_REJECTED

  All 3 approved → FULLY_APPROVED → publish erp_setup_task
  Any rejection → REJECTED → publish rejection_notification_task

8.2 Approver Dashboard Shows
  - Bayesian probability + confidence interval
  - RL model prediction
  - Model confidence indicator (green/yellow)
  - Feedback field → stored in risk_model_feedback

---

## Phase 9 — ERP Setup & Activation
Duration: Day 15

9.1 ERP Setup Agent
  - Celery task: setup_erp_task (approval_queue)
  - Worker-1 picks task on FULLY_APPROVED
  - Generate Vendor Code: V-{4 digits}
  - Create vendor record in Supabase (PII fields encrypted with pgcrypto)
  - Call Zoho Books / SAP API: create vendor, enable payments
  - Publish activation_notification_task
  - Status: ACTIVE

---

## Phase 10 — Federated Learning Module 
Duration: Day 16–17

10.1 FL Client (per company instance)
  - Celery beat: every 30 days → trigger federated_training_task (federated_queue)
  - Worker-1 trains local model on vendor_outcomes for 5 epochs
  - Sends weight delta to FL Server (central FastAPI microservice)
  - Differential Privacy: Gaussian noise added to gradients

10.2 FL Server (separate Docker service)
  - Receives deltas from all FL clients
  - FedAvg: weighted average of all deltas
  - Broadcasts updated global model back to all clients
  - Tool: Flower (flwr)

---

## Phase 11 — RAG Vendor Query Agent 
Duration: Day 18

11.1 RAG Chain
  - pgvector already populated from Phase 3 embedding pipeline
  - LangChain RAG: query → embed → similarity search → GPT-4o answer

11.2 Query Endpoint
  - REST: POST /api/v1/rag/query
  - Auth: JWT required (admin role only)
  - Returns: answer + source vendor IDs + evidence passages

11.3 Sample Queries
  - "Which vendors have SOC 2 expiring in 60 days?"
  - "All Tier 1 blocked vendors and reasons"
  - "Vendors with bank account mismatches"

---

## Phase 12 — Vendor Support Chatbot 
Duration: Day 19

12.1 GPT-4o Chatbot on Vendor Portal
  - REST: POST /api/v1/chat/vendor
  - Auth: token-based (vendor portal token)
  - Context: vendor checklist status + FAQ
  - Answers vendor questions about document requirements, process status

---

## Phase 13 — Dashboards (Frontend)
Duration: Day 20–21

13.1 Employee Dashboard — /dashboard/employee
  - Submit vendor request form
  - Track status of submitted requests

13.2 Vendor Portal — /vendor/register?token=
  - Multi-step registration + document upload
  - AI chatbot widget

13.3 Approver Dashboard — /dashboard/approvals
  - Pending approvals for logged-in role
  - Bayesian score + RL prediction per vendor
  - Approve / Reject + feedback

13.4 Admin Dashboard — /dashboard/admin
  - All vendors + pipeline status
  - RAG query box
  - ML model performance metrics
  - Grafana embedded iframe (observability)

13.5 Grafana Dashboards (Observability)
  - API request rate + latency
  - Celery worker-1 vs worker-2 throughput
  - Agent success/failure rates
  - Queue depth per queue
  - All logs searchable via Loki

---

## Phase 14 — Testing & Deployment
Duration: Day 22–24

14.1 Unit Tests
  - Each agent tool tested with mock API responses
  - Bayesian scorer tested with edge case confidence inputs
  - RL model tested with adversarial synthetic vendors
  - Idempotency tested: run same task twice → second run skipped

14.2 Integration Tests
  - Full onboarding flow end-to-end
  - Human-in-the-loop pause/resume
  - Parallel worker test: submit 10 vendors simultaneously → both workers active

14.3 Security Tests
  - Verify PII never appears in API responses
  - Verify RLS blocks cross-role data access
  - Verify JWT expiry is enforced
  - Verify MFA OTP blocks access without second factor

14.4 Observability Tests
  - Verify traces appear in Jaeger/Grafana Tempo for each request
  - Verify logs appear in Loki from both workers
  - Verify Prometheus metrics update on each request

14.5 Deployment
  Local: docker-compose up (all services on vendor-onboarding-network)
  Bonus: Minikube — convert docker-compose to K8s manifests, deploy locally
  Cloud: FastAPI + Celery → Render, Redis → Upstash, Frontend → Vercel

---

## docker-compose Services Summary

| Service | Role | Port |
|---|---|---|
| fastapi | API server | 8000 |
| celery-worker-1 | Async worker (verification, continual learning, federated) | — |
| celery-worker-2 | Async worker (approval, notification, RL training, embedding) | — |
| redis | Message broker + task state | 6379 |
| prometheus | Metrics scraper | 9090 |
| grafana | Metrics + log dashboards | 3000 |
| loki | Log aggregator | 3100 |
| jaeger | Request tracing UI (optional) | 16686 |

All on network: vendor-onboarding-network

---

## REST API Structure

| Method | Endpoint | Role | Purpose |
|---|---|---|---|
| POST | /api/v1/vendor/request | employee | Raise vendor request |
| POST | /api/v1/vendor/invite/{id} | admin | Send vendor portal link |
| GET | /api/v1/vendor/validate-token/{token} | vendor | Validate onboarding token |
| POST | /api/v1/vendor/upload/{token} | vendor | Upload document |
| GET | /api/v1/vendor/{id} | admin | Get vendor details |
| POST | /api/v1/approvals/{id}/legal | legal | Legal approval |
| POST | /api/v1/approvals/{id}/finance | finance | Finance approval |
| POST | /api/v1/approvals/{id}/it | it | IT approval |
| POST | /api/v1/rag/query | admin | Natural language vendor search |
| POST | /api/v1/chat/vendor | vendor | Vendor support chatbot |
| GET | /metrics | internal | Prometheus metrics scrape |

---

## Complete Agent List (SaaS — 18 Agents)

| Agent | Type | Pattern |
|---|---|---|
| Intake Agent | Rule-based | Tool Use |
| Vendor Invitation Agent | Rule-based | Tool Use |
| Document Collection Agent | Rule-based + Embedding | Tool Use + Self-supervised |
| GST Verification Agent | Tool Use | Tool Use |
| PAN Verification Agent | Tool Use | Tool Use |
| Bank Validation Agent | Tool Use | Tool Use |
| Sanctions Check Agent | Tool Use | Tool Use |
| MCA Verification Agent | Tool Use | Tool Use |
| SOC 2 Parser Agent | LLM (GPT-4o) | ReAct |
| Bayesian Risk Scoring Agent | Bayesian Inference | RL Risk Model Agent | Reinforcement Learning | Continual Learning Module | Online ML (River) | Federated Learning Module | Federated Learning (Flower) | Approval Routing Agent | Human-in-the-Loop | Supervisor |
| ERP Setup Agent | Automation | Tool Use |
| RAG Vendor Query Agent | RAG + LLM | Tool Use + ReAct |
| Vendor Support Chatbot | LLM + Context | Tool Use |
| Notification Agent | Automation | Tool Use |

---

## Supabase Table Summary

| Table | Purpose |
|---|---|
| vendor_requests | Employee vendor requests |
| vendors | Master record (PII encrypted) |
| vendor_documents | Extracted doc text |
| verification_results | All check results + confidence scores |
| bayesian_scores | Bayesian confidence per check |
| rl_training_episodes | RL experience replay buffer |
| risk_model_feedback | Ground truth outcomes |
| model_versions | ML model version history |
| vendor_embeddings | pgvector embeddings for RAG |
| approvals | Approval decisions per role |
| onboarding_tokens | Vendor portal tokens |
| notifications_log | Email audit trail |
