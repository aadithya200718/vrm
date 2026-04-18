# Phase 4: Activation, Monitoring & Production Deployment

## Objective
Implement the final activation and monitoring components: ERP setup agent (vendor code generation, Zoho Books/SAP integration), audit trail setup for Healthcare vendors, scheduler agent (BAA renewal reminders, annual HIPAA reassessments, RL model retraining), RAG compliance query agent, vendor support chatbot (HIPAA-aware for Healthcare), and comprehensive testing (unit, integration, security, observability). This phase also covers deployment to docker-compose locally, Minikube (bonus), and cloud (Render + Vercel).

## Context
Building on Phase 3's risk assessment and approval workflows, this phase completes the vendor onboarding system by implementing post-approval activation, ongoing monitoring, compliance tracking, and production deployment. The system must handle ERP integration, maintain audit trails, schedule recurring compliance tasks, provide intelligent query capabilities, and support vendors through AI-powered chat.

## ERP Setup & Activation Agent

### ERP Setup Agent Implementation

**Celery Task:** `setup_erp_task` (approval_queue)
- Triggered when vendor status changes to `FULLY_APPROVED`
- Worker-1 picks task from `approval_queue`
- Workflow:
  1. Check idempotency (skip if vendor already has vendor_code)
  2. Generate unique vendor code: `V-{YYYY}-{4-digit-sequential}`
  3. Encrypt PII fields (GST, PAN, bank account) using pgcrypto
  4. Create vendor master record in Supabase
  5. Call external ERP API (Zoho Books or SAP)
  6. Store ERP vendor ID in vendor metadata
  7. Update vendor status to `ACTIVE`
  8. Publish `activation_notification_task` to `notification_queue`
  9. Create OpenTelemetry span: `erp_setup`

**Vendor Code Generation:**
- Format: `V-{YEAR}-{SEQUENCE}`
- Example: `V-2026-0001`, `V-2026-0002`
- Sequence resets annually
- Stored in `vendors.vendor_code` field
- Unique constraint enforced at DB level

**ERP Integration Options:**

**Option 1: Zoho Books Integration**
- Endpoint: `POST https://books.zoho.com/api/v3/contacts`
- Auth: OAuth 2.0 with refresh token
- Payload:
  ```json
  {
    "contact_name": "{vendor_name}",
    "contact_type": "vendor",
    "vendor_code": "{generated_code}",
    "payment_terms": 30,
    "currency_code": "INR",
    "gst_no": "{decrypted_gst}",
    "pan_no": "{decrypted_pan}",
    "bank_details": {
      "account_number": "{decrypted_account}",
      "ifsc_code": "{ifsc}"
    }
  }
  ```
- Response: `{ contact_id, vendor_code, status }`
- Store `contact_id` in `vendors.metadata.erp_vendor_id`

**Option 2: SAP Integration**
- Endpoint: `POST /sap/opu/odata/sap/API_BUSINESS_PARTNER/A_BusinessPartner`
- Auth: Basic Auth or OAuth
- Payload: SAP-specific XML/JSON format
- Response: Business Partner ID
- Store BP ID in `vendors.metadata.erp_vendor_id`

**Option 3: Mock ERP (Development)**
- For MVP/testing without real ERP
- Generate mock ERP ID: `ERP-{UUID}`
- Store in metadata
- Log to console for verification

### Activation Notification Agent

**Celery Task:** `activation_notification_task` (notification_queue)
- Worker-2 picks task
- Workflow:
  1. Fetch vendor details
  2. Generate activation email with:
     - Vendor code
     - Portal access credentials
     - Payment setup instructions
     - Support contact
  3. Send via SendGrid
  4. Log to `notifications_log`

**Email Template:**
- Subject: "Vendor Onboarding Complete - {vendor_name}"
- Body:
  - Congratulations message
  - Vendor code: `V-2026-XXXX`
  - Next steps: invoice submission, payment setup
  - Support contact: vendor-support@company.com

