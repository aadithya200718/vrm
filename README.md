# Vendor Onboarding Control Tower

Dual-workflow vendor onboarding system for IT/SaaS and HIPAA-sensitive healthcare vendors. The repo now contains:

- A FastAPI backend with `api`, `agents`, `models`, `tools`, `tasks`, `learning`, `rag`, `compliance`, `core`, and `middleware` packages.
- A React frontend wired to the new backend contracts for intake, vendor detail, approval, compliance, and token-based vendor portal flows.
- Docker Compose for FastAPI, two Celery workers, Redis, Prometheus, Grafana, Loki, Jaeger, and a lightweight federated-learning service.
- Supabase migration SQL for the Phase 1-3 schema, extensions, RLS, and append-only `ephi_access_log`.

## What Is Implemented

### Phase 1

- FastAPI app factory, structured JSON logging, Prometheus `/metrics`, CORS, and SSE support.
- Singleton-style Supabase client helper and a local JSON repository fallback for offline development.
- Domain models for vendor requests, documents, verifications, approvals, notifications, embeddings, ML feedback, BAA records, scheduled tasks, and ePHI access logs.
- Docker Compose + observability configs + Grafana dashboard provisioning.
- Supabase SQL migration enabling `pgcrypto`, `vector`, RLS, and append-only ePHI log enforcement.

### Phase 2

- SaaS and Healthcare intake endpoints with ePHI gate routing.
- Vendor invitation, token validation, SaaS upload, Healthcare upload, document parsing, classification, and embedding generation.
- Standard verification pipeline plus healthcare-specific HIPAA checks.
- SSE event emission for status and verification updates.
- Frontend intake screen with workflow selector and ePHI gate.
- Vendor portal routes for SaaS and Healthcare uploads.

### Phase 3

- Bayesian risk scoring with healthcare weighting and hard overrides.
- RL-style heuristic scoring, continual-learning updates, federated-round metadata capture, and model version persistence.
- 3-step SaaS and 4-step Healthcare approval workflows.
- Approval packet, workflow, decision history, approval status, and compliance dashboard views.
- RAG-style compliance query endpoint and healthcare chatbot endpoint.

## Important Runtime Notes

- Local development defaults to a JSON-backed repository in `backend/.data/dev_store.json`. This keeps the stack runnable without live Supabase credentials.
- The Supabase migration is included for production deployment, but this repo does not auto-apply it.
- External verification providers and OpenAI calls are represented with heuristic fallbacks when keys are absent.
- The federated-learning service is a local FastAPI stub that exposes the integration surface; it is not a full Flower deployment yet.

## Running Locally

### Backend

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Docker Compose

```bash
docker compose up --build
```

## Useful Dev Tokens

- Admin: `dev-role:admin:ops@hackstrom.local`
- Employee: `dev-role:employee:employee@hackstrom.local`
- Legal: `dev-role:legal:legal@hackstrom.local`
- Finance: `dev-role:finance:finance@hackstrom.local`
- IT: `dev-role:it:it@hackstrom.local`
- Compliance Officer: `dev-role:compliance_officer:compliance@hackstrom.local`

## Key Paths
- Backend entry: `backend/main.py`
- FastAPI app: `backend/api/app.py`
- Workflow service: `backend/core/services.py`
- Supabase schema: `backend/supabase/migrations/001_phase_1_3.sql`
- Docker Compose: `docker-compose.yml`
- Frontend API client: `frontend/src/lib/api.ts`