### Healthcare-Specific Activation

**Celery Task:** `setup_audit_trail_task` (audit_log_queue)
- Triggered for Healthcare vendors only
- Worker-2 picks task
- Workflow:
  1. Create initial ePHI access log entry
  2. Schedule BAA renewal reminder (6 months before expiry)
  3. Schedule annual HIPAA reassessment (12 months from activation)
  4. Store scheduled tasks in `scheduled_tasks` table
  5. Publish notification to Compliance Officer

**BAA Expiry Tracking:**
- Extract BAA expiry date from `baa_records` table
- Calculate reminder date: `expiry_date - 180 days`
- Create scheduled task: `baa_renewal_reminder`
- Celery beat picks task on due date
- Sends email to Compliance Officer and vendor

## Scheduler Agent

### Celery Beat Configuration

**Celery Beat Tasks:**
- `check_baa_expiry` - Runs daily at 9 AM
- `schedule_hipaa_reassessments` - Runs daily at 10 AM
- `retrain_rl_model` - Runs every 7 days
- `federated_learning_round` - Runs every 30 days
- `evaluate_continual_model` - Runs every 30 days
- `cleanup_expired_tokens` - Runs daily at midnight

**Beat Schedule Configuration:**
```python
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    'check-baa-expiry': {
        'task': 'backend.tasks.scheduler.check_baa_expiry',
        'schedule': crontab(hour=9, minute=0),
    },
    'schedule-hipaa-reassessments': {
        'task': 'backend.tasks.scheduler.schedule_hipaa_reassessments',
        'schedule': crontab(hour=10, minute=0),
    },
    'retrain-rl-model': {
        'task': 'backend.tasks.ml.retrain_rl_model',
        'schedule': crontab(day_of_week='monday', hour=2, minute=0),
    },
    'federated-learning-round': {
        'task': 'backend.tasks.ml.federated_training_task',
        'schedule': crontab(day_of_month=1, hour=3, minute=0),
    },
    'evaluate-continual-model': {
        'task': 'backend.tasks.ml.evaluate_continual_model',
        'schedule': crontab(day_of_month=1, hour=4, minute=0),
    },
    'cleanup-expired-tokens': {
        'task': 'backend.tasks.scheduler.cleanup_expired_tokens',
        'schedule': crontab(hour=0, minute=0),
    },
}
```

### BAA Renewal Reminder Task

**Celery Task:** `check_baa_expiry` (scheduler_queue)
- Worker-2 picks task daily
- Workflow:
  1. Query `baa_records` where `expiry_date` within next 180 days
  2. For each expiring BAA:
     - Check if reminder already sent (avoid duplicates)
     - Publish `send_baa_renewal_reminder` to `notification_queue`
     - Update `scheduled_tasks` status to `completed`
  3. Query `baa_records` where `expiry_date` < today
     - Mark vendor as `BAA_EXPIRED`
     - Publish urgent notification to Compliance Officer
     - Optionally suspend vendor access

**BAA Renewal Email:**
- Subject: "URGENT: BAA Expiring in {days} Days - {vendor_name}"
- Recipients: Compliance Officer, vendor contact
- Body:
  - BAA expiry date
  - Required actions
  - Template for new BAA
  - Deadline for renewal

### Annual HIPAA Reassessment Task

**Celery Task:** `schedule_hipaa_reassessments` (scheduler_queue)
- Worker-2 picks task daily
- Workflow:
  1. Query `vendors` where `workflow_type = HEALTHCARE` and `activated_at` = 12 months ago
  2. For each vendor due for reassessment:
     - Create reassessment request in `scheduled_tasks`
     - Publish `send_reassessment_request` to `notification_queue`
     - Update vendor status to `REASSESSMENT_REQUIRED`
  3. Compliance Officer receives dashboard notification

**Reassessment Checklist:**
- Updated HIPAA attestation
- Current BAA (if renewed)
- Updated ePHI data flow map
- Updated subprocessor list
- Cyber liability insurance renewal
- Breach notification policy review

### RL Model Retraining Task

**Celery Task:** `retrain_rl_model` (rl_training_queue)
- Worker-2 picks task weekly
- Workflow:
  1. Fetch all vendor outcomes from last 7 days
  2. Filter for completed vendors (approved + activated or rejected)
  3. For each vendor:
     - Fetch state vector from `risk_assessments`
     - Fetch actual outcome from `vendors.status`
     - Calculate reward using `reward_for_outcome()`
     - Store episode in `rl_training_episodes`
  4. Load current RL model
  5. Retrain incrementally (5 epochs)
  6. Evaluate on validation set (last 30 days)
  7. If accuracy improves:
     - Save new model version
     - Update `model_versions` table
     - Log metrics to Prometheus
  8. If accuracy degrades:
     - Rollback to previous version
     - Alert admin via `notification_queue`

### Token Cleanup Task

**Celery Task:** `cleanup_expired_tokens` (scheduler_queue)
- Worker-2 picks task daily at midnight
- Workflow:
  1. Query `onboarding_tokens` where `expires_at < now()` and `used = false`
  2. Delete expired tokens
  3. Update associated vendor requests to `SUBMISSION_EXPIRED`
  4. Log cleanup count to Prometheus

## RAG Compliance Query Agent

### RAG Implementation

**Vector Store Setup:**
- pgvector extension already enabled in Phase 1
- `vendor_embeddings` table populated in Phase 2
- Embedding model: OpenAI text-embedding-3-small (1536 dimensions)

**LangChain RAG Chain:**
```python
from langchain.vectorstores.pgvector import PGVector
from langchain.chains import RetrievalQA
from langchain.chat_models import ChatOpenAI

# Initialize vector store
vectorstore = PGVector(
    connection_string=supabase_connection_string,
    embedding_function=OpenAIEmbeddings(),
    collection_name="vendor_embeddings",
)

# Create RAG chain
rag_chain = RetrievalQA.from_chain_type(
    llm=ChatOpenAI(model="gpt-4o", temperature=0),
    chain_type="stuff",
    retriever=vectorstore.as_retriever(search_kwargs={"k": 5}),
    return_source_documents=True,
)
```

### RAG Query Endpoint

**Endpoint:** `POST /api/v1/rag/compliance/query`
- Auth: JWT (compliance_officer or admin role)
- Request body: `ComplianceQueryRequest`
  - `query` (string) - Natural language question
  - `vendor_id` (optional) - Scope to specific vendor
- Workflow:
  1. Validate JWT and role
  2. Embed query using OpenAI embeddings
  3. Perform similarity search in pgvector
  4. Retrieve top 5 relevant document chunks
  5. Pass to GPT-4o with context
  6. Generate answer with citations
  7. Log query to `ephi_access_log` (if Healthcare vendor)
  8. Return answer + source documents

**Response:**
```json
{
  "answer": "3 vendors have SOC 2 expiring in 60 days: Vendor A (expires 2026-06-15), Vendor B (expires 2026-06-20), Vendor C (expires 2026-06-25).",
  "sources": [
    {
      "vendor_id": "vendor-123",
      "vendor_name": "Vendor A",
      "document_type": "SOC 2 Type II",
      "excerpt": "Audit period: 2025-01-01 to 2025-12-31. Expiry: 2026-06-15.",
      "confidence": 0.92
    }
  ],
  "query_timestamp": "2026-04-17T10:30:00Z"
}
```

### Sample RAG Queries

**Compliance Queries:**
- "Which vendors have SOC 2 expiring in 60 days?"
- "All Tier 1 blocked vendors and reasons"
- "Vendors with bank account mismatches"
- "Healthcare vendors with BAA missing breach notification clause"
- "Vendors with OIG exclusions"
- "All vendors with ePHI data leaving jurisdiction"

**Analytics Queries:**
- "Average approval time by risk tier"
- "Most common rejection reasons"
- "Vendors approved by Legal but rejected by Finance"
- "Healthcare vendors with subprocessor coverage gaps"

### Healthcare-Specific RAG Features

**ePHI Access Logging:**
- Every RAG query on Healthcare vendor data logs to `ephi_access_log`
- Log entry includes:
  - `actor_email` - Compliance Officer email
  - `actor_role` - COMPLIANCE_OFFICER
  - `action` - "RAG_QUERY"
  - `details` - Query text, vendor IDs accessed, timestamp

**HIPAA Compliance Filters:**
- RAG queries automatically filter by `workflow_type = HEALTHCARE`
- Only Compliance Officers and Admins can query Healthcare data
- All queries traced with OpenTelemetry span: `rag_compliance_query`

## Vendor Support Chatbot

### Chatbot Implementation

**SaaS Vendor Chatbot:**
- Endpoint: `POST /api/v1/chat/vendor`
- Auth: Token-based (vendor portal token)
- Context:
  - Vendor's current checklist status
  - Documents uploaded vs required
  - Current onboarding phase
  - FAQ knowledge base
- Tool: GPT-4o (temperature=0.7, max_tokens=500)

**Healthcare Vendor Chatbot:**
- Endpoint: `POST /api/v1/chat/vendor/healthcare`
- Auth: Token-based (vendor portal token)
- Context:
  - All SaaS context PLUS:
  - HIPAA-specific document requirements
  - BAA template guidance
  - ePHI data flow map examples
  - HIPAA compliance FAQ
- Tool: GPT-4o (temperature=0.7, max_tokens=500)

### Chatbot Workflow

**Request:**
```json
{
  "token": "vendor-portal-token",
  "message": "What documents do I still need to upload?",
  "conversation_history": [
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Hi! How can I help you today?"}
  ]
}
```

**Workflow:**
1. Validate vendor token
2. Fetch vendor's current status and checklist
3. Build context prompt:
   ```
   You are a helpful vendor onboarding assistant.
   Vendor: {vendor_name}
   Status: {status}
   Documents uploaded: {uploaded_docs}
   Documents required: {required_docs}
   Missing: {missing_docs}
   
   Answer the vendor's question based on this context.
   Be friendly, concise, and helpful.
   ```
4. Call GPT-4o with context + conversation history
5. Return assistant response
6. Log conversation to `notifications_log`

**Response:**
```json
{
  "message": "You still need to upload 3 documents: SOC 2 Type II report, ISO 27001 certificate, and Penetration Test Report. You can upload them on the Documents page.",
  "suggested_actions": [
    "Upload SOC 2 Type II",
    "Upload ISO 27001",
    "Upload Pen Test Report"
  ]
}
```

### Healthcare Chatbot Enhancements

**HIPAA-Specific Responses:**
- BAA template download link
- ePHI data flow map examples
- Subprocessor list template
- Breach notification policy template
- HIPAA compliance checklist

**Example Conversation:**
- User: "What is a BAA?"
- Bot: "A Business Associate Agreement (BAA) is a contract required by HIPAA between a covered entity and a business associate that handles ePHI. It outlines how ePHI will be protected. You can download our BAA template here: [link]"

### Chatbot Widget Integration

**Frontend Integration:**
- React component: `VendorChatWidget.tsx`
- Floating chat button on vendor portal
- Persistent conversation history (session storage)
- Auto-expand on first visit
- Typing indicators
- Message timestamps

## Comprehensive Testing

### Unit Tests

**Backend Unit Tests:**
- Test each agent tool with mock API responses
- Test Bayesian scorer with edge case confidence inputs
- Test RL model with adversarial synthetic vendors
- Test idempotency: run same task twice → second run skipped
- Test PII encryption/decryption
- Test JWT validation and expiry
- Test role-based access control

**Test Framework:** pytest
**Coverage Target:** >80%

**Example Test:**
```python
def test_bayesian_scorer_with_all_high_confidence():
    scores = [
        ("GST", 0.95, 1.0),
        ("PAN", 0.92, 1.0),
        ("Bank", 0.88, 1.0),
        ("Sanctions", 0.99, 1.0),
        ("MCA", 0.91, 1.0),
        ("SOC2", 0.87, 1.0),
    ]
    result = calculate_bayesian_score(scores, healthcare=False)
    assert result.probability_legitimate > 0.85
    assert result.risk_tier == RiskTier.TIER_3.value
```

### Integration Tests

**End-to-End Onboarding Flow:**
1. Employee submits vendor request
2. Vendor receives invitation email
3. Vendor uploads all documents
4. Verification agents run in parallel
5. Bayesian + RL scoring completes
6. Approval workflow routes correctly
7. All 3 approvers approve
8. ERP setup completes
9. Vendor activated

**Test Scenarios:**
- SaaS vendor (8 documents, 3-step approval)
- Healthcare vendor (11 documents, 4-step approval)
- Healthcare vendor with OIG exclusion (auto-reject)
- Healthcare vendor with incomplete BAA (rejection)
- Vendor with sanctions match (auto-reject)

**Parallel Worker Test:**
- Submit 10 vendors simultaneously
- Verify both workers active (check logs)
- Verify tasks distributed across workers
- Verify no duplicate processing (idempotency)

### Security Tests

**PII Masking Test:**
- Call vendor API endpoint
- Verify response does not contain: `pan`, `gst`, `bank_account`, `ephi_types`
- Verify internal service calls get full PII (service role JWT)

**RLS Policy Test:**
- Create test users with different roles
- Verify Legal role cannot access Finance data
- Verify Vendor role cannot access other vendors' data
- Verify Compliance Officer can access Healthcare data only

**JWT Expiry Test:**
- Generate JWT with 1-second expiry
- Wait 2 seconds
- Call protected endpoint
- Verify 401 Unauthorized response

**MFA Test:**
- Enable MFA for test user
- Attempt login without OTP
- Verify access denied
- Complete OTP flow
- Verify access granted

**ePHI Access Log Test:**
- Query Healthcare vendor data
- Verify entry in `ephi_access_log`
- Attempt UPDATE on `ephi_access_log`
- Verify operation blocked (INSERT-only policy)

### Observability Tests

**OpenTelemetry Trace Test:**
- Submit vendor request
- Verify trace span created in Jaeger
- Verify span propagates to Celery worker
- Verify child spans for each agent tool call

**Prometheus Metrics Test:**
- Submit 5 vendor requests
- Query Prometheus: `http_requests_total{path="/api/v1/vendor/request"}`
- Verify count = 5
- Query: `http_request_duration_seconds`
- Verify latency metrics present

**Loki Logs Test:**
- Submit vendor request
- Query Loki: `{service="fastapi"} |= "vendor_request"`
- Verify structured JSON logs
- Verify fields: timestamp, service, level, vendor_id, message

**Grafana Dashboard Test:**
- Open Grafana: `http://localhost:3000`
- Navigate to "API Latency" dashboard
- Verify request rate chart shows data
- Navigate to "Worker Throughput" dashboard
- Verify worker-1 and worker-2 metrics

### Performance Tests

**Load Test:**
- Use Locust or k6
- Simulate 100 concurrent users
- Submit 1000 vendor requests
- Measure: throughput, latency, error rate
- Target: <500ms p95 latency, <1% error rate

**Celery Queue Depth Test:**
- Submit 50 vendors simultaneously
- Monitor queue depth in Prometheus
- Verify queues drain within 5 minutes
- Verify no task timeouts

## Deployment

### Local Deployment (docker-compose)

**Prerequisites:**
- Docker 20.10+
- Docker Compose 2.0+
- 8GB RAM minimum

**Steps:**
1. Clone repository
2. Copy `.env.example` to `.env`
3. Fill in API keys (OpenAI, SendGrid, etc.)
4. Run: `docker-compose up -d`
5. Verify all services running: `docker-compose ps`
6. Check logs: `docker-compose logs -f fastapi`
7. Access API: `http://localhost:8000/docs`
8. Access Grafana: `http://localhost:3000` (admin/admin)

**Health Checks:**
- FastAPI: `curl http://localhost:8000/health`
- Prometheus: `curl http://localhost:9090/-/healthy`
- Grafana: `curl http://localhost:3000/api/health`
- Redis: `docker exec -it <redis-container> redis-cli ping`

### Minikube Deployment (Bonus)

**Prerequisites:**
- Minikube 1.30+
- kubectl 1.27+
- 16GB RAM minimum

**Steps:**
1. Start Minikube: `minikube start --cpus=4 --memory=8192`
2. Enable ingress: `minikube addons enable ingress`
3. Convert docker-compose to K8s manifests:
   - Use Kompose: `kompose convert -f docker-compose.yml`
   - Or manually create Deployments, Services, ConfigMaps
4. Create namespace: `kubectl create namespace vendor-onboarding`
5. Apply manifests: `kubectl apply -f k8s/ -n vendor-onboarding`
6. Verify pods: `kubectl get pods -n vendor-onboarding`
7. Port-forward: `kubectl port-forward svc/fastapi 8000:8000 -n vendor-onboarding`

**K8s Resources:**
- Deployments: fastapi, celery-worker-1, celery-worker-2, redis, prometheus, grafana, loki, jaeger
- Services: ClusterIP for internal, LoadBalancer for external
- ConfigMaps: environment variables
- Secrets: API keys, JWT secrets
- PersistentVolumeClaims: Redis data, Grafana dashboards

### Cloud Deployment (Render + Vercel)

**Backend (Render):**
1. Create Render account
2. Create new Web Service:
   - Name: vendor-onboarding-api
   - Environment: Docker
   - Dockerfile path: `backend/Dockerfile`
   - Instance type: Standard (2GB RAM)
3. Add environment variables (all from `.env`)
4. Create Redis instance on Render or Upstash
5. Create 2 Background Workers:
   - Worker 1: `celery -A backend.tasks.celery_app.celery_app worker --queues=verification_queue,hipaa_check_queue,approval_queue,continual_learning_queue,federated_queue`
   - Worker 2: `celery -A backend.tasks.celery_app.celery_app worker --queues=verification_queue,notification_queue,rl_training_queue,embedding_queue,scheduler_queue,audit_log_queue`
6. Deploy: Render auto-deploys on git push

**Frontend (Vercel):**
1. Create Vercel account
2. Import GitHub repository
3. Framework: React (Vite)
4. Root directory: `frontend`
5. Build command: `npm run build`
6. Output directory: `dist`
7. Add environment variable: `VITE_API_BASE_URL=https://vendor-onboarding-api.onrender.com`
8. Deploy: Vercel auto-deploys on git push

**Database (Supabase):**
- Already configured in Phase 1
- Run migrations: `supabase db push`
- Enable RLS policies
- Configure Auth providers

**Observability (Cloud):**
- Prometheus: Grafana Cloud or Prometheus Cloud
- Grafana: Grafana Cloud (free tier)
- Loki: Grafana Cloud Logs
- Jaeger: Jaeger Cloud or Honeycomb

## Implementation Checklist

### ERP Setup & Activation
- [ ] Implement vendor code generation (V-YYYY-XXXX format)
- [ ] Implement ERP setup Celery task
- [ ] Integrate with Zoho Books API (or SAP)
- [ ] Implement mock ERP for development
- [ ] Implement activation notification task
- [ ] Test PII encryption in vendor master record
- [ ] Implement Healthcare audit trail setup task
- [ ] Test ERP integration end-to-end

### Scheduler Agent
- [ ] Configure Celery Beat schedule
- [ ] Implement BAA expiry check task
- [ ] Implement BAA renewal reminder email
- [ ] Implement annual HIPAA reassessment task
- [ ] Implement RL model retraining task
- [ ] Implement federated learning round task
- [ ] Implement continual model evaluation task
- [ ] Implement token cleanup task
- [ ] Test all scheduled tasks with mock dates

### RAG Compliance Query
- [ ] Implement LangChain RAG chain with pgvector
- [ ] Implement RAG query endpoint
- [ ] Add ePHI access logging for Healthcare queries
- [ ] Test sample compliance queries
- [ ] Implement source document citation
- [ ] Add query result caching (optional)
- [ ] Create RAG query UI component (frontend)
- [ ] Test RAG accuracy with ground truth queries

### Vendor Support Chatbot
- [ ] Implement SaaS chatbot endpoint
- [ ] Implement Healthcare chatbot endpoint
- [ ] Build context prompt with vendor status
- [ ] Implement conversation history tracking
- [ ] Create chatbot widget component (frontend)
- [ ] Add typing indicators and timestamps
- [ ] Test chatbot with sample conversations
- [ ] Implement suggested actions feature

### Testing
- [ ] Write unit tests for all agents (>80% coverage)
- [ ] Write integration tests for end-to-end flows
- [ ] Write security tests (PII masking, RLS, JWT, MFA)
- [ ] Write observability tests (traces, metrics, logs)
- [ ] Write performance tests (load testing)
- [ ] Run all tests in CI/CD pipeline
- [ ] Generate test coverage report
- [ ] Fix all failing tests

### Deployment
- [ ] Test local deployment with docker-compose
- [ ] Verify all services healthy
- [ ] Test Minikube deployment (bonus)
- [ ] Deploy backend to Render
- [ ] Deploy frontend to Vercel
- [ ] Configure production environment variables
- [ ] Set up Grafana Cloud for observability
- [ ] Configure domain and SSL certificates
- [ ] Run smoke tests on production
- [ ] Set up monitoring alerts

### Documentation
- [ ] Update README with deployment instructions
- [ ] Document API endpoints (OpenAPI/Swagger)
- [ ] Create user guide for employees
- [ ] Create user guide for vendors
- [ ] Create admin guide for approvers
- [ ] Document troubleshooting steps
- [ ] Create architecture diagram
- [ ] Record demo video

## Success Criteria
- Vendor code generated and stored correctly
- ERP integration creates vendor in external system
- Activation notification sent to vendor
- Healthcare vendors have audit trail initialized
- BAA expiry reminders sent 180 days before expiry
- Annual HIPAA reassessments scheduled correctly
- RL model retrains weekly with new outcomes
- RAG queries return accurate answers with citations
- Chatbot provides helpful responses to vendor questions
- All unit tests pass with >80% coverage
- End-to-end integration tests pass
- Security tests verify PII masking and RLS policies
- Observability tests verify traces, metrics, and logs
- Performance tests meet latency and throughput targets
- Local docker-compose deployment works
- Cloud deployment (Render + Vercel) works
- Production monitoring and alerts configured

## Final Deliverables
1. Fully functional vendor onboarding system (SaaS + Healthcare)
2. Complete test suite (unit, integration, security, performance)
3. Production deployment on Render + Vercel
4. Grafana dashboards for monitoring
5. Comprehensive documentation (README, API docs, user guides)
6. Demo video showcasing key features
7. Architecture diagram
8. Deployment runbook

## Post-Launch Monitoring
- Monitor Grafana dashboards daily
- Review error logs in Loki
- Track approval workflow bottlenecks
- Monitor BAA expiry calendar
- Review RL model accuracy weekly
- Collect user feedback from vendors and approvers
- Iterate on chatbot responses based on common questions
- Optimize RAG query performance
- Scale Celery workers based on queue depth
- Plan Phase 5 enhancements (if needed)
